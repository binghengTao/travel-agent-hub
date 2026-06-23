"""
旅行助手 源码组件。


"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from app.core.config import Settings, get_settings


class SessionStore:
    """SessionStore"""
    def __init__(self, settings: Settings | None = None):
        """说明：__init__ 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        self.settings = settings or get_settings()
        self._redis = None
        self._memory: dict[str, list[dict[str, Any]]] = {}
        self._summaries: dict[str, str] = {}
        self._runs: dict[str, dict[str, Any]] = {}
        self._profiles: dict[str, dict[str, Any]] = {}
        self._facts: dict[str, list[dict[str, Any]]] = {}
        self._user_sessions: dict[str, set[str]] = {}

    async def connect(self) -> None:
        """说明：connect 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        try:
            import redis.asyncio as redis

            self._redis = redis.from_url(self.settings.redis_url, decode_responses=True)
            await self._redis.ping()
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning("Redis connection failed, using in-memory fallback: %s", exc)
            self._redis = None

    async def append(self, session_id: str, role: str, content: str, *, user_id: str | None = None) -> None:
        """说明：append 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        item = {"role": role, "content": content, "created_at": _now()}
        key = self._session_key(session_id, user_id)
        if self._redis:
            await self._redis.rpush(key, json.dumps(item, ensure_ascii=False))
            await self._redis.expire(key, self.settings.session_ttl_seconds)
            if user_id:
                await self._redis.sadd(self._sessions_key(user_id), session_id)
            return
        self._memory.setdefault(key, []).append(item)
        if user_id:
            self._user_sessions.setdefault(user_id, set()).add(session_id)

    async def history(self, session_id: str, limit: int = 20, *, user_id: str | None = None) -> list[dict[str, Any]]:
        """说明：history 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        key = self._session_key(session_id, user_id)
        if self._redis:
            raw = await self._redis.lrange(key, -limit, -1)
            return [json.loads(item) for item in raw]
        return self._memory.get(key, [])[-limit:]

    async def replace_history(self, session_id: str, messages: list[dict[str, Any]], *, user_id: str | None = None) -> None:
        """说明：replace_history 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        key = self._session_key(session_id, user_id)
        if self._redis:
            await self._redis.delete(key)
            if messages:
                await self._redis.rpush(key, *[json.dumps(item, ensure_ascii=False) for item in messages])
                await self._redis.expire(key, self.settings.session_ttl_seconds)
            return
        self._memory[key] = messages

    async def delete_history(self, session_id: str, *, user_id: str | None = None) -> None:
        """说明：delete_history 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        key = self._session_key(session_id, user_id)
        if self._redis:
            await self._redis.delete(key)
            return
        self._memory.pop(key, None)

    async def list_sessions(self, user_id: str) -> list[str]:
        """说明：list_sessions 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        if self._redis:
            return sorted(await self._redis.smembers(self._sessions_key(user_id)))
        return sorted(self._user_sessions.get(user_id, set()))

    async def get_summary(self, session_id: str, *, user_id: str | None = None) -> str:
        """说明：get_summary 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        key = self._summary_key(session_id, user_id)
        if self._redis:
            return await self._redis.get(key) or ""
        return self._summaries.get(key, "")

    async def save_summary(self, session_id: str, summary: str, *, user_id: str | None = None) -> None:
        """说明：save_summary 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        key = self._summary_key(session_id, user_id)
        if self._redis:
            await self._redis.setex(key, self.settings.session_ttl_seconds, summary)
            return
        self._summaries[key] = summary

    async def save_run(self, run_id: str, payload: dict[str, Any]) -> None:
        """说明：save_run 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        if self._redis:
            await self._redis.setex(self._run_key(run_id), self.settings.session_ttl_seconds, json.dumps(payload, ensure_ascii=False))
            return
        self._runs[run_id] = payload

    async def get_run(self, run_id: str) -> dict[str, Any] | None:
        """说明：get_run 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        if self._redis:
            raw = await self._redis.get(self._run_key(run_id))
            return json.loads(raw) if raw else None
        return self._runs.get(run_id)

    async def get_profile(self, user_id: str) -> dict[str, Any]:
        """说明：get_profile 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        if self._redis:
            raw = await self._redis.get(self._profile_key(user_id))
            return json.loads(raw) if raw else {}
        return self._profiles.get(user_id, {})

    async def save_profile(self, user_id: str, profile: dict[str, Any]) -> dict[str, Any]:
        """说明：save_profile 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        current = await self.get_profile(user_id)
        merged = {**current, **profile}
        if self._redis:
            await self._redis.set(self._profile_key(user_id), json.dumps(merged, ensure_ascii=False))
            return merged
        self._profiles[user_id] = merged
        return merged

    async def delete_profile(self, user_id: str) -> None:
        """说明：delete_profile 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        if self._redis:
            await self._redis.delete(self._profile_key(user_id))
            return
        self._profiles.pop(user_id, None)

    async def get_facts(self, user_id: str, limit: int = 20) -> list[dict[str, Any]]:
        """说明：get_facts 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        if self._redis:
            raw = await self._redis.lrange(self._facts_key(user_id), -limit, -1)
            return [json.loads(item) for item in raw]
        return self._facts.get(user_id, [])[-limit:]

    async def add_facts(self, user_id: str, facts: list[dict[str, Any]]) -> None:
        """说明：add_facts 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        if not facts:
            return
        existing = await self.get_facts(user_id, limit=200)
        existing_text = {item.get("text") for item in existing}
        new_items = [item for item in facts if item.get("text") and item.get("text") not in existing_text]
        if not new_items:
            return
        if self._redis:
            await self._redis.rpush(self._facts_key(user_id), *[json.dumps(item, ensure_ascii=False) for item in new_items])
            await self._redis.ltrim(self._facts_key(user_id), -200, -1)
            return
        self._facts.setdefault(user_id, []).extend(new_items)
        self._facts[user_id] = self._facts[user_id][-200:]

    async def close(self) -> None:
        """说明：close 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        if self._redis:
            await self._redis.close()

    @staticmethod
    def _session_key(session_id: str, user_id: str | None = None) -> str:
        """说明：_session_key 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        if user_id:
            return f"travelai:session:{user_id}:{session_id}:messages"
        return f"travelai:session:{session_id}"

    @staticmethod
    def _summary_key(session_id: str, user_id: str | None = None) -> str:
        """说明：_summary_key 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        if user_id:
            return f"travelai:session:{user_id}:{session_id}:summary"
        return f"travelai:session:{session_id}:summary"

    @staticmethod
    def _sessions_key(user_id: str) -> str:
        """说明：_sessions_key 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        return f"travelai:user:{user_id}:sessions"

    @staticmethod
    def _run_key(run_id: str) -> str:
        """说明：_run_key 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        return f"travelai:agent:run:{run_id}"

    @staticmethod
    def _profile_key(user_id: str) -> str:
        """说明：_profile_key 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        return f"travelai:user:{user_id}:profile"

    @staticmethod
    def _facts_key(user_id: str) -> str:
        """说明：_facts_key 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        return f"travelai:user:{user_id}:facts"


def _now() -> str:
    """说明：_now 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    return datetime.now(timezone.utc).isoformat()
