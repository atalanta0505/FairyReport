# Planner to Maker Message — V2-T44 v1

- **任务 ID**：V2-T44
- **合同版本**：v1 (`docs/dev-flow/tasks/V2-T44/01-planner-task-contract-v1.md`)
- **起始精确 SHA**：`b18d22265206eabdf89f80897806c0f01d1e60a7`

---

## 交付任务

1. **每章参考资料抽屉（Step 3 & Step 4）与 Step 5 联网文献可点击优化**：
   - 联网文献标题呈现为清爽的超链接（带有外部打开图标 `↗`），点击直接唤起系统默认浏览器打开原网址；
   - 移除抽屉卡片中显式堆砌的 raw URL 字符块，保持卡片精致紧凑。

2. **章末 Markdown 资料清单超链接化**：
   - `build_chapter_ref_section` 中针对网页链接生成 `- [标题](URL)`；
   - `_parse_ref_section` 与 `extractReferences` 兼容解析 `- [标题](URL)` 与 `- 标题 — URL`。

3. **导出报告（Word & Markdown）文末参考文献 100% 完整附链**：
   - 导出时的《参考文献》章中，联网检索文献格式为 `[N] [联网检索] 标题. 访问网址: https://...`；
   - `assignGlobalRefNumbers` 与 `merge_global_refs` 双向保证 URL 完整提取并传递至导出生成器。

4. **测试与流水线验证**。
