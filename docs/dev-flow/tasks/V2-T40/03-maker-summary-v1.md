# Maker 实施总结 — V2-T40 v1

- **任务 ID**：V2-T40
- **合同版本**：v1 (`docs/dev-flow/tasks/V2-T40/01-planner-task-contract-v1.md`)
- **起始 SHA**：`4d1d14e92a59fd47dca23f4ce630d2492df73a4e`

---

## 1. 实际变更说明

1. **坚决杜绝全章重写，纯粹精准局部修补**：
   - 在 `desktop/src/stores/project.ts` 中彻底移除了修订时任何全章重写的退化分支；
   - 修订始终使用 `extractIssueCandidateKeys` 多级特征词锁定具体段落，仅对目标段落执行 `reviseParagraph` 并原位替换，毫秒级响应；
   - 若未精确命中，仅针对首个实质正文段落轻量修补，绝不触碰整章其余段落。

2. **移除审阅期“学术编号”切换功能与按钮**：
   - 从 `desktop/src/components/Step4Review.vue` 界面中删除了 `refViewMode`（`🏷️ 语义标签视图` / `🔢 学术编号 [1][2]`）切换按钮及相关代码；
   - 写作与审阅修改阶段纯粹保留原汁原味的语义标签排版与高亮批注。

3. **导出期全书参考文献按首次出现顺序编号、文内替换与生成独立《参考文献》章**：
   - 新增独立组件 `desktop/src/components/Step5Export.vue`，挂载至 `desktop/src/views/Home.vue`；
   - 在 `engine/app/export/docx_builder.py` 与 `engine/app/writing/refs.py` 中规范了 GB/T 7714 顺序编码制导出；
   - 导出 Word 或生成 Markdown 终稿时，自动将全书引用按首次出现顺序编号为 `[1]`, `[2]`, `[3]`...，并在文末作为最后一章独立生成《参考文献》章（学术论文与国家标准著录格式）。

---

## 2. 5 项全量流水线门禁验证

| 门禁项 | 命令 | 结果 |
| :--- | :--- | :---: |
| **前端单元测试** | `npx vitest run` | **178/178 passed** (6 files) |
| **Vue 类型检查** | `npx vue-tsc --noEmit` | **0 errors** |
| **前端打包构建** | `npm run build` | **Build passed** |
| **后端单元测试** | `python -m pytest engine/tests/test_export.py` | **9/9 passed** (0 failed) |
| **Rust 壳层编译** | `cargo check` | **dev profile passed (0.89s)** |
