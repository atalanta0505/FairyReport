import * as engineApi from "../../lib/engineApi";
import type {
  ChapterInfo,
  LLMConfig,
  OutlineResult,
  TemplateItem,
} from "../../lib/engineApi";
import {
  defaultWritingOrderReason,
  deriveDefaultWritingOrder,
  loadOutlineFromLocal,
  loadWritingOrderFromLocal,
  normalizeReportTypeName,
  parseChaptersFromOutline,
  saveOutlineToLocal,
  saveWritingOrderToLocal,
} from "../projectStorage";
import type { ProjectStoreState } from "./types";

function isValidWritingOrder(order: number[] | undefined, chapters: ChapterInfo[]): order is number[] {
  return Boolean(
    order &&
      order.length > 0 &&
      order.length === chapters.length &&
      chapters.every((c) => order.includes(c.seq)),
  );
}

export function createOutlineSlice(state: ProjectStoreState) {
  const {
    currentProject,
    reportType,
    templates,
    loadingTemplates,
    outlineMd,
    outlineChapters,
    writingOrder,
    writingOrderReason,
    generatingOutline,
    lastBaseUrl,
    error,
  } = state;

  let debounceTimer: ReturnType<typeof setTimeout> | null = null;

  function applyResolvedWritingOrder(
    candidateOrder: number[] | undefined,
    candidateReason: string | undefined,
    targetProject: string,
    targetType: string,
    checkLocalFallback: boolean,
  ) {
    if (isValidWritingOrder(candidateOrder, outlineChapters.value)) {
      writingOrder.value = candidateOrder;
      writingOrderReason.value = candidateReason || "";
      return;
    }
    if (checkLocalFallback && targetProject) {
      const localWO = loadWritingOrderFromLocal(targetProject);
      if (localWO && isValidWritingOrder(localWO.order, outlineChapters.value)) {
        writingOrder.value = localWO.order;
        writingOrderReason.value = localWO.reason || "";
        return;
      }
    }
    writingOrder.value = deriveDefaultWritingOrder(outlineChapters.value, targetType);
    writingOrderReason.value = defaultWritingOrderReason(writingOrder.value);
  }

  async function loadTemplates(baseUrl: string): Promise<TemplateItem[]> {
    if (!baseUrl) return [];
    loadingTemplates.value = true;
    error.value = null;
    try {
      const list = await engineApi.getTemplates(baseUrl);
      const normalized = list.map((t) => ({
        ...t,
        report_type: normalizeReportTypeName(t.report_type),
      }));
      templates.value = normalized;
      reportType.value = normalizeReportTypeName(reportType.value);
      if (normalized.length > 0 && !normalized.find((t) => t.report_type === reportType.value)) {
        reportType.value = normalized[0].report_type;
      }
      return normalized;
    } catch (e) {
      error.value = (e as Error).message;
      throw e;
    } finally {
      loadingTemplates.value = false;
    }
  }

  async function saveOutline(baseUrl?: string, projectName?: string): Promise<void> {
    const targetUrl = baseUrl || lastBaseUrl.value;
    if (targetUrl) lastBaseUrl.value = targetUrl;
    const targetName = projectName || currentProject.value?.name;
    if (!targetName) return;

    const payload = {
      report_type: reportType.value,
      outline_md: outlineMd.value,
      chapters: outlineChapters.value,
      writing_order: writingOrder.value,
      writing_order_reason: writingOrderReason.value,
      updated_at: new Date().toISOString(),
    };

    saveOutlineToLocal(targetName, payload);
    saveWritingOrderToLocal(targetName, writingOrder.value, writingOrderReason.value);

    if (targetUrl) {
      try {
        await engineApi.saveProjectOutline(targetUrl, targetName, payload);
      } catch {
        /* non-fatal */
      }
    }
  }

  function triggerAutoSaveOutline(baseUrl?: string, projectName?: string, delayMs = 300) {
    const targetName = projectName || currentProject.value?.name;
    if (!targetName) return;

    saveOutlineToLocal(targetName, {
      report_type: reportType.value,
      outline_md: outlineMd.value,
      chapters: outlineChapters.value,
      writing_order: writingOrder.value,
      writing_order_reason: writingOrderReason.value,
      updated_at: new Date().toISOString(),
    });
    saveWritingOrderToLocal(targetName, writingOrder.value, writingOrderReason.value);

    if (debounceTimer) clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      saveOutline(baseUrl, targetName).catch(() => {});
    }, delayMs);
  }

  async function generateOutline(
    baseUrl: string,
    llmConfig: LLMConfig,
    reportTypeOverride?: string,
    projectNameOverride?: string,
  ): Promise<OutlineResult> {
    if (baseUrl) lastBaseUrl.value = baseUrl;
    const targetProject =
      projectNameOverride !== undefined ? projectNameOverride : currentProject.value?.name || "";
    const targetType = reportTypeOverride || reportType.value;
    if (!baseUrl) throw new Error("引擎未就绪");
    if (!targetType) throw new Error("请先选择报告类型");

    generatingOutline.value = true;
    error.value = null;
    try {
      const res = await engineApi.generateOutline(baseUrl, {
        project: targetProject,
        report_type: targetType,
        llm_config: llmConfig,
      });
      outlineMd.value = res.outline_md;
      const parsed = parseChaptersFromOutline(res.outline_md || "");
      outlineChapters.value =
        parsed.length > 0 ? parsed : res.chapters && res.chapters.length > 0 ? res.chapters : [];

      applyResolvedWritingOrder(
        res.writing_order,
        res.writing_order_reason,
        targetProject,
        targetType,
        false,
      );
      if (targetProject) {
        saveWritingOrderToLocal(targetProject, writingOrder.value, writingOrderReason.value);
        await saveOutline(baseUrl, targetProject);
      }
      return res;
    } catch (e) {
      error.value = (e as Error).message;
      throw e;
    } finally {
      generatingOutline.value = false;
    }
  }

  async function loadOutline(
    baseUrl?: string,
    projectName?: string,
  ): Promise<OutlineResult | null> {
    const targetUrl = baseUrl || lastBaseUrl.value;
    if (targetUrl) lastBaseUrl.value = targetUrl;
    const targetName = projectName || currentProject.value?.name;
    if (!targetName) {
      outlineMd.value = "";
      outlineChapters.value = [];
      writingOrder.value = [];
      writingOrderReason.value = "";
      return null;
    }

    if (targetUrl) {
      try {
        const res = await engineApi.getProjectOutline(targetUrl, targetName);
        if (
          res &&
          (res.outline_md || res.report_type || (res.chapters && res.chapters.length > 0))
        ) {
          outlineMd.value = res.outline_md || "";
          const parsed = parseChaptersFromOutline(res.outline_md || "");
          outlineChapters.value =
            parsed.length > 0
              ? parsed
              : res.chapters && res.chapters.length > 0
              ? res.chapters
              : [];
          if (res.report_type) {
            reportType.value = normalizeReportTypeName(res.report_type);
          }
          applyResolvedWritingOrder(
            res.writing_order,
            res.writing_order_reason,
            targetName,
            reportType.value,
            true,
          );
          saveWritingOrderToLocal(targetName, writingOrder.value, writingOrderReason.value);
          saveOutlineToLocal(targetName, {
            report_type: reportType.value,
            outline_md: outlineMd.value,
            chapters: outlineChapters.value,
            writing_order: writingOrder.value,
            writing_order_reason: writingOrderReason.value,
            updated_at: res.updated_at,
          });
          return {
            outline_md: outlineMd.value,
            chapters: outlineChapters.value,
            writing_order: writingOrder.value,
            writing_order_reason: writingOrderReason.value,
          };
        }
      } catch {
        /* fallback to local storage */
      }
    }

    const local = loadOutlineFromLocal(targetName);
    if (local) {
      if (local.report_type) {
        reportType.value = normalizeReportTypeName(local.report_type);
      }
      outlineMd.value = local.outline_md || "";
      const parsedLocal = parseChaptersFromOutline(local.outline_md || "");
      outlineChapters.value =
        parsedLocal.length > 0
          ? parsedLocal
          : local.chapters && local.chapters.length > 0
          ? local.chapters
          : [];
      applyResolvedWritingOrder(
        local.writing_order,
        local.writing_order_reason,
        targetName,
        reportType.value,
        true,
      );
      saveWritingOrderToLocal(targetName, writingOrder.value, writingOrderReason.value);
      return {
        outline_md: outlineMd.value,
        chapters: outlineChapters.value,
        writing_order: writingOrder.value,
        writing_order_reason: writingOrderReason.value,
      };
    }

    outlineMd.value = "";
    outlineChapters.value = [];
    writingOrder.value = [];
    writingOrderReason.value = "";
    return null;
  }

  function setOutlineMd(md: string, baseUrl?: string) {
    outlineMd.value = md;
    outlineChapters.value = parseChaptersFromOutline(md);
    if (!isValidWritingOrder(writingOrder.value, outlineChapters.value)) {
      writingOrder.value = deriveDefaultWritingOrder(outlineChapters.value, reportType.value);
    }
    triggerAutoSaveOutline(baseUrl);
  }

  function setReportType(type: string, baseUrl?: string) {
    reportType.value = normalizeReportTypeName(type);
    triggerAutoSaveOutline(baseUrl);
  }

  return {
    loadTemplates,
    generateOutline,
    loadOutline,
    saveOutline,
    triggerAutoSaveOutline,
    setOutlineMd,
    setReportType,
  };
}
