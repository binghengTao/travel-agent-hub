"""
旅行助手 源码组件。


"""

import asyncio

from app.core.config import Settings
from app.services.context_memory import ContextBuilder, estimate_tokens
from app.services.session_store import SessionStore


def test_context_compression_and_budget():
    """说明：test_context_compression_and_budget 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    async def run():
        """说明：run 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        settings = Settings(
            max_context_tokens=220,
            recent_history_tokens=70,
            memory_summary_tokens=45,
            rag_context_tokens=45,
            web_context_tokens=35,
            compression_trigger_tokens=120,
        )
        store = SessionStore(settings)
        builder = ContextBuilder(settings, providers=None)

        for index in range(30):
            await store.append(
                "s1",
                "user",
                f"第 {index} 轮：我喜欢轻松行程，不喜欢购物，预算中等，想去杭州西湖。"
                "请记住这些偏好并在后续规划中使用。",
                user_id="u1",
            )
            await store.append("s1", "assistant", "好的，我会记住你的偏好。", user_id="u1")

        await builder.compressor.compress_if_needed(user_id="u1", session_id="s1", store=store)

        summary = await store.get_summary("s1", user_id="u1")
        facts = await store.get_facts("u1")
        recent = await store.history("s1", limit=120, user_id="u1")
        context = await builder.build(
            user_id="u1",
            session_id="s1",
            store=store,
            current_message="帮我安排杭州两天轻松路线",
            rag_sources=[{"source": "杭州旅游攻略.pdf", "preview": "西湖适合轻松游览"}],
            web_sources=[{"title": "西湖开放信息", "snippet": "请以景区官方信息为准"}],
        )

        assert summary
        assert facts
        assert len(recent) < 60
        assert estimate_tokens(context.prompt_context) <= settings.max_context_tokens
        assert "长期事实记忆" in context.prompt_context

    asyncio.run(run())
