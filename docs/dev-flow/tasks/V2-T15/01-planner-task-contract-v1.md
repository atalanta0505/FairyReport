# 任务合同 V2-T15 v1 — Step 4 审阅修改体验优化、诊断栏自适应、Diff同步排版与参考资料抽屉

- 状态：READY_FOR_MAKER（2026-08-26 产品负责人批准 V2-T15 实施方案）
- 依据：产品负责人确认 5 项审阅优化诉求与全书体检设计
- 精确起始 SHA：`d6e84eae8dd1a5607d96e636c648ddaa7b14a97b`
- 工作树门禁：`git status --short` 必须干净

---

## 1. 唯一主要变化

1. **专家诊断卡片自适应重构与功能说明 (`desktop/src/components/Step4Review.vue`)**：
   - 彻底解决诊断卡片底部截断问题，采用 `max-height: 480px; overflow-y: auto;` 自适应排版，使四个选项卡（「问题清单」「数值核验表」「缺失资料清单」「综合修改建议」）完全展示且点击顺畅；
   - 卡片收起时，渲染高 44px 的通栏胶囊卡片（含结论徽标、评分、诊断摘要预览与醒目的 `[ ▼ 展开诊断详情 ]` 按钮），点击热区宽大易点；
   - 在顶部三个审阅按钮区域补充清晰的功能定位与使用场景说明文字（全维综合、数值自洽、合规审查）。
2. **审阅与修订动态进度心跳 (`desktop/src/components/Step4Review.vue`)**：
   - 增加审阅耗时计时器与 4 阶段动态心跳提示（参数提取 ➔ 规程审查 ➔ 数值自洽 ➔ 诊断生成），彻底消除“卡死”感。
3. **Diff 差异对比排版规范化与双栏同步滚动 (`desktop/src/components/Step4Review.vue`, `desktop/src/lib/diff.ts`)**：
   - 在计算 Diff 前，强制对原文与修订正文统一调用 `normalizeMarkdown`，彻底消除单行源码粘连导致的巨长行错位问题；
   - 左右双栏采用与正文相同的 10.5pt 水利工程排版样式；
   - 实现左右双栏滚动条比例联动同步滚动（Sync Scroll：左栏滚动右栏同步，右栏滚动左栏同步）；
   - 单栏内联模式下，采用段落级高亮（红色删除线 `<s>` 与绿色浅底新增），排版干净清晰。
4. **参考资料来源清单抽屉 (`desktop/src/components/Step3Writing.vue`, `desktop/src/components/Step4Review.vue`, `desktop/src/lib/markdown.ts`)**：
   - 在 Step 3 与 Step 4 右侧顶部增加「📚 本章参考资料来源 (N)」抽屉按钮；
   - 点击滑出抽屉，自动提取正文中所有的 `【源:xxx】`、`[Z]` 及 `【网:xxx】` 标签，列出参考文件清单与段落摘要。
5. **全书跨章一致性体检 (`desktop/src/components/Step4Review.vue`, `desktop/src/stores/project.ts`)**：
   - 在左侧增加「🚀 全书一键综合体检」快捷入口，可在后台批量审查未审阅章节并汇总；
   - 在「📊 质量看板」中展示全书 10~12 章质量达标矩阵与全书缺失资料总台账。
6. **单元测试与产物构建**：
   - 增补 `desktop/src/tests/` 对应测试用例；
   - 重建 `desktop/dist/**`。

---

## 2. 允许修改

- `desktop/src/components/Step4Review.vue`
- `desktop/src/components/Step3Writing.vue`
- `desktop/src/lib/diff.ts`
- `desktop/src/lib/markdown.ts`
- `desktop/src/stores/project.ts`
- `desktop/src/tests/**`
- `desktop/dist/**`
- `docs/dev-flow/tasks/V2-T15/**`

---

## 3. 禁止修改

- `backend/**`、`engine/**`、根目录产品代码、`generic_knowledge/**`、`AGENTS.md`、`.gitignore`

---

## 4. 验收标准

- [ ] `npx vitest run`（`desktop/`）全绿。
- [ ] `python -m pytest engine/tests -q` 全绿。
- [ ] `npx vue-tsc --noEmit`、`npm run build`、`cargo check` 全绿。
- [ ] B 级实跑：
  1. 诊断卡片展开时高度自适应且四个选项卡完整展示；收起时为 44px 易点击条；
  2. 点击审阅时显示动态计时器与 4 阶段心跳提示；
  3. Diff 对比双栏排版无粘连，左右双栏滚动条实现比例联动同步滚动；
  4. Step 3 / Step 4 点击「📚 参考资料来源」能滑出抽屉列出本章命中底稿文件；
  5. 质量看板正常展示全书健康矩阵。

---

## 5. 快速验证顺序

1. `npx vitest run`（workdir=`desktop`）
2. `python -m pytest engine/tests -q`
3. `npx vue-tsc --noEmit`（workdir=`desktop`）
4. `npm run build`（workdir=`desktop`）
5. `cargo check`（workdir=`desktop/src-tauri`）
