# 任务合同 V2-T43 v1 — 导出文件夹直达与高亮定位、节标题与正文粘连彻底拆解

- **状态**：READY_FOR_MAKER
- **依据**：产品负责人反馈的 2 项明确改进要求：
  1. “打开导出文件夹”应直接打开导出的 docx/md 文件所在 `exports/` 目录（并高亮选中该文件），而不是项目的输入资料 files 文件夹；
  2. 彻底解决导出的 Word 文档中多级节标题与正文无空格粘连（如 `2.3.1 宏观层面必要性从宏观层面看...`）的问题，确保所有节标题 100% 独立成为 Heading 样式，正文首行缩进独立成段。
- **精确起始 SHA**：`0487fbdbc6b6d4f90f2e8cc916509ff878381850`
- **工作树门禁**：干净工作树

---

## 1. 允许修改

- `engine/app/export/router.py`
- `engine/app/export/docx_builder.py`
- `engine/app/writing/writer.py`
- `desktop/src/components/Step5Export.vue`
- `desktop/src/lib/engineApi.ts`
- `desktop/src/lib/markdown.ts`
- `engine/tests/**`
- `desktop/src/tests/**`
- `docs/dev-flow/tasks/V2-T43/**`

---

## 2. 验收标准

- [ ] 后端提供 `POST /export/open-folder` 接口，支持在 Windows 资源管理器中打开 exports 目录并精准 `/select` 选中导出的 `.docx` 或 `.md` 成果文件；
- [ ] 前端 Step 5 导出成功后，点击“📂 打开导出文件夹”能够直接打开 exports 目录并高亮选中当前导出的文件；
- [ ] 多级节标题与正文粘连（无空格、带冒号、无 #、带中文连词等所有形态）在 `normalize_chapter_markdown` 和 `docx_builder.py` 中 100% 自动拆分为独立标题行与正文段落；
- [ ] 5 项全量流水线门禁全部绿灯通过。
