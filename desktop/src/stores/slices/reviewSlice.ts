import * as engineApi from "../../lib/engineApi";
import { extractIssueCandidateKeys } from "../../lib/markdown";
import {
  getFullReviewStorageKey,
  loadFullReviewFromLocal,
  loadReviewsFromLocal,
  saveFullReviewToLocal,
  saveReviewsToLocal,
} from "../projectStorage";
import type { ProjectStoreState, ReviewMode } from "./types";

function ensureReviewIssueIds(seq: number, rev: engineApi.ExpertReviewResult, withTimestamp = false) {
  if (rev.issues) {
    rev.issues.forEach((iss, idx) => {
      if (!iss.id) {
        iss.id = withTimestamp
          ? `issue-${seq}-${idx + 1}-${Date.now()}`
          : `issue-${seq}-${idx + 1}`;
      }
    });
  }
  if (rev.initial_issues_count === undefined) {
    rev.initial_issues_count = rev.issues?.length || 0;
  }
}

function locateTargetParagraph(originalText: string, issue: engineApi.ReviewIssue): string {
  const candidates = extractIssueCandidateKeys(issue);
  const paragraphs = originalText.split(/\n\n+/);

  for (const cand of candidates) {
    if (!cand || cand.length < 2) continue;
    const cleanCand = cand.replace(/[^\u4e00-\u9fa5a-zA-Z0-9]/g, "");
    for (const p of paragraphs) {
      if (p.includes(cand)) return p;
      if (cleanCand.length >= 4) {
        const cleanP = p.replace(/[^\u4e00-\u9fa5a-zA-Z0-9]/g, "");
        if (
          cleanP.includes(cleanCand) ||
          (cleanCand.length >= 8 && cleanP.includes(cleanCand.slice(0, 8)))
        ) {
          return p;
        }
      }
    }
  }

  if (issue.location) {
    const locKey = issue.location
      .replace(/^(?:第[一二三四五六七八九十百零\d]+章|\d+(?:\.\d+)*)\s*/, "")
      .trim();
    if (locKey.length >= 2) {
      for (const p of paragraphs) {
        if (p.includes(locKey)) return p;
      }
    }
  }

  for (const p of paragraphs) {
    if (p.trim().length >= 20 && !p.trim().startsWith("#")) {
      return p;
    }
  }
  return "";
}

export function createReviewSlice(
  state: ProjectStoreState,
  saveChapter: (baseUrl?: string, seq?: number, text?: string, immediate?: boolean) => Promise<void>,
) {
  const {
    currentProject,
    reportType,
    outlineChapters,
    chapters,
    selectedChapterSeq,
    chapterReviews,
    fullBookReview,
    reviewingSeq,
    reviewingMode,
    batchReviewing,
    reviewProgress,
    revisingSeq,
    revisingIssueId,
    revisionProgress,
    chapterSnapshots,
    activeRevision,
    lastBaseUrl,
    error,
  } = state;

  let reviewProgressTimer: ReturnType<typeof setInterval> | null = null;
  let revisionProgressTimer: ReturnType<typeof setInterval> | null = null;

  function clearReviewTimer() {
    if (reviewProgressTimer) {
      clearInterval(reviewProgressTimer);
      reviewProgressTimer = null;
    }
  }

  function clearRevisionTimer() {
    if (revisionProgressTimer) {
      clearInterval(revisionProgressTimer);
      revisionProgressTimer = null;
    }
  }

  function getChapterTitle(seq: number): string {
    return outlineChapters.value.find((c) => c.seq === seq)?.title || `第 ${seq} 章`;
  }

  async function loadReviews(
    baseUrl?: string,
    projectName?: string,
  ): Promise<Record<number, engineApi.ExpertReviewResult>> {
    const targetUrl = baseUrl || lastBaseUrl.value;
    if (targetUrl) lastBaseUrl.value = targetUrl;
    const targetName = projectName || currentProject.value?.name;
    if (!targetName) {
      chapterReviews.value = {};
      return {};
    }

    if (targetUrl) {
      try {
        const res = await engineApi.getProjectReviews(targetUrl, targetName);
        if (res && res.reviews) {
          const newReviews: Record<number, engineApi.ExpertReviewResult> = {};
          for (const [k, v] of Object.entries(res.reviews)) {
            const seq = Number(k);
            if (!isNaN(seq) && v) {
              ensureReviewIssueIds(seq, v);
              newReviews[seq] = v;
            }
          }
          chapterReviews.value = newReviews;
          saveReviewsToLocal(targetName, newReviews);
          return newReviews;
        }
      } catch {
        /* fallback */
      }
    }

    const local = loadReviewsFromLocal(targetName);
    if (local) {
      for (const [k, v] of Object.entries(local)) {
        const seq = Number(k);
        if (!isNaN(seq) && v) ensureReviewIssueIds(seq, v);
      }
      chapterReviews.value = local;
      return local;
    }

    chapterReviews.value = {};
    return {};
  }

  async function saveReview(
    baseUrl?: string,
    seq?: number,
    reviewResult?: engineApi.ExpertReviewResult,
  ): Promise<void> {
    const targetUrl = baseUrl || lastBaseUrl.value;
    if (targetUrl) lastBaseUrl.value = targetUrl;
    const targetName = currentProject.value?.name;
    const targetSeq = seq !== undefined ? seq : selectedChapterSeq.value;
    if (!targetSeq) return;

    if (reviewResult) {
      chapterReviews.value[targetSeq] = reviewResult;
    }
    const currentResult = chapterReviews.value[targetSeq];
    if (!currentResult) return;

    if (targetName) {
      saveReviewsToLocal(targetName, chapterReviews.value);
    }
    if (targetUrl && targetName) {
      try {
        await engineApi.saveProjectReview(targetUrl, targetName, targetSeq, currentResult);
      } catch {
        /* non-fatal */
      }
    }
  }

  async function deleteReview(baseUrl?: string, seq?: number): Promise<void> {
    const targetUrl = baseUrl || lastBaseUrl.value;
    if (targetUrl) lastBaseUrl.value = targetUrl;
    const targetName = currentProject.value?.name;
    const targetSeq = seq !== undefined ? seq : selectedChapterSeq.value;

    delete chapterReviews.value[targetSeq];
    if (targetName) {
      saveReviewsToLocal(targetName, chapterReviews.value);
      if (targetUrl) {
        try {
          await engineApi.deleteProjectReview(targetUrl, targetName, targetSeq);
        } catch {
          /* ignore */
        }
      }
    }
  }

  async function runChapterReview(
    baseUrl: string,
    seq: number,
    mode: ReviewMode = "fast",
    llmConfig: engineApi.LLMConfig,
  ): Promise<engineApi.ExpertReviewResult> {
    if (baseUrl) lastBaseUrl.value = baseUrl;
    const targetText = chapters.value[seq] || "";
    if (!targetText.trim()) {
      throw new Error(`第 ${seq} 章尚无正文内容，请先在步骤 3 写作该章节`);
    }

    reviewingSeq.value = seq;
    reviewingMode.value = mode;
    error.value = null;

    const chapterTitle = getChapterTitle(seq);
    const targetName = currentProject.value?.name;

    reviewProgress.value = {
      currentSeq: seq,
      currentTitle: chapterTitle,
      currentIndex: 1,
      totalTarget: 1,
      percent: 50,
      elapsedSeconds: 0,
      thoughtText: "",
      completedIssuesCount: 0,
    };

    clearReviewTimer();
    const startTime = Date.now();
    reviewProgressTimer = setInterval(() => {
      if (reviewProgress.value) {
        reviewProgress.value.elapsedSeconds = Math.floor((Date.now() - startTime) / 1000);
      }
    }, 1000);

    try {
      const res = await engineApi.streamChapterReview(
        baseUrl,
        {
          chapter_text: targetText,
          report_type: reportType.value,
          chapter_title: chapterTitle,
          mode,
          llm_config: llmConfig,
        },
        (progress) => {
          if (reviewProgress.value && progress.type === "thought") {
            reviewProgress.value.thoughtText += progress.chunk;
          }
        },
      );

      const issues = res.review?.issues ? [...res.review.issues] : [];
      const reviewRes: engineApi.ExpertReviewResult = {
        ...res.review,
        issues,
        initial_issues_count: issues.length,
        updated_at: new Date().toISOString(),
      };
      ensureReviewIssueIds(seq, reviewRes, true);

      chapterReviews.value[seq] = reviewRes;
      if (targetName) {
        saveReviewsToLocal(targetName, chapterReviews.value);
      }
      await saveReview(baseUrl, seq, reviewRes);
      return reviewRes;
    } catch (e) {
      error.value = (e as Error).message;
      throw e;
    } finally {
      clearReviewTimer();
      reviewingSeq.value = null;
      reviewProgress.value = null;
    }
  }

  async function runParagraphRevision(
    baseUrl: string,
    seq: number,
    issue: engineApi.ReviewIssue,
    llmConfig: engineApi.LLMConfig,
  ): Promise<string> {
    const targetUrl = baseUrl || lastBaseUrl.value;
    const originalText = chapters.value[seq] || "";
    if (!originalText.trim()) {
      throw new Error(`第 ${seq} 章尚无正文内容，无法修订`);
    }

    revisingSeq.value = seq;
    revisingIssueId.value = issue.id || issue.quote || issue.description || "single";
    error.value = null;

    if (!chapterSnapshots.value[seq]) {
      chapterSnapshots.value[seq] = originalText;
    }

    const chapterTitle = getChapterTitle(seq);
    const targetParagraph = locateTargetParagraph(originalText, issue);
    const instruction = `针对问题「${issue.description || issue.message}」，执行修改建议：${issue.suggestion || "完善论述与参数依据"}`;

    try {
      let newChapterText = originalText;
      if (targetParagraph) {
        let res: { revised_paragraph: string };
        try {
          res = await engineApi.streamParagraphRevision(
            targetUrl,
            {
              paragraph_text: targetParagraph,
              instruction,
              llm_config: llmConfig,
              chapter_title: chapterTitle,
              report_type: reportType.value,
            },
            (event) => {
              if (!revisionProgress.value) return;
              if (event.type === "stage" && event.message) {
                revisionProgress.value.message = event.message;
              } else if (event.type === "thought") {
                revisionProgress.value.thoughtText += event.thought || event.chunk || "";
              }
            },
          );
        } catch {
          res = await engineApi.reviseParagraph(targetUrl, {
            paragraph_text: targetParagraph,
            instruction,
            llm_config: llmConfig,
            chapter_title: chapterTitle,
            report_type: reportType.value,
          });
        }
        if (res && res.revised_paragraph) {
          newChapterText = originalText.replace(targetParagraph, res.revised_paragraph);
        }
      }

      chapters.value = { ...chapters.value, [seq]: newChapterText };
      await saveChapter(targetUrl, seq, newChapterText, true);

      if (chapterReviews.value[seq]?.issues) {
        const issues = chapterReviews.value[seq].issues || [];
        const targetIdx = issues.findIndex((i) => {
          if (issue.id && i.id && issue.id === i.id) return true;
          if (issue.quote && i.quote && issue.quote.trim() && i.quote.trim() === issue.quote.trim()) {
            return true;
          }
          const d1 = (i.description || i.message || "").trim();
          const d2 = (issue.description || issue.message || "").trim();
          return Boolean(d1 && d2 && d1 === d2);
        });
        if (targetIdx !== -1) issues.splice(targetIdx, 1);
        if (issues.length === 0) chapterReviews.value[seq].status = "通过";
        await saveReview(targetUrl, seq, chapterReviews.value[seq]);
      }

      return newChapterText;
    } catch (e) {
      error.value = (e as Error).message;
      throw e;
    } finally {
      revisingSeq.value = null;
      revisingIssueId.value = null;
    }
  }

  async function undoChapterRevision(baseUrl: string, seq: number): Promise<void> {
    const targetUrl = baseUrl || lastBaseUrl.value;
    const snapshot = chapterSnapshots.value[seq];
    if (!snapshot) return;

    chapters.value[seq] = snapshot;
    await saveChapter(targetUrl, seq, snapshot, true);
    delete chapterSnapshots.value[seq];
  }

  async function removeChapterIssue(baseUrl: string, seq: number, issueId: string): Promise<void> {
    const targetUrl = baseUrl || lastBaseUrl.value;
    if (chapterReviews.value[seq]?.issues) {
      chapterReviews.value[seq].issues = chapterReviews.value[seq].issues.filter(
        (i) => i.id !== issueId,
      );
      await saveReview(targetUrl, seq, chapterReviews.value[seq]);
    }
  }

  async function clearChapterIssues(baseUrl: string, seq: number): Promise<void> {
    const targetUrl = baseUrl || lastBaseUrl.value;
    if (chapterReviews.value[seq]) {
      chapterReviews.value[seq].issues = [];
      chapterReviews.value[seq].status = "通过";
      await saveReview(targetUrl, seq, chapterReviews.value[seq]);
    }
  }

  async function runChapterRevisionStream(
    baseUrl: string,
    seq: number,
    instruction: string,
    llmConfig: engineApi.LLMConfig,
    onThoughtChunk?: (thought: string) => void,
  ): Promise<string> {
    const targetUrl = baseUrl || lastBaseUrl.value;
    const originalText = chapters.value[seq] || "";
    if (!originalText.trim()) {
      throw new Error(`第 ${seq} 章尚无正文内容，无法修订`);
    }
    if (!instruction.trim()) {
      throw new Error("请输入修改指令或点击专家建议填入指令");
    }

    revisingSeq.value = seq;
    error.value = null;

    if (!chapterSnapshots.value[seq]) {
      chapterSnapshots.value[seq] = originalText;
    }

    const chapterTitle = getChapterTitle(seq);
    revisionProgress.value = {
      seq,
      stage: "locate",
      message: "AI 专家正在统筹修改意见与缺陷清单...",
      elapsedSeconds: 0,
      thoughtText: "",
    };

    clearRevisionTimer();
    const startTime = Date.now();
    revisionProgressTimer = setInterval(() => {
      if (revisionProgress.value) {
        revisionProgress.value.elapsedSeconds = Math.floor((Date.now() - startTime) / 1000);
      }
    }, 1000);

    try {
      const res = await engineApi.reviseChapterStream(
        targetUrl,
        {
          chapter_text: originalText,
          instruction,
          llm_config: llmConfig,
          chapter_title: chapterTitle,
          report_type: reportType.value,
        },
        (progress) => {
          if (!revisionProgress.value) return;
          if (progress.type === "stage") {
            revisionProgress.value.stage = progress.stage;
            revisionProgress.value.message = progress.message;
          } else if (progress.type === "thought") {
            revisionProgress.value.thoughtText += progress.thought;
            onThoughtChunk?.(progress.thought);
          }
        },
      );

      chapters.value[seq] = res.revised_text;
      await saveChapter(targetUrl, seq, res.revised_text, true);
      await clearChapterIssues(targetUrl, seq);

      activeRevision.value = {
        seq,
        originalText,
        revisedText: res.revised_text,
        instruction,
        createdAt: new Date().toISOString(),
      };
      return res.revised_text;
    } catch (e) {
      error.value = (e as Error).message;
      throw e;
    } finally {
      clearRevisionTimer();
      revisingSeq.value = null;
      revisionProgress.value = null;
    }
  }

  async function runChapterRevision(
    baseUrl: string,
    seq: number,
    instruction: string,
    llmConfig: engineApi.LLMConfig,
  ): Promise<string> {
    return runChapterRevisionStream(baseUrl, seq, instruction, llmConfig);
  }

  async function applyRevision(baseUrl?: string, seq?: number): Promise<void> {
    const targetUrl = baseUrl || lastBaseUrl.value;
    if (!activeRevision.value) return;
    const targetSeq = seq !== undefined ? seq : activeRevision.value.seq;
    if (activeRevision.value.seq !== targetSeq) return;

    const newText = activeRevision.value.revisedText;
    chapters.value[targetSeq] = newText;
    await saveChapter(targetUrl, targetSeq, newText, true);
    await clearChapterIssues(targetUrl, targetSeq);
    activeRevision.value = null;
  }

  function stopBatchReview(): void {
    batchReviewing.value = false;
    clearReviewTimer();
    reviewProgress.value = null;
  }

  function discardRevision(): void {
    activeRevision.value = null;
  }

  async function loadFullBookReview(
    baseUrl?: string,
    projectName?: string,
  ): Promise<engineApi.FullReviewData | null> {
    const targetUrl = baseUrl || lastBaseUrl.value;
    if (targetUrl) lastBaseUrl.value = targetUrl;
    const targetName = projectName || currentProject.value?.name;
    if (!targetName) {
      fullBookReview.value = null;
      return null;
    }

    if (targetUrl) {
      try {
        const res = await engineApi.getProjectFullReview(targetUrl, targetName);
        if (
          res &&
          (res.summary ||
            (res.issues && res.issues.length > 0) ||
            (res.numerical_checks && res.numerical_checks.length > 0) ||
            (res.chapter_evaluations && Object.keys(res.chapter_evaluations).length > 0))
        ) {
          fullBookReview.value = res;
          saveFullReviewToLocal(targetName, res);
          return res;
        }
      } catch {
        /* fallback */
      }
    }

    const local = loadFullReviewFromLocal(targetName);
    fullBookReview.value = local || null;
    return fullBookReview.value;
  }

  async function saveFullBookReview(
    baseUrl?: string,
    data?: engineApi.FullReviewData,
  ): Promise<void> {
    const targetUrl = baseUrl || lastBaseUrl.value;
    if (targetUrl) lastBaseUrl.value = targetUrl;
    const targetName = currentProject.value?.name;
    if (!targetName) return;

    if (data) fullBookReview.value = data;
    const currentData = fullBookReview.value;
    if (!currentData) return;

    saveFullReviewToLocal(targetName, currentData);
    if (targetUrl) {
      try {
        await engineApi.saveProjectFullReview(targetUrl, targetName, currentData);
      } catch {
        /* non-fatal */
      }
    }
  }

  async function deleteFullBookReview(baseUrl?: string): Promise<void> {
    const targetUrl = baseUrl || lastBaseUrl.value;
    if (targetUrl) lastBaseUrl.value = targetUrl;
    const targetName = currentProject.value?.name;
    if (!targetName) return;

    fullBookReview.value = null;
    try {
      if (typeof localStorage !== "undefined") {
        localStorage.removeItem(getFullReviewStorageKey(targetName));
      }
    } catch {
      /* ignore */
    }
    if (targetUrl) {
      try {
        await engineApi.deleteProjectFullReview(targetUrl, targetName);
      } catch {
        /* ignore */
      }
    }
  }

  async function runFullBookReview(
    baseUrl: string,
    llmConfig: engineApi.LLMConfig,
    forceAll = false,
    mode: "fast" | "all" = "fast",
  ): Promise<engineApi.FullReviewData> {
    if (baseUrl) lastBaseUrl.value = baseUrl;
    if (!baseUrl) throw new Error("引擎未就绪");

    const targetChapters = outlineChapters.value.filter((ch) => {
      const text = chapters.value[ch.seq];
      return text && text.trim().length > 0;
    });

    if (targetChapters.length === 0) {
      throw new Error("暂无可审阅的章节（需先在步骤 3 写作并生成正文）");
    }

    batchReviewing.value = true;
    error.value = null;
    clearReviewTimer();

    const firstChapter = targetChapters[0];
    reviewProgress.value = {
      currentSeq: firstChapter.seq,
      currentTitle: firstChapter.title,
      currentIndex: 1,
      totalTarget: targetChapters.length,
      percent: 0,
      elapsedSeconds: 0,
      thoughtText: "",
      completedIssuesCount: 0,
    };

    reviewProgressTimer = setInterval(() => {
      if (reviewProgress.value) {
        reviewProgress.value.elapsedSeconds += 1;
      }
    }, 1000);

    const targetName = currentProject.value?.name;

    try {
      for (let idx = 0; idx < targetChapters.length; idx++) {
        if (!batchReviewing.value) break;
        const ch = targetChapters[idx];
        const text = chapters.value[ch.seq] || "";

        if (reviewProgress.value) {
          reviewProgress.value.currentSeq = ch.seq;
          reviewProgress.value.currentTitle = ch.title;
          reviewProgress.value.currentIndex = idx + 1;
          reviewProgress.value.thoughtText = "";
        }

        if (forceAll || !chapterReviews.value[ch.seq]) {
          try {
            reviewingSeq.value = ch.seq;
            const res = await engineApi.streamChapterReview(
              baseUrl,
              {
                chapter_text: text,
                report_type: reportType.value,
                chapter_title: ch.title,
                mode,
                llm_config: llmConfig,
              },
              (ev) => {
                if (reviewProgress.value && ev.type === "thought" && ev.chunk) {
                  reviewProgress.value.thoughtText += ev.chunk;
                }
              },
            );

            const issues = res.review?.issues ? [...res.review.issues] : [];
            const reviewRes: engineApi.ExpertReviewResult = {
              ...res.review,
              issues,
              initial_issues_count: issues.length,
              updated_at: new Date().toISOString(),
            };
            ensureReviewIssueIds(ch.seq, reviewRes, true);

            chapterReviews.value[ch.seq] = reviewRes;
            if (targetName) {
              saveReviewsToLocal(targetName, chapterReviews.value);
            }
            try {
              await saveReview(baseUrl, ch.seq, reviewRes);
            } catch {
              /* non-fatal */
            }
          } catch {
            /* 章节审阅异常不中断 */
          } finally {
            reviewingSeq.value = null;
          }
        }

        let issuesSum = 0;
        for (let j = 0; j <= idx; j++) {
          const r = chapterReviews.value[targetChapters[j].seq];
          if (r && r.issues) issuesSum += r.issues.length;
        }
        if (reviewProgress.value) {
          reviewProgress.value.completedIssuesCount = issuesSum;
          reviewProgress.value.percent = Math.round(((idx + 1) / targetChapters.length) * 100);
        }
      }

      const allIssues: engineApi.ReviewIssue[] = [];
      const allNumerical: engineApi.NumericalCheckItem[] = [];
      const allGaps: (string | { chapterSeq?: number; chapterTitle?: string; gap: string })[] = [];
      const chapterEvals: Record<
        string,
        { status: string; summary: string; issues_count: number; score?: number }
      > = {};

      let passedCount = 0;
      let warningCount = 0;

      for (const ch of outlineChapters.value) {
        const rev = chapterReviews.value[ch.seq];
        if (rev) {
          if (rev.status === "通过") passedCount++;
          if (rev.status === "需补充" || rev.status === "风险警告") warningCount++;

          if (rev.issues && rev.issues.length > 0) {
            for (const iss of rev.issues) {
              allIssues.push({
                ...iss,
                location: iss.location || `第 ${ch.seq} 章 ${ch.title}`,
              });
            }
          }
          if (rev.numerical_checks && rev.numerical_checks.length > 0) {
            for (const nc of rev.numerical_checks) {
              allNumerical.push({
                ...nc,
                note: nc.note ? `${nc.note} (第 ${ch.seq} 章)` : `来自第 ${ch.seq} 章`,
              });
            }
          }
          if (rev.data_gap_checklist && rev.data_gap_checklist.length > 0) {
            for (const g of rev.data_gap_checklist) {
              allGaps.push({
                chapterSeq: ch.seq,
                chapterTitle: ch.title,
                gap: typeof g === "string" ? g : (g as any).gap || String(g),
              });
            }
          }
          chapterEvals[String(ch.seq)] = {
            status: rev.status || "通过",
            summary: rev.summary || "",
            issues_count: rev.issues?.length || 0,
            score: rev.score,
          };
        } else {
          chapterEvals[String(ch.seq)] = {
            status: "未生成",
            summary: "该章节尚无正文或未执行审阅",
            issues_count: 0,
          };
        }
      }

      const totalTarget = targetChapters.length;
      const complianceRate =
        totalTarget > 0
          ? Math.max(0, Math.min(100, Math.round((passedCount / totalTarget) * 100)))
          : 100;
      const healthStatus =
        warningCount === 0 && allIssues.length === 0
          ? "达标"
          : warningCount > 2 ||
            allIssues.some(
              (i) =>
                i.severity === "error" ||
                (i.severity as string) === "danger" ||
                (i.severity as string) === "high",
            )
          ? "存在重大缺陷"
          : "待完善";

      const summary = `全书共 ${outlineChapters.value.length} 章（已审阅 ${totalTarget} 章），发现 ${allIssues.length} 处待优化问题与 ${allGaps.length} 处资料缺口。整体合规与数据自洽达标度为 ${complianceRate}%，健康评估状态为「${healthStatus}」。`;

      const fullData: engineApi.FullReviewData = {
        summary,
        compliance_rate: complianceRate,
        health_status: healthStatus,
        issues: allIssues,
        numerical_checks: allNumerical,
        data_gap_checklist: allGaps,
        chapter_evaluations: chapterEvals,
        general_suggestions: [
          "1. 严格对照行业工程编制规程与投资项目规范，核对前后章节投资估算与建设规模数据自洽性；",
          "2. 补充完善缺失的附表、附图与前置审批支撑性底稿；",
          "3. 针对高亮批注与数据疑点小节进行专项润色与 AI 修订。",
        ],
        updated_at: new Date().toISOString(),
      };

      fullBookReview.value = fullData;
      await saveFullBookReview(baseUrl, fullData);
      return fullData;
    } catch (e) {
      error.value = (e as Error).message;
      throw e;
    } finally {
      clearReviewTimer();
      batchReviewing.value = false;
      reviewProgress.value = null;
    }
  }

  async function runAllChaptersReview(
    baseUrl: string,
    llmConfig: engineApi.LLMConfig,
    forceAll = false,
    mode: "fast" | "all" = "fast",
  ): Promise<void> {
    await runFullBookReview(baseUrl, llmConfig, forceAll, mode);
  }

  return {
    loadReviews,
    saveReview,
    deleteReview,
    runChapterReview,
    runParagraphRevision,
    undoChapterRevision,
    removeChapterIssue,
    clearChapterIssues,
    runChapterRevisionStream,
    runChapterRevision,
    applyRevision,
    runAllChaptersReview,
    stopBatchReview,
    discardRevision,
    loadFullBookReview,
    saveFullBookReview,
    deleteFullBookReview,
    runFullBookReview,
  };
}
