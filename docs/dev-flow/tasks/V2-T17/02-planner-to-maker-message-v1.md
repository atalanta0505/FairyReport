# Planner 至 Maker 任务派发 — V2-T17 第 1 轮

- **任务 ID**：`V2-T17` 第 1 轮
- **有效合同**：`docs/dev-flow/tasks/V2-T17/01-planner-task-contract-v1.md`
- **起始 SHA**：`b8ff383bca9bc255df27d5320ee13589b25208f3`

---

### 【核心实现要点】

1. **`engine/app/embedding.py`（嵌入模型本地化优先与持久化缓存）**：
   - 升级 `FastEmbedEmbedder._ensure_model()`：
     ```python
     def _ensure_model(self):
         if self._model is None:
             from fastembed import TextEmbedding
             from pathlib import Path
             from .config import settings

             # 1. 优先使用仓库内预置或下载好的模型（100% 离线，毫秒级就绪）
             repo_model_dir = Path(__file__).resolve().parent.parent.parent / "data" / "fastembed_models"
             data_model_dir = Path(settings.engine_data_dir) / "models" / "fastembed"

             specific_path = None
             if repo_model_dir.exists() and (repo_model_dir / "model_optimized.onnx").exists():
                 specific_path = str(repo_model_dir)
             elif data_model_dir.exists() and (data_model_dir / "model_optimized.onnx").exists():
                 specific_path = str(data_model_dir)

             if specific_path:
                 self._model = TextEmbedding(model_name=self._model_name, specific_model_path=specific_path)
             else:
                 cache_dir = str(Path(settings.engine_data_dir) / "models")
                 self._model = TextEmbedding(model_name=self._model_name, cache_dir=cache_dir)
     ```
   - 确保完全兼容打桩 `DeterministicStubEmbedder` 与现有单元测试。

2. **`engine/app/materials/router.py`（单文件摄取异常保护与事务回滚）**：
   - 在 `_process_file` 中增加 try-except 保护：
     ```python
     def _process_file(
         session: Session,
         proj: models.Project,
         store: ProjectVectorStore,
         embedder,
         fpath: str,
         copy_dest_dir: str | None = None,
     ) -> IngestResult:
         filename = os.path.basename(fpath)
         ext = os.path.splitext(filename)[1].lower()
         size_bytes = os.path.getsize(fpath) if os.path.exists(fpath) else 0

         try:
             md_text = to_markdown(fpath)
             if not md_text or not md_text.strip():
                 return IngestResult(
                     source_id=filename,
                     filename=filename,
                     ext=ext,
                     chunk_count=0,
                     size_bytes=size_bytes,
                     status="error",
                     error="转换后内容为空",
                 )

             chunks = chunk_text(md_text, source_name=filename, source_id=filename)
             if not chunks:
                 return IngestResult(
                     source_id=filename,
                     filename=filename,
                     ext=ext,
                     chunk_count=0,
                     size_bytes=size_bytes,
                     status="error",
                     error="切片后无内容",
                 )

             embeddings = embedder.encode([c["text"] for c in chunks])
             store.delete_by_source(filename)
             store.upsert(chunks, embeddings)

             if copy_dest_dir:
                 dest_path = os.path.join(copy_dest_dir, filename)
                 if os.path.abspath(fpath) != os.path.abspath(dest_path):
                     shutil.copy2(fpath, dest_path)

             existing = session.execute(
                 select(models.Material).where(
                     models.Material.project_id == proj.id,
                     models.Material.source_id == filename,
                 )
             ).scalars().first()
             if existing:
                 existing.filename = filename
                 existing.ext = ext
                 existing.chunk_count = len(chunks)
                 existing.size_bytes = size_bytes
             else:
                 session.add(
                     models.Material(
                         project_id=proj.id,
                         source_id=filename,
                         filename=filename,
                         ext=ext,
                         chunk_count=len(chunks),
                         size_bytes=size_bytes,
                     )
                 )
             session.commit()

             return IngestResult(
                 source_id=filename,
                 filename=filename,
                 ext=ext,
                 chunk_count=len(chunks),
                 size_bytes=size_bytes,
                 status="ok",
                 error=None,
             )
         except Exception as e:
             session.rollback()
             return IngestResult(
                 source_id=filename,
                 filename=filename,
                 ext=ext,
                 chunk_count=0,
                 size_bytes=size_bytes,
                 status="error",
                 error=f"摄取失败: {str(e)}",
             )
     ```

3. **门禁与交付**：
   - 运行全部快速验证链（pytest, vitest, vue-tsc, build, cargo check）；
   - 提交代码与 `docs/dev-flow/tasks/V2-T17/rounds/01/maker-completion.md`。
