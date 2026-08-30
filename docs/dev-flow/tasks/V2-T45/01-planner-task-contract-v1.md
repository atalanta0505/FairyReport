# 任务合同 V2-T45 v1 — 联网检索文献端到端 URL 持久化关联、可点击直达浏览器与导出完整著录

- **状态**：READY_FOR_MAKER
- **依据**：产品负责人反馈：“联网检索文献的链接功能都没有做上。好好分析根因，然后想解决办法。”
- **根因分析**：
  1. **URL 生成与提取断链**：后端在流式写作时，RAG 检索出的网页条目虽然送入 LLM 提示词，但生成完成后未将包含真实 URL 的 `📎 本章参考资料` 章末段落追加到章节正文中，且未持久化项目级 `web_refs.json`，导致 URL 在生成后彻底丢失；
  2. **繁简/长标题模糊匹配缺失**：百度搜索结果标题包含部委后缀或繁体字，LLM 引用标签为简体缩写，原本的严格正则无法提取 URL；
  3. **Tauri 桌面沙箱阻断 `<a>` 标签跳转**：Tauri 2 桌面端默认屏蔽了 Webview 内 `<a target="_blank">` 打开系统浏览器的行为，必须通过 `@tauri-apps/plugin-shell` 或本地引擎 `POST /writing/open-url` 唤起默认系统浏览器；
  4. **导出时缺少项目级 URL 追溯**：`build_merged_md` 未能在导出时回溯查询项目级 web_refs 映射。
- **精确起始 SHA**：`99446d251b800beabeaebfb722a7b0b1f19df1f1`
- **工作树门禁**：干净工作树

---

## 1. 允许修改

- `engine/app/writing/web_search.py`
- `engine/app/writing/refs.py`
- `engine/app/writing/rag.py`
- `engine/app/writing/writer.py`
- `engine/app/writing/router.py`
- `engine/app/export/docx_builder.py`
- `desktop/src/lib/engineApi.ts`
- `desktop/src/lib/markdown.ts`
- `desktop/src/components/Step3Writing.vue`
- `desktop/src/components/Step4Review.vue`
- `desktop/src/components/Step5Export.vue`
- `engine/tests/**`
- `desktop/src/tests/**`
- `docs/dev-flow/tasks/V2-T45/**`

---

## 2. 验收标准

- [ ] 后端持久化项目级 `web_refs.json`，支持简体/繁体/子串容错匹配；
- [ ] 后端在章节写作生成结束后自动附加或流式输出带真实 URL 的 `📎 本章参考资料` 段落（`- [标题](URL)`）；
- [ ] 后端提供 `POST /writing/open-url` 接口，前端在 Tauri 桌面下点击文献标题通过 `plugin-shell` + `open-url` 100% 弹出系统浏览器访问原网页；
- [ ] 导出 Word 与 Markdown 文档末尾的《参考文献》章 100% 完整附带原始 URL（`访问网址: https://...`）；
- [ ] 5 项全量流水线门禁全部绿灯通过。
