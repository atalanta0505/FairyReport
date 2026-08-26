# 任务合同 V2-T13 v1 — 章节流式写作动态构思指示与左侧目录全章收起展开

- 状态：ACCEPTED（2026-08-26 Checker 验收通过，锁定 SHA `b1dd22a0c61df4b13457ef299fbfbe5e81dce862`）
- 依据：产品负责人反馈指示：
  1. “开始编写某章时，为什么在流式输出前大约有2~3分钟的“空白时间”才开始输出呢？要不要增加一些动态提示呢？用户可能觉得等待时间有点太长了。”
  2. “已完成的章，在左侧的导航栏里，允许全章收起和全章展开。”
- 精确起始 SHA：`37e63bad477af6d682095f9684691615c31a32f3`
- 候选交付 SHA：`b1dd22a0c61df4b13457ef299fbfbe5e81dce862`
- 工作树门禁：`git status --short` 必须干净

---

## 1. 唯一主要变化

1. **引擎层阶段与思考事件流式透传 (`engine/app/writing/`)**：
   - `llm_client.py`：在 `chat_stream_iter` 中捕获 `delta.get("reasoning_content")` / `delta.get("reasoning")` / `delta.get("thought")`，当有思考片段时以 JSON 结构 `{"type": "thought", "chunk": ...}` 透传；当有正文时正常产出文本或 `{"type": "content", "chunk": ...}`；
   - `router.py`：在 `_stream_chapter` 前置 yield 阶段指示事件（`stage: rag`、`stage: skeleton`、`stage: reasoning`）。
2. **桌面端 API 客户端与状态流转 (`desktop/src/`)**：
   - `desktop/src/lib/engineApi.ts`：`streamChapterWriting` 解析 `type === 'stage'` 与 `type === 'thought'` 消息，并通过扩展的回调通知 store；
   - `desktop/src/stores/project.ts`：管理 `writingProgress: ref<{ seq: number; stage: string; message: string; elapsedSeconds: number; thoughtText: string } | null>`，提供计时器并在正文产生或结束时清理。
3. **沉浸式动态构思指示卡片 (`desktop/src/components/Step3Writing.vue`)**：
   - 当正在生成且正文字数为 0 时，右侧主画布展示居中的高质感动态卡片：包含流水线阶段打勾步进指示、实时秒级计时器、动态呼吸波形、思维链推演折叠窗与说明提示；正文输出时平滑淡出并切换至排版打字机。
4. **左侧章节导航栏全章收起与展开 (`desktop/src/components/Step3Writing.vue`)**：
   - 单章：在每个有子标题的章节卡片中提供 `▼ 收起` / `▶ 展开` 切换；
   - 全局：在目录顶部提供 `[ ⊞ 全部展开 ]` / `[ ⊟ 全部收起 ]` 快捷操作；
   - 联动：选中或生成某章时自动展开。
5. **单元测试与产物**：
   - 更新 `engine/tests/test_writing_router.py` 与 `desktop/src/tests/project.test.ts`；
   - 重建 `desktop/dist/**`。

---

## 2. 允许修改

- `engine/app/writing/llm_client.py`
- `engine/app/writing/router.py`
- `desktop/src/lib/engineApi.ts`
- `desktop/src/stores/project.ts`
- `desktop/src/components/Step3Writing.vue`
- `engine/tests/test_writing_router.py`
- `desktop/src/tests/project.test.ts`
- `desktop/dist/**`
- `docs/dev-flow/tasks/V2-T13/**`

---

## 3. 禁止修改

- `backend/**`、根目录产品代码、`generic_knowledge/**`、`AGENTS.md`、`.gitignore`

---

## 4. 验收标准

- [ ] `python -m pytest engine/tests -q` 全绿。
- [ ] `npx vitest run`（`desktop/`）全绿。
- [ ] `npx vue-tsc --noEmit`、`npm run build`、`cargo check` 全绿。
- [ ] B 级实跑：
  1. 点击单章写作，右侧立即显示动态流水线指示卡片与实时计时器，正文到达后无缝切换排版视图；
  2. 左侧章节列表支持单章折叠收起/展开，以及顶部一键全部展开/全部收起。

---

## 5. 快速验证顺序

1. `python -m pytest engine/tests -q`
2. `npx vitest run`（workdir=`desktop`）
3. `npx vue-tsc --noEmit`（workdir=`desktop`）
4. `npm run build`（workdir=`desktop`）
