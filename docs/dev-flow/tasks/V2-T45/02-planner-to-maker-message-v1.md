# Planner to Maker Message — V2-T45 v1

- **任务 ID**：V2-T45
- **合同版本**：v1 (`docs/dev-flow/tasks/V2-T45/01-planner-task-contract-v1.md`)
- **起始精确 SHA**：`99446d251b800beabeaebfb722a7b0b1f19df1f1`

---

## 交付任务

1. **项目级 `web_refs.json` 注册表与容错查询 (`web_search.py`, `rag.py`, `refs.py`)**：
   - 每次搜索得到结果时，持久化写入 `data/projects/{name}/web_refs.json`，保存简/繁双语映射；
   - `_extract_url_for_label` 支持从 rag_context 和 `web_refs.json` 智能查找 URL。

2. **章节写作末尾自动组装 `📎 本章参考资料` (`writer.py`, `router.py`)**：
   - 章节流式写作完成时，自动识别正文中的 `【网:...】` 标签，提取对应的真实 URL，并追加标准的 `## 📎 本章参考资料\n\n### 网页链接\n- [标题](URL)`；
   - 流式 SSE 发送此段落或在落库前拼接。

3. **Tauri 桌面端与后端直达浏览器打开 URL (`router.py`, `engineApi.ts`, `Step3Writing.vue`, `Step4Review.vue`, `Step5Export.vue`)**：
   - 新增 `POST /writing/open-url`；
   - 前端封装 `handleOpenWebUrl`，点击文献标题时优先使用 Tauri `plugin-shell`，降级调用 `/writing/open-url`，100% 弹出系统浏览器。

4. **全格式导出完整附带原始网址 (`docx_builder.py`, `markdown.ts`)**：
   - `build_merged_md` 传入 `project` 名称，在 `format_ref_appendix` 中完整著录 `访问网址: https://...`。

5. **全量测试与门禁验证**。
