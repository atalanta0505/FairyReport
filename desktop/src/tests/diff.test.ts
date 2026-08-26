import { describe, expect, it } from "vitest";
import {
  computeDiffBlocks,
  computeDiffStats,
  computeLineDiff,
  computeWordDiff,
  tokenizeWords,
} from "../lib/diff";

describe("diff.ts 单元测试", () => {
  describe("computeLineDiff 行级对比", () => {
    it("空文本对比返回空数组", () => {
      const diff = computeLineDiff("", "");
      expect(diff).toEqual([]);
    });

    it("原文本为空，全量新增", () => {
      const diff = computeLineDiff("", "第1行\n第2行");
      expect(diff.length).toBe(2);
      expect(diff[0]).toEqual({ type: "added", text: "第1行", newLineNumber: 1 });
      expect(diff[1]).toEqual({ type: "added", text: "第2行", newLineNumber: 2 });
    });

    it("修改后文本为空，全量删除", () => {
      const diff = computeLineDiff("第1行\n第2行", "");
      expect(diff.length).toBe(2);
      expect(diff[0]).toEqual({ type: "removed", text: "第1行", oldLineNumber: 1 });
      expect(diff[1]).toEqual({ type: "removed", text: "第2行", oldLineNumber: 2 });
    });

    it("文本完全相同返回全量 unchanged", () => {
      const text = "# 第一章 概述\n本章节介绍项目基本背景。";
      const diff = computeLineDiff(text, text);
      expect(diff.length).toBe(2);
      expect(diff[0]).toEqual({
        type: "unchanged",
        text: "# 第一章 概述",
        oldLineNumber: 1,
        newLineNumber: 1,
      });
      expect(diff[1]).toEqual({
        type: "unchanged",
        text: "本章节介绍项目基本背景。",
        oldLineNumber: 2,
        newLineNumber: 2,
      });
    });

    it("精准识别中间插入行与删除行", () => {
      const orig = "标题\n第一段\n第二段\n结尾";
      const mod = "标题\n第一段\n插入的新段落\n结尾";

      const diff = computeLineDiff(orig, mod);
      const types = diff.map((d) => d.type);
      expect(types).toEqual(["unchanged", "unchanged", "removed", "added", "unchanged"]);

      const removed = diff.find((d) => d.type === "removed");
      expect(removed?.text).toBe("第二段");
      expect(removed?.oldLineNumber).toBe(3);

      const added = diff.find((d) => d.type === "added");
      expect(added?.text).toBe("插入的新段落");
      expect(added?.newLineNumber).toBe(3);
    });
  });

  describe("tokenizeWords 与 computeWordDiff 词级微观对比", () => {
    it("分词支持中英文及标点", () => {
      const tokens = tokenizeWords("项目投资 1200 万元（约 $1.8M）。");
      expect(tokens).toContain("项");
      expect(tokens).toContain("目");
      expect(tokens).toContain("1200");
      expect(tokens).toContain("万");
      expect(tokens).toContain("元");
    });

    it("词级微观对比能高亮修改词汇", () => {
      const oldStr = "项目总投资为 1000 万元。";
      const newStr = "项目总投资为 1200 万元整。";

      const diff = computeWordDiff(oldStr, newStr);
      const added = diff.filter((d) => d.type === "added").map((d) => d.text);
      const removed = diff.filter((d) => d.type === "removed").map((d) => d.text);

      expect(removed).toContain("1000");
      expect(added).toContain("1200");
      expect(added).toContain("整");
    });
  });

  describe("computeDiffBlocks 双栏块级对齐", () => {
    it("构建双栏对比块", () => {
      const orig = "段落一\n段落二（待修改）\n段落三";
      const mod = "段落一\n段落二（已修改并补充数据）\n段落三";

      const blocks = computeDiffBlocks(orig, mod);
      expect(blocks.length).toBe(3);
      expect(blocks[0].type).toBe("unchanged");
      expect(blocks[1].type).toBe("modified");
      expect(blocks[1].oldLines[0].text).toBe("段落二（待修改）");
      expect(blocks[1].newLines[0].text).toBe("段落二（已修改并补充数据）");
      expect(blocks[2].type).toBe("unchanged");
    });

    it("处理纯新增和纯删除块", () => {
      const orig = "首行\n末行";
      const mod = "首行\n插入1\n插入2\n末行";

      const blocks = computeDiffBlocks(orig, mod);
      expect(blocks.length).toBe(3);
      expect(blocks[1].type).toBe("added");
      expect(blocks[1].newLines.length).toBe(2);
    });
  });

  describe("computeDiffStats 统计指标", () => {
    it("正确计算行数统计", () => {
      const orig = "行1\n行2\n行3";
      const mod = "行1\n行2修改\n行3\n行4新增";

      const stats = computeDiffStats(orig, mod);
      expect(stats.unchangedLines).toBe(2); // 行1, 行3
      expect(stats.removedLines).toBe(1); // 行2
      expect(stats.addedLines).toBe(2); // 行2修改, 行4新增
      expect(stats.totalOriginalLines).toBe(3);
      expect(stats.totalModifiedLines).toBe(4);
    });
  });

  describe("Markdown 自动断行规范化与防粘连 Diff 测试", () => {
    it("粘连标题与单行表格在 Diff 前自动规范化断行，避免整段错位", () => {
      const gluedOrig = "# 第一章 概述## 1.1 项目概况本工程总投资 10 亿元。";
      const gluedMod = "# 第一章 概述## 1.1 项目概况本工程总投资 12 亿元整。";

      const diff = computeLineDiff(gluedOrig, gluedMod);
      // 应该被规整为多行，而不是 1 行整体替换
      expect(diff.length).toBeGreaterThan(2);
      expect(diff[0].text).toBe("# 第一章 概述");
      expect(diff[0].type).toBe("unchanged");
      expect(diff[2].text).toBe("## 1.1 项目概况");
      expect(diff[2].type).toBe("unchanged");

      const stats = computeDiffStats(gluedOrig, gluedMod);
      expect(stats.unchangedLines).toBeGreaterThanOrEqual(2);
    });

    it("支持已知大纲标题库精确断行比对", () => {
      const orig = "### 1.4.1 主要研究结论经综合评估，各项指标合格。";
      const mod = "### 1.4.1 主要研究结论经重新核算，新增抗震指标。";
      const knownHeadings = ["1.4.1 主要研究结论"];

      const blocks = computeDiffBlocks(orig, mod, knownHeadings);
      expect(blocks[0].oldLines[0].text).toBe("### 1.4.1 主要研究结论");
      expect(blocks[0].type).toBe("unchanged");
      expect(blocks[1].type).toBe("modified");
    });
  });
});
