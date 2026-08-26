# 致 Maker 转发消息 — V2-T10 第 5 轮（阶段持久化自恢复与全景小节标题正文智能解耦）

你是当前唯一可写 Maker。

- 工作目录：`D:\Repo\FairyReport_lite`
- 精确起始 SHA：`5335509930f78a7c2feac1b570220c8227bda641`
- 有效合同：`docs/dev-flow/tasks/V2-T10/01-planner-task-contract-v5.md`

## 核心实现任务

1. **`desktop/src/stores/project.ts`**：
   - 将 `getStoredStep`、`setStoredStep`、`getStoredProjectName`、`setStoredProjectName` 改为读写 `localStorage`（键名仍为 `frl_current_step` 与 `frl_current_project`），确保关闭重启应用后精准恢复当前阶段与项目。
2. **`desktop/src/lib/markdown.ts`**：
   - 新增并导出 `extractOutlineHeadings(outlineMd: string): string[]`：
     ```ts
     export function extractOutlineHeadings(outlineMd: string): string[] {
       if (!outlineMd || typeof outlineMd !== "string") return [];
       const lines = outlineMd.split("\n");
       const headings: string[] = [];
       for (const line of lines) {
         const trimmed = line.trim();
         const match = trimmed.match(/^#{1,4}\s+(.+)$/);
         if (match) {
           headings.push(match[1].trim());
         }
       }
       // 长度降序排序，保证长标题优先匹配
       return headings.sort((a, b) => b.length - a.length);
     }
     ```
   - 增强 `normalizeMarkdown(md: string, knownHeadings?: string[]): string`：
     - 精准匹配已知大纲标题库（去掉 # 后的纯标题前缀匹配）：
       ```ts
       if (knownHeadings && Array.isArray(knownHeadings)) {
         for (const h of knownHeadings) {
           if (!h || typeof h !== "string") continue;
           const cleanH = h.replace(/^#+\s*/, "").trim();
           if (!cleanH) continue;
           const escaped = cleanH.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
           // 匹配形如 ### 1.4.1 主要研究结论经研究论证， -> ### 1.4.1 主要研究结论\n\n经研究论证，
           const reg = new RegExp(`^(#{1,6}\\s+(?:\\d+(?:\\.\\d+)*\\s+)?${escaped})\\s*([^\\n]+)$`, "gm");
           text = text.replace(reg, "$1\n\n$2");
         }
       }
       ```
     - 增加行业小节特征词通用断行规则：
       ```ts
       text = text.replace(
         /(#{1,6}\s+\d+(?:\.\d+)*\s+[\u4e00-\u9fa5\w、—\-\/（）()]{1,20}?(?:概况|背景|进展|情况|分析|方案|建议|结论|目标|任务|内容|规模|地点|工期|来源|估算|指标|信息|依据|政策|规范|成果|其他|符合性|衔接性|必要性|适当时|要求|保障|评估|设计|组织|测算|预算|说明|构成|论证|原则|措施|布局|标准|选址|模式|效益|影响|评价|预案|附件|附表|附图))([，。：:（(《“\u4e00-\u9fa5].*)$/gm,
         "$1\n\n$2"
       );
       ```
3. **`desktop/src/components/Step3Writing.vue`**：
   - 计算 `const outlineHeadings = computed(() => extractOutlineHeadings(projectStore.outlineMd));`
   - 在 `markdownToHtml` 与 `extractSubHeadings` 调用处传入 `outlineHeadings.value`。
4. **单测适配与产物重构**：
   - 更新 `project.test.ts` 与 `markdown.test.ts`；
   - 重新构建 `desktop/dist/**`；
   - 运行 vitest、vue-tsc、build、pytest 与 cargo check。

## 完成时

1. 只提交允许范围；
2. 完成说明写到 `docs/dev-flow/tasks/V2-T10/rounds/05/maker-completion.md`，单独提交；
3. 不 amend、不 rebase、不 push；
4. 冻结工作树交回。
