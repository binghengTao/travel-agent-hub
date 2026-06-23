"""
旅行助手 源码组件。


"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.config import Settings, get_settings
from app.services.model_provider import ModelMessage, ProviderRegistry
from app.services.session_store import SessionStore


@dataclass
class ContextBundle:
    """ContextBundle"""
    # prompt_context 是最终送入模型的压缩上下文，其余字段用于前端/日志解释上下文来源。
    prompt_context: str
    profile: dict[str, Any] = field(default_factory=dict)
    facts: list[dict[str, Any]] = field(default_factory=list)
    summary: str = ""
    recent_messages: list[dict[str, Any]] = field(default_factory=list)
    token_estimate: int = 0


class ContextBuilder:
    """Builds bounded, explainable context for chat and agent calls."""

    def __init__(self, settings: Settings | None = None, providers: ProviderRegistry | None = None):
        """说明：__init__ 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        self.settings = settings or get_settings()
        self.providers = providers
        self.compressor = MemoryCompressor(self.settings, providers)

    async def build(
        self,
        *,
        user_id: str,
        session_id: str,
        store: SessionStore,
        current_message: str = "",
        profile: dict[str, Any] | None = None,
        rag_sources: list[dict[str, Any]] | None = None,
        web_sources: list[dict[str, Any]] | None = None,
        tool_results: list[dict[str, Any]] | None = None,
    ) -> ContextBundle:
        """说明：build 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        # 构造上下文前先尝试压缩旧历史，保证后续拼装不会无限膨胀。
        await self.compressor.compress_if_needed(user_id=user_id, session_id=session_id, store=store)
        profile = profile if profile is not None else await store.get_profile(user_id)
        facts = await store.get_facts(user_id, limit=20)
        summary = await store.get_summary(session_id, user_id=user_id)
        recent_messages = await store.history(session_id, limit=20, user_id=user_id)

        # sections 的顺序就是上下文优先级：用户画像和事实优先，RAG/网页/工具证据按预算补充。
        sections = [
            ("用户画像", _jsonish(profile), self.settings.memory_summary_tokens),
            ("长期事实记忆", _facts_text(facts), self.settings.memory_summary_tokens),
            ("会话摘要", summary, self.settings.memory_summary_tokens),
            ("最近对话", _messages_text(recent_messages), self.settings.recent_history_tokens),
            ("本轮问题", current_message, 1000),
            ("RAG 证据", _jsonish(rag_sources or []), self.settings.rag_context_tokens),
            ("网页证据", _jsonish(web_sources or []), self.settings.web_context_tokens),
            ("工具结果", _jsonish(tool_results or []), self.settings.web_context_tokens),
        ]
        chunks: list[str] = []
        used = 0
        for title, content, section_budget in sections:
            if not content:
                continue
            title_tokens = estimate_tokens(f"## {title}\n")
            # 每段先受自己的预算限制，再受全局 MAX_CONTEXT_TOKENS 限制。
            allowed = max(min(section_budget, self.settings.max_context_tokens - used - title_tokens), 0)
            if allowed <= 0:
                break
            clipped = clip_to_tokens(content, allowed)
            section_text = f"## {title}\n{clipped}"
            used += estimate_tokens(section_text)
            chunks.append(section_text)

        prompt_context = clip_to_tokens("\n\n".join(chunks), self.settings.max_context_tokens)
        return ContextBundle(
            prompt_context=prompt_context,
            profile=profile,
            facts=facts,
            summary=summary,
            recent_messages=recent_messages,
            token_estimate=estimate_tokens(prompt_context),
        )


class MemoryCompressor:
    """MemoryCompressor"""
    def __init__(self, settings: Settings | None = None, providers: ProviderRegistry | None = None):
        """说明：__init__ 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        self.settings = settings or get_settings()
        self.providers = providers

    async def compress_if_needed(self, *, user_id: str, session_id: str, store: SessionStore) -> None:
        """说明：compress_if_needed 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        # 每次都先抽取最近消息中的显式偏好，避免用户刚说的约束被压缩窗口漏掉。
        messages = await store.history(session_id, limit=120, user_id=user_id)
        await store.add_facts(user_id, _extract_facts(messages[-20:]))
        if estimate_tokens(_messages_text(messages)) <= self.settings.compression_trigger_tokens:
            return

        # recent 保留原文，old_messages 压成摘要；这样长对话既有近因细节，也有远期记忆。
        recent: list[dict[str, Any]] = []
        recent_tokens = 0
        for item in reversed(messages):
            item_tokens = estimate_tokens(str(item.get("content", "")))
            if recent and recent_tokens + item_tokens > self.settings.recent_history_tokens:
                break
            recent.append(item)
            recent_tokens += item_tokens
        recent.reverse()

        old_messages = messages[: max(len(messages) - len(recent), 0)]
        if not old_messages:
            return

        old_text = _messages_text(old_messages)
        existing_summary = await store.get_summary(session_id, user_id=user_id)
        summary = await self._summarize(existing_summary, old_text)
        facts = _extract_facts(old_messages)
        await store.save_summary(session_id, summary, user_id=user_id)
        await store.add_facts(user_id, facts)
        await store.replace_history(session_id, recent, user_id=user_id)

    async def _summarize(self, existing_summary: str, old_text: str) -> str:
        """说明：_summarize 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        provider = self.providers.resolve("auto") if self.providers else None
        if provider and provider.configured:
            # 有真实模型时使用 Qwen/兼容模型压缩摘要；无 Key 时走确定性截断，不阻塞主流程。
            prompt = (
                "请把以下旧对话压缩为中文会话摘要，保留用户偏好、约束、目的地、预算、重要事实和未完成任务。"
                "不要超过 800 字。\n\n"
                f"已有摘要:\n{existing_summary}\n\n旧对话:\n{clip_to_tokens(old_text, 6000)}"
            )
            try:
                return await provider.chat([ModelMessage(role="user", content=prompt)], model=self.settings.qwen_fast_model)
            except Exception as exc:
                import logging
                logging.getLogger(__name__).warning("Memory summarization via LLM failed, falling back to truncation: %s", exc)

        merged = "\n".join(part for part in [existing_summary, old_text] if part)
        return clip_to_tokens(merged, self.settings.memory_summary_tokens)


def estimate_tokens(text: str) -> int:
    """说明：estimate_tokens 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    # 当前项目不绑定具体 tokenizer，先用轻量估算控制预算；后续可替换为模型 tokenizer。
    cjk = sum(1 for char in text if "\u4e00" <= char <= "\u9fff")
    ascii_chars = len(text) - cjk
    return max(cjk // 2 + ascii_chars // 4, 1) if text else 0


def clip_to_tokens(text: str, max_tokens: int) -> str:
    """说明：clip_to_tokens 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    # 使用二分截断，避免逐字符循环在长上下文下变慢。
    if max_tokens <= 0:
        return ""
    if estimate_tokens(text) <= max_tokens:
        return text
    suffix = "\n[内容已按上下文预算截断]"
    if estimate_tokens(suffix) >= max_tokens:
        suffix = ""
    allowed = max(max_tokens - estimate_tokens(suffix), 1)
    low, high = 0, len(text)
    best = ""
    while low <= high:
        mid = (low + high) // 2
        candidate = text[:mid].rstrip()
        if estimate_tokens(candidate) <= allowed:
            best = candidate
            low = mid + 1
        else:
            high = mid - 1
    result = (best + suffix).strip()
    while result and estimate_tokens(result) > max_tokens:
        if result.endswith(suffix.strip()):
            result = result[: -len(suffix.strip())].rstrip()
        else:
            result = result[:-1].rstrip()
    return result


def _messages_text(messages: list[dict[str, Any]]) -> str:
    """说明：_messages_text 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    return "\n".join(f"{item.get('role', 'unknown')}: {item.get('content', '')}" for item in messages)


def _facts_text(facts: list[dict[str, Any]]) -> str:
    """说明：_facts_text 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    return "\n".join(f"- {item.get('text')}" for item in facts if item.get("text"))


def _jsonish(value: Any) -> str:
    """说明：_jsonish 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    if not value:
        return ""
    return str(value)


def _extract_facts(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """说明：_extract_facts 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    facts = []
    keywords = [
        "喜欢",
        "不喜欢",
        "偏好",
        "预算",
        "酒店",
        "餐饮",
        "忌口",
        "出发地",
        "目的地",
        "节奏",
        "购物",
    ]
    for item in messages:
        content = str(item.get("content", ""))
        if item.get("role") == "user" and any(keyword in content for keyword in keywords):
            facts.append({"text": content[:240], "source": "conversation"})
    return facts
