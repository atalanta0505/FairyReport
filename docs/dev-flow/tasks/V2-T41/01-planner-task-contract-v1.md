# 任务合同 V2-T41 v1 — 成果导出支持 Word (.docx) 与 Markdown (.md) 双格式一键导出

- **状态**：READY_FOR_MAKER
- **依据**：产品负责人要求确认并完善 Step 5 报告导出功能，原生支持 `.docx` 与 `.md` 双格式完整导出。
- **精确起始 SHA**：`5eeab7f98fd2b45b25bbc4caf0edf6a2858f807a`
- **工作树门禁**：干净工作树

---

## 1. 唯一主要变化

1. **后端导出路由增加 `/export/md` 原生导出接口 (`engine/app/export/router.py`)**：
   - 支持 `POST /export/md` 请求，将全书章节合并、引用按首次出现顺序全局编号 `[1][2]...` 并在文末自动生成 GB/T 7714 规范的《参考文献》章；
   - 导出为标准 `.md` 文件至 `exports/` 目录，返回保存路径、大小与文本内容。

2. **前端 API 接入 `exportMd` (`desktop/src/lib/engineApi.ts`)**：
   - 增加 `ExportMdRequest` 类型与 `exportMd` 函数。

3. **Step 5 导出界面增加 Word (.docx) 与 Markdown (.md) 双格式一键导出卡片 (`desktop/src/components/Step5Export.vue`)**：
   - 提供 🚀 一键导出 Word 报告 (.docx)；
   - 提供 📝 一键导出 Markdown 报告 (.md)（直接落地文件并在浏览器/客户端中提供直接下载与路径查看）；
   - 提供 📋 复制全书 Markdown 源码（含学术编号）。

4. **单测与 5 项流水线门禁 (`engine/tests/test_export.py`, Vitest, vue-tsc, build, cargo check)**。

---

## 2. 允许修改

- `engine/app/export/router.py`
- `engine/tests/test_export.py`
- `desktop/src/lib/engineApi.ts`
- `desktop/src/components/Step5Export.vue`
- `docs/dev-flow/tasks/V2-T41/**`

---

## 3. 验收标准

- [ ] `/export/md` 接口可用，能正确生成包含全局学术编号与文末参考文献章的 `.md` 文件；
- [ ] 前端 Step 5 界面同时支持 `.docx` 和 `.md` 格式一键导出；
- [ ] 5 项全量流水线门禁全部绿灯通过。
