"""
旅行助手 源码组件。


"""

import asyncio

from app.services.session_store import SessionStore


def test_memory_profile_roundtrip():
    """说明：test_memory_profile_roundtrip 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    async def run():
        """说明：run 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        store = SessionStore()
        saved = await store.save_profile("u1", {"travel_style": "自然风光"})

        assert saved["travel_style"] == "自然风光"
        assert (await store.get_profile("u1"))["travel_style"] == "自然风光"

        await store.delete_profile("u1")
        assert await store.get_profile("u1") == {}

    asyncio.run(run())


def test_user_scoped_history_is_isolated():
    """说明：test_user_scoped_history_is_isolated 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    async def run():
        """说明：run 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        store = SessionStore()
        await store.append("s1", "user", "我喜欢轻松行程", user_id="u1")
        await store.append("s1", "user", "我喜欢购物", user_id="u2")

        assert (await store.history("s1", user_id="u1"))[0]["content"] == "我喜欢轻松行程"
        assert (await store.history("s1", user_id="u2"))[0]["content"] == "我喜欢购物"
        assert await store.list_sessions("u1") == ["s1"]

    asyncio.run(run())


def test_summary_and_fact_memory_roundtrip():
    """说明：test_summary_and_fact_memory_roundtrip 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    async def run():
        """说明：run 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        store = SessionStore()
        await store.save_summary("s1", "用户计划去杭州。", user_id="u1")
        await store.add_facts("u1", [{"text": "用户不喜欢购物", "source": "conversation"}])

        assert await store.get_summary("s1", user_id="u1") == "用户计划去杭州。"
        assert (await store.get_facts("u1"))[0]["text"] == "用户不喜欢购物"

    asyncio.run(run())
