"""
旅行助手 源码组件。


"""

from __future__ import annotations

import asyncio
import hashlib
import math
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncIterator, Iterable, Literal

from app.core.config import Settings, get_settings


ProviderName = Literal["qwen", "deepseek", "local"]


@dataclass
class ModelMessage:
    """ModelMessage"""
    role: str
    content: str


class ModelProvider:
    """ModelProvider"""
    name: ProviderName = "qwen"

    def __init__(self, settings: Settings):
        """说明：__init__ 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        self.settings = settings

    @property
    def configured(self) -> bool:
        """说明：configured 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        return False

    async def chat(self, messages: list[ModelMessage | dict], model: str | None = None, temperature: float = 0.3) -> str:
        """说明：chat 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        # 基类提供离线兜底回答，确保没有 API Key 时项目仍能启动和演示接口结构。
        return self._offline_answer(messages, model)

    async def stream(
        self,
        messages: list[ModelMessage | dict],
        model: str | None = None,
        temperature: float = 0.3,
    ) -> AsyncIterator[str]:
        """说明：stream 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        answer = await self.chat(messages, model=model, temperature=temperature)
        for token in _chunk_text(answer):
            await asyncio.sleep(0)
            yield token

    async def embed(self, texts: list[str], model: str | None = None) -> list[list[float]]:
        """说明：embed 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        # 稳定 hash embedding 不是语义模型，但可让 RAG 流程在无 Key 环境下完成端到端测试。
        return [stable_embedding(text, self.settings.embedding_dimension) for text in texts]

    async def rerank(self, query: str, documents: list[str], top_k: int) -> list[tuple[int, float]]:
        """说明：rerank 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        query_terms = set(_tokenize(query))
        scored: list[tuple[int, float]] = []
        for index, doc in enumerate(documents):
            doc_terms = set(_tokenize(doc))
            overlap = len(query_terms & doc_terms)
            density = overlap / max(len(query_terms), 1)
            scored.append((index, density))
        return sorted(scored, key=lambda item: item[1], reverse=True)[:top_k]

    async def caption_image(self, image_path: Path) -> str:
        """说明：caption_image 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        return f"已接收图片 {image_path.name}。当前未配置视觉模型，无法真实识图。"

    async def generate_image(self, prompt: str, output_path: Path) -> Path:
        """说明：generate_image 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        output_path.write_text(f"Image generation placeholder for: {prompt}", encoding="utf-8")
        return output_path

    async def text_to_speech(self, text: str, output_path: Path) -> Path:
        """说明：text_to_speech 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        output_path.write_bytes(b"")
        return output_path

    async def transcribe_audio(self, audio_path: Path) -> str:
        """说明：transcribe_audio 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        return f"已接收音频 {audio_path.name}。当前未配置 ASR 模型，无法真实转写。"

    def _offline_answer(self, messages: list[ModelMessage | dict], model: str | None) -> str:
        """说明：_offline_answer 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        normalized = normalize_messages(messages)
        user_text = next((m["content"] for m in reversed(normalized) if m["role"] == "user"), "")
        return (
            f"【离线模式】模型 provider `{self.name}` 尚未配置可用 API key 或本地 endpoint。\n\n"
            f"我已收到问题：{user_text}\n\n"
            "接入 `.env` 中的 Qwen/DeepSeek/Local OpenAI-compatible 配置后，此处会返回真实模型结果。"
        )


class OpenAICompatibleProvider(ModelProvider):
    """OpenAICompatibleProvider"""
    name: ProviderName = "qwen"

    def __init__(self, settings: Settings, *, api_key: str | None, base_url: str | None, default_model: str):
        """说明：__init__ 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        super().__init__(settings)
        self.api_key = api_key
        self.base_url = base_url
        self.default_model = default_model
        self._client = None

    @property
    def configured(self) -> bool:
        """说明：configured 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        return bool(self.api_key and self.base_url)

    def _get_client(self):
        """说明：_get_client 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        if self._client is None:
            from openai import AsyncOpenAI

            # DashScope、DeepSeek、本地模型都通过 OpenAI-compatible SDK 统一接入。
            self._client = AsyncOpenAI(api_key=self.api_key or "local", base_url=self.base_url)
        return self._client

    async def chat(self, messages: list[ModelMessage | dict], model: str | None = None, temperature: float = 0.3) -> str:
        """说明：chat 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        if not self.configured:
            return await super().chat(messages, model=model, temperature=temperature)
        client = self._get_client()
        response = await client.chat.completions.create(
            model=model or self.default_model,
            messages=normalize_messages(messages),
            temperature=temperature,
        )
        return response.choices[0].message.content or ""

    async def stream(
        self,
        messages: list[ModelMessage | dict],
        model: str | None = None,
        temperature: float = 0.3,
    ) -> AsyncIterator[str]:
        """说明：stream 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        if not self.configured:
            async for token in super().stream(messages, model=model, temperature=temperature):
                yield token
            return
        client = self._get_client()
        stream = await client.chat.completions.create(
            model=model or self.default_model,
            messages=normalize_messages(messages),
            temperature=temperature,
            stream=True,
        )
        async for event in stream:
            token = event.choices[0].delta.content
            if token:
                yield token

    async def embed(self, texts: list[str], model: str | None = None) -> list[list[float]]:
        """说明：embed 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        if not self.configured:
            return await super().embed(texts, model=model)
        client = self._get_client()
        try:
            response = await client.embeddings.create(model=model or self.settings.qwen_embedding_model, input=texts)
            return [item.embedding for item in response.data]
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning("OpenAI embed failed, falling back to hash: %s", exc)
            return await super().embed(texts, model=model)


class QwenProvider(OpenAICompatibleProvider):
    """QwenProvider"""
    name: ProviderName = "qwen"

    def __init__(self, settings: Settings):
        """说明：__init__ 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        super().__init__(
            settings,
            api_key=settings.qwen_api_key,
            base_url=settings.qwen_base_url,
            default_model=settings.qwen_chat_model,
        )


class DeepSeekProvider(OpenAICompatibleProvider):
    """DeepSeekProvider"""
    name: ProviderName = "deepseek"

    def __init__(self, settings: Settings):
        """说明：__init__ 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        super().__init__(
            settings,
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            default_model=settings.deepseek_chat_model,
        )


class LocalOpenAIProvider(OpenAICompatibleProvider):
    """LocalOpenAIProvider"""
    name: ProviderName = "local"

    def __init__(self, settings: Settings):
        """说明：__init__ 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        super().__init__(
            settings,
            api_key=settings.local_openai_api_key,
            base_url=settings.local_openai_base_url,
            default_model=settings.local_chat_model,
        )


class ProviderRegistry:
    """ProviderRegistry"""
    def __init__(self, settings: Settings | None = None):
        """说明：__init__ 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        self.settings = settings or get_settings()
        self.providers: dict[ProviderName, ModelProvider] = {
            "qwen": QwenProvider(self.settings),
            "deepseek": DeepSeekProvider(self.settings),
            "local": LocalOpenAIProvider(self.settings),
        }

    def resolve(self, provider: str = "auto", *, reasoning: bool = False) -> ModelProvider:
        """说明：resolve 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        if provider in self.providers:
            return self.providers[provider]  # type: ignore[index]
        preferred = self.providers[self.settings.default_provider]
        if preferred.configured:
            return preferred
        # 用户未配置默认 provider 时，自动寻找任意可用 provider；都不可用则返回默认 provider 的离线兜底。
        for candidate in self.providers.values():
            if candidate.configured:
                return candidate
        return preferred

    def model_catalog(self) -> dict:
        """说明：model_catalog 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        return {
            "default_provider": self.settings.default_provider,
            "providers": {name: {"configured": provider.configured} for name, provider in self.providers.items()},
            "models": {
                "chat": self.settings.qwen_chat_model,
                "fast": self.settings.qwen_fast_model,
                "reasoning": self.settings.qwen_reasoning_model,
                "deepseek_chat": self.settings.deepseek_chat_model,
                "deepseek_reasoning": self.settings.deepseek_reasoning_model,
                "embedding": self.settings.qwen_embedding_model,
                "rerank": self.settings.qwen_rerank_model,
                "vision": self.settings.qwen_vision_model,
                "image": self.settings.qwen_image_model,
                "tts": self.settings.qwen_tts_model,
                "asr": self.settings.qwen_asr_model,
                "local": self.settings.local_chat_model,
            },
        }


def stable_embedding(text: str, dimension: int = 1024) -> list[float]:
    """说明：stable_embedding 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    # 使用 sha256 派生确定性向量，保证测试结果可重复，避免随机向量导致排序抖动。
    vector = [0.0] * dimension
    tokens = _tokenize(text)
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "little") % dimension
        sign = 1 if digest[4] % 2 == 0 else -1
        vector[index] += sign * (1.0 + len(token) / 20.0)
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


def cosine(a: Iterable[float], b: Iterable[float]) -> float:
    """说明：cosine 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    a_list = list(a)
    b_list = list(b)
    denom = math.sqrt(sum(x * x for x in a_list)) * math.sqrt(sum(x * x for x in b_list))
    if denom == 0:
        return 0.0
    return sum(x * y for x, y in zip(a_list, b_list)) / denom


def _tokenize(text: str) -> list[str]:
    """说明：_tokenize 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    chunks: list[str] = []
    current = []
    for char in text.lower():
        if "\u4e00" <= char <= "\u9fff":
            if current:
                chunks.append("".join(current))
                current.clear()
            chunks.append(char)
        elif char.isalnum():
            current.append(char)
        else:
            if current:
                chunks.append("".join(current))
                current.clear()
    if current:
        chunks.append("".join(current))
    return chunks


def _chunk_text(text: str, size: int = 16) -> list[str]:
    """说明：_chunk_text 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    return [text[index : index + size] for index in range(0, len(text), size)]


def normalize_messages(messages: list[ModelMessage | dict]) -> list[dict[str, str]]:
    """说明：normalize_messages 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    normalized = []
    for item in messages:
        if isinstance(item, ModelMessage):
            normalized.append({"role": item.role, "content": item.content})
        else:
            normalized.append({"role": str(item.get("role", "user")), "content": str(item.get("content", ""))})
    return normalized
