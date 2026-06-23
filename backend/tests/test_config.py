"""
旅行助手 源码组件。


"""

from app.core.config import get_settings


def test_settings_paths_are_resolved():
    """说明：test_settings_paths_are_resolved 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    settings = get_settings()
    assert settings.dataset_dir.name == "dataset"
    assert settings.qwen_chat_model == "qwen3.6-plus"
