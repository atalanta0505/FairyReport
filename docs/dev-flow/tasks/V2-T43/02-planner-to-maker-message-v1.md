# Planner to Maker Message — V2-T43 v1

- **任务 ID**：V2-T43
- **合同版本**：v1 (`docs/dev-flow/tasks/V2-T43/01-planner-task-contract-v1.md`)
- **起始精确 SHA**：`0487fbdbc6b6d4f90f2e8cc916509ff878381850`

---

## 交付任务

1. **导出文件夹直达与文件精准高亮定位**：
   - 在 `engine/app/export/router.py` 中新增 `POST /export/open-folder` 接口，支持传入 `path`，在 Windows 下使用 `explorer.exe /select,"<file_path>"` 自动打开 `exports` 目录并高亮选中文件；
   - 在 `desktop/src/lib/engineApi.ts` 中新增 `openExportFolder`；
   - 在 `desktop/src/components/Step5Export.vue` 中调用 `openExportFolder(exportDocxResultPath)` 与 `openExportFolder(exportMdResultPath)`。

2. **多级节标题与正文粘连彻底拆解**：
   - 在 `engine/app/writing/writer.py` 的 `normalize_chapter_markdown` 中强化对多级节标题的粘连拆分算法（支持无空格、无标点、常见中文主题词与连词边界探测）；
   - 在 `engine/app/export/docx_builder.py` 的 `md_to_docx` 与 `_parse_md_line` 中加入前置规范化清洗与即时拆分，确保任何粘连文本均拆分为独立的 Heading 样式与正文段落。

3. **流水线验证与门禁通过**。
