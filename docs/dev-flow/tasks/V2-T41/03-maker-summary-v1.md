# Maker 实施总结 — V2-T41 v1

- **任务 ID**：V2-T41
- **合同版本**：v1 (`docs/dev-flow/tasks/V2-T41/01-planner-task-contract-v1.md`)
- **起始 SHA**：`5eeab7f98fd2b45b25bbc4caf0edf6a2858f807a`

---

## 1. 实际变更说明

1. **后端导出路由增加 `/export/md` 原生导出接口 (`engine/app/export/router.py`)**：
   - 新增 `ExportMdRequest` 与 `POST /export/md` 接口，支持将全书章节合并、引用按首次出现顺序全局编号 `[1][2]...` 并在文末自动生成 GB/T 7714 规范的《参考文献》章；
   - 导出为标准 `.md` 文件并返回本地保存路径、文件字节数与全书内容。

2. **前端 API 接入 `exportMd` (`desktop/src/lib/engineApi.ts`)**：
   - 暴露 `ExportMdRequest` 类型与 `exportMd` 函数。

3. **Step 5 导出界面增加 Word (.docx) 与 Markdown (.md) 双格式一键导出卡片 (`desktop/src/components/Step5Export.vue`)**：
   - 🚀 一键导出 Word 报告 (.docx)；
   - 💾 一键导出 Markdown 报告 (.md)；
   - 📋 复制全书 Markdown 源码（含学术编号与参考文献章）；
   - 📂 导出完成后可一键打开成果文件夹。

4. **单测增强 (`engine/tests/test_export.py`)**：
   - 增加了 `test_export_md_success` 单元测试，并通过全部 10 项导出测试。

---

## 2. 5 项全量流水线门禁验证

| 门禁项 | 命令 | 结果 |
| :--- | :--- | :---: |
| **前端单元测试** | `npx vitest run` | **178/178 passed** (6 files) |
| **Vue 类型检查** | `npx vue-tsc --noEmit` | **0 errors** |
| **前端打包构建** | `npm run build` | **Build passed** |
| **后端单元测试** | `python -m pytest engine/tests/test_export.py` | **10/10 passed** (0 failed) |
| **Rust 壳层编译** | `cargo check` | **dev profile passed (0.90s)** |
