# Planner to Maker Message — V2-T41 v1

- **任务 ID**：V2-T41
- **合同版本**：v1 (`docs/dev-flow/tasks/V2-T41/01-planner-task-contract-v1.md`)
- **起始精确 SHA**：`5eeab7f98fd2b45b25bbc4caf0edf6a2858f807a`

---

## 交付任务

1. 在 `engine/app/export/router.py` 中添加 `POST /export/md` 接口，支持导出 `.md` 成果文件；
2. 在 `desktop/src/lib/engineApi.ts` 中暴露 `exportMd`；
3. 在 `desktop/src/components/Step5Export.vue` 中支持一键导出 Word (.docx) 与 Markdown (.md) 双格式；
4. 在 `engine/tests/test_export.py` 中补充 `/export/md` 单元测试，并跑通 5 项门禁。
