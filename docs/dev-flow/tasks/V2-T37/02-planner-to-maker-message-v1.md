# Planner to Maker Message — V2-T37 v1

- **任务 ID**：V2-T37
- **合同版本**：v1 (`docs/dev-flow/tasks/V2-T37/01-planner-task-contract-v1.md`)
- **精确起始 SHA**：`1212dd34dc72c237df9cfc7a95d253ec351eeceb`

---

## 交付任务

请 Maker 依据合同实现以下改动：

1. **后端新增流式修订接口 `POST /writing/revise_stream` (`engine/app/writing/router.py`)**：
   - 支持 SSE 流式推送 `stage`、`thought`（模型深度思考链）、`chunk`、`done` 事件。

2. **前端流式 API 客户端与 Store 改造 (`desktop/src/lib/engineApi.ts`, `desktop/src/stores/project.ts`)**：
   - `engineApi.reviseChapterStream(baseUrl, req, onProgress)`；
   - `projectStore.runChapterRevisionStream`：流式接收 thought 并更新到 `revisionProgress` 状态；修订成功后原位更新正文，清空本章问题项并持久化；
   - 完成后重置 `revisingSeq = null`。

3. **Step4Review.vue 交互与文案优化**：
   - `handleDirectRevision` 调用 `runChapterRevisionStream`，在顶部修订心跳条中展示实时思考流；
   - 修订完成后自动关闭修订心跳条（`projectStore.revisingSeq = null`，关闭定时器）；
   - 将文案 `"🟢 发改委标准达标 ✓"` 调整为 `"🟢 已修改 ✓"`。

4. **通过 5 项全量门禁**。
