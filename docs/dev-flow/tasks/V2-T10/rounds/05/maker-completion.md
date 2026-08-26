# Maker 完成说明 — V2-T10 第 5 轮（阶段持久化自恢复与全景小节标题正文智能解耦）

## 基本信息

- **任务 ID**：V2-T10
- **轮次**：第 5 轮
- **完成时间**：2026-08-26
- **有效合同**：[`docs/dev-flow/tasks/V2-T10/01-planner-task-contract-v5.md`](file:///d:/Repo/FairyReport_lite/docs/dev-flow/tasks/V2-T10/01-planner-task-contract-v5.md)
- **精确起始 SHA**：`8c06202410a80db61b8fbf1e02c636ddf13fc345`
- **候选交付 SHA**：`9a63cca2fff7cfc4a2ec6a871144e9e115b73dca`

---

## 1. 核心实现范围与修改文件清单

### 1.1 跨会话阶段与项目持久化自恢复
- **文件**：[`desktop/src/stores/project.ts`](file:///d:/Repo/FairyReport_lite/desktop/src/stores/project.ts)
  - 将 `getStoredStep`、`setStoredStep`、`getStoredProjectName`、`setStoredProjectName` 中的存储媒介由 `sessionStorage` 切换为 `localStorage`（并保留 `sessionStorage` 兼容读取与同步）；
  - 保持键名 `frl_current_step` 与 `frl_current_project` 不变；
  - 确保应用关闭、重启或刷新后，直接自恢复到用户停留在的精确阶段步骤（Step 1~5）及选定项目，杜绝回跳到 Step 1。

### 1.2 全景小节标题正文智能解耦与行业特征词法识别
- **文件**：[`desktop/src/lib/markdown.ts`](file:///d:/Repo/FairyReport_lite/desktop/src/lib/markdown.ts)
  - 新增并导出 `extractOutlineHeadings(outlineMd: string): string[]`：
    - 从大纲 Markdown 中提取所有 `#` ~ `####` 纯净标题；
    - 自动生成包含带序号与去序号版本的纯标题集合，并按文本长度降序排列（长标题优先精确匹配）；
  - 升级 `normalizeMarkdown(md: string, knownHeadings?: string[])` 预处理链路：
    - **第一道防线（大纲标题库精确前缀断行）**：遍历 `knownHeadings`，采用 `^(#{1,6}\s+(?:\d+(?:\.\d+)*\s+)?${escaped})\s*([^\n]+)$` 强行将粘连正文拆解为 `$1\n\n$2`；
    - **第二道防线（工程咨询行业特征小节标题词法断行）**：新增行业小节词法正则：
      `/(#{1,6}\s+\d+(?:\.\d+)*\s+[\u4e00-\u9fa5\w、—\-\/（）()]{1,20}?(?:概况|背景|进展|情况|分析|方案|建议|结论|目标|任务|内容|规模|地点|工期|来源|估算|指标|信息|依据|政策|规范|成果|其他|符合性|衔接性|必要性|适当时|要求|保障|评估|设计|组织|测算|预算|说明|构成|论证|原则|措施|布局|标准|选址|模式|效益|影响|评价|预案|附件|附表|附图))([，。：:（(《“\u4e00-\u9fa5].*)$/gm`
      全景覆盖如 `1.4.1 主要研究结论`、`1.4.2 问题与建议`、`2.2.1 与经济社会发展规划衔接性`、`2.2.2 与区域规划衔接性`、`2.2.4 与国土空间规划衔接性`、`2.3.1 宏观层面必要性`、`2.3.4 建设时机适当时` 等小节标题与正文的粘连拆解；
    - **第三道防线（中文句式起首词断行）**：增加标点排除保护（`[^\s#\n，。！？；]`），精准配合前述防线。

### 1.3 写作界面 Step 3 集成
- **文件**：[`desktop/src/components/Step3Writing.vue`](file:///d:/Repo/FairyReport_lite/desktop/src/components/Step3Writing.vue)
  - 响应式计算 `const outlineHeadings = computed(() => extractOutlineHeadings(projectStore.outlineMd));`；
  - 在 `syncEditorContent`、`chapterSubHeadingsMap` 计算属性及 `currentChapterText` 实时监听中，统一向 `markdownToHtml` 与 `extractSubHeadings` 传入 `outlineHeadings.value`；
  - 确保左侧子标题导航树纯净显示（不包含任何正文文字），且右侧就地富文本编辑器精确渲染独立 `<h3>` 与 `<p>` 段落。

### 1.4 单元测试覆盖
- **文件**：[`desktop/src/tests/project.test.ts`](file:///d:/Repo/FairyReport_lite/desktop/src/tests/project.test.ts)
  - 更新为 `localStorage` 阶段与项目跨会话持久化和恢复单测。
- **文件**：[`desktop/src/tests/markdown.test.ts`](file:///d:/Repo/FairyReport_lite/desktop/src/tests/markdown.test.ts)
  - 新增 `extractOutlineHeadings` 标题提取与长度降序单测；
  - 针对 1.4.1、1.4.2、2.2.1、2.2.2、2.2.4、2.3.1、2.3.4 等全场景小节粘连解耦新增测试；
  - 新增已知大纲标题库与行业特征小节标题端到端解耦及 HTML/目录渲染测试。

### 1.5 生产构建产物
- **文件**：[`desktop/dist/**`](file:///d:/Repo/FairyReport_lite/desktop/dist)
  - 重新编译生成前端生产静态产物。

---

## 2. 快速验证记录

严格按照合同第 5 节指定顺序执行快速验证：

1. **桌面端单元测试**：
   ```powershell
   cd desktop
   npx vitest run
   # 输出：4 passed (api.test.ts, engine.test.ts, markdown.test.ts, project.test.ts), 91 passed (91)
   ```
2. **桌面端 TypeScript 类型检查**：
   ```powershell
   cd desktop
   npx vue-tsc --noEmit
   # 输出：退出码 0，无任何类型报错
   ```
3. **桌面端生产构建**：
   ```powershell
   cd desktop
   npm run build
   # 输出：✓ built in 862ms，产物完整输出至 desktop/dist/
   ```
4. **后端引擎端测试**：
   ```powershell
   python -m pytest engine/tests -q
   # 输出：78 passed, 2 warnings in 43.59s
   ```
5. **Rust / Tauri 编译检查**：
   ```powershell
   cd desktop/src-tauri
   cargo check
   # 输出：Finished dev profile in 1.56s，无错误
   ```

---

## 3. 设计决策与技术说明

1. **多重防御体系（Defense-in-Depth）**：
   - **大纲库精确匹配（第一道防线）**：通过提取并降序排列当前项目大纲中的所有小节标题，对章节 Markdown 进行精准前缀断行；
   - **工程咨询行业特征词法正则（第二道防线）**：涵盖“衔接性”、“必要性”、“适当时”、“结论”、“建议”等 40 余个行业关键词，即使大纲标题未同步或手动编写时，也能智能识别小节标题结尾并将其与正文拆分；
   - **高频句首词与标点保护（第三道防线）**：在遇到“项目”、“本项目”、“根据”等高频句首词时，结合标点排除保护拆解粘连，杜绝误切。
2. **跨会话持久化与平滑降级**：
   - 使用 `localStorage` 作为主要存储媒介，确保浏览器或 WebView 进程关闭重启后，步骤和项目状态依然完整；
   - 同时向 `sessionStorage` 写入并作为降级回退，保证全环境兼容性。

---

## 4. 冻结声明与交回

- 本地候选提交 SHA：`9a63cca2fff7cfc4a2ec6a871144e9e115b73dca`
- 严格遵循修改范围：仅修改合同允许的 `desktop/src/stores/project.ts`、`desktop/src/lib/markdown.ts`、`desktop/src/components/Step3Writing.vue`、`desktop/src/tests/project.test.ts`、`desktop/src/tests/markdown.test.ts`、`desktop/dist/**` 与任务文档。
- 严格禁止修改约束：未触碰 `backend/**`、`engine/**`、根目录产品代码、`generic_knowledge/**`、`AGENTS.md`、`.gitignore` 等禁止路径。
- 无 `git push`、无 `git commit --amend`、无 `git rebase`。
- 本轮编码与测试全部完成，提交本完成说明后冻结工作树，交由 Checker 验收。
