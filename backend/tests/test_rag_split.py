"""
旅行助手 源码组件。


"""

from app.rag.indexer import split_text


def test_split_text_overlaps():
    """说明：test_split_text_overlaps 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    chunks = split_text("a" * 120, chunk_size=50, overlap=10)
    assert len(chunks) == 3
    assert chunks[0][-10:] == chunks[1][:10]
