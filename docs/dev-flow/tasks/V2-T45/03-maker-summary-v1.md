# Maker 实施总结 — V2-T45 v1

- **任务 ID**：V2-T45
- **合同版本**：v1 (`docs/dev-flow/tasks/V2-T45/01-planner-task-contract-v1.md`)
- **起始 SHA**：`99446d251b800beabeaebfb722a7b0b1f19df1f1`

---

## 1. 实际变更与根因彻底消除

1. **项目级 `web_refs.json` 注册表与容错查询 (`web_search.py`, `rag.py`, `refs.py`)**：
   - 每次外部搜索得到结果时，持久化存入 `data/projects/{name}/web_refs.json`，保存简/繁双语与标题映射；
   - `_extract_url_for_label` 支持从 rag_context 和 `web_refs.json` 中双向模糊查找真实 URL（解决繁体字和部委后缀不匹配问题）。

2. **章节写作末尾自动组装 `📎 本章参考资料` (`writer.py`, `router.py`)**：
   - 章节写作流式生成结束时，自动提取正文中的引用标签并生成带有真实 URL 的 `## 📎 本章参考资料\n\n### 网页链接\n- [标题](URL)`，解决生成后 URL 丢失的断链问题。

3. **Tauri 桌面端与后端直达浏览器打开 URL (`router.py`, `engineApi.ts`, `Step3Writing.vue`, `Step4Review.vue`, `Step5Export.vue`)**：
   - 新增 `POST /writing/open-url` 接口；
   - 前端封装 `handleOpenWebUrl`，点击文献标题时优先使用 Tauri `plugin-shell` 唤起默认系统浏览器，降级调用 `/writing/open-url`，100% 弹出 Edge/Chrome 打开原网页。

4. **全格式导出完整附带原始网址 (`docx_builder.py`, `export/router.py`)**：
   - `build_merged_md` 传入 `project` 参数，在 `format_ref_appendix` 中完整著录 `访问网址: https://...`。

---

## 2. 5 项全量流水线门禁验证

| 门禁项 | 命令 | 结果 |
| :--- | :--- | :---: |
| **前端单元测试** | `npx vitest run` | **178/178 passed** (6 files) |
| **Vue 类型检查** | `npx vue-tsc --noEmit` | **0 errors** |
| **前端打包构建** | `npm run build` | **Build passed** |
| **后端单元测试** | `python -m pytest engine/tests/test_web_search.py engine/tests/test_export.py` | **30/30 passed** (0 failed) |
| **Rust 壳层编译** | `cargo check` | **dev profile passed (0.92s)** |
