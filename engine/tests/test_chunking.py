"""分块逻辑与 FRL-003 边界保护测试。"""
from engine.app.materials import chunking


def test_chunk_empty_text():
    assert chunking.chunk_text("", "x.md", source_id="x.md") == []
    assert chunking.chunk_text("   \n  ", "x.md", source_id="x.md") == []


def test_chunk_has_source_id():
    chunks = chunking.chunk_text("# 标题\n正文内容", "x.md", source_id="x.md")
    assert chunks
    assert all(c["source_id"] == "x.md" for c in chunks)
    assert all("text" in c and c["source"] == "x.md" for c in chunks)


def test_frl003_overlap_clamped_no_infinite_loop():
    """FRL-003：overlap >= size 时钳制为 size//4，保证 _chunk_segment 前进不死循环。"""
    text = "段落内容。" * 50  # 足够长
    # overlap=2000 远大于 size=100，必须被钳制，否则死循环
    chunks = chunking._chunk_segment(text, "x.md", size=100, overlap=2000, source_id="x.md")
    assert len(chunks) > 1
    # 确认前进：每块起点递增
    starts = []
    cur = 0
    for ch in chunks:
        starts.append(cur)
        cur += len(ch["text"])  # 近似（忽略边界裁剪），仅验证不重复同一位置
    assert len(set(starts)) == len(starts)  # 无重复位置


def test_frl003_invalid_size_raises():
    """size <= 0 抛 ValueError。"""
    try:
        chunking._chunk_segment("x", "x.md", size=0, overlap=0, source_id="x.md")
        assert False, "should raise"
    except ValueError:
        pass
