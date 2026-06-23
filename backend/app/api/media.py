"""
旅行助手 源码组件。


"""

from __future__ import annotations

import time
from uuid import uuid4

from fastapi import APIRouter, Depends, UploadFile

from app.api.deps import files, providers
from app.schemas.media import CaptionResponse, CopywritingRequest, ImageRequest, MediaJobResponse, TextRequest
from app.services.file_service import ALLOWED_AUDIO_TYPES, ALLOWED_IMAGE_TYPES, FileService
from app.services.model_provider import ModelMessage, ProviderRegistry

router = APIRouter()


@router.post("/caption")
async def caption_image(
    image: UploadFile,
    registry: ProviderRegistry = Depends(providers),
    file_service: FileService = Depends(files),
) -> CaptionResponse:
    """说明：caption_image 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    trace_id = uuid4().hex
    started = time.perf_counter()
    path = await file_service.save_upload(image, "images", ALLOWED_IMAGE_TYPES)
    caption = await registry.resolve("auto").caption_image(path)
    return CaptionResponse(trace_id=trace_id, caption=caption, latency_ms=_latency(started))


@router.post("/copywriting")
async def copywriting(payload: CopywritingRequest, registry: ProviderRegistry = Depends(providers)) -> dict:
    """说明：copywriting 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    trace_id = uuid4().hex
    started = time.perf_counter()
    provider = registry.resolve("auto")
    answer = await provider.chat(
        [
            ModelMessage(role="system", content="You are a travel social-media copywriting expert. Always answer in Simplified Chinese."),
            ModelMessage(role="user", content=f"Always answer in Simplified Chinese. Generate {payload.style} style travel copy from this image caption: {payload.image_caption}"),
        ],
        model=registry.settings.qwen_fast_model,
    )
    return {"trace_id": trace_id, "session_id": payload.session_id, "answer": answer, "latency_ms": _latency(started)}


@router.post("/tts")
async def tts(payload: TextRequest, registry: ProviderRegistry = Depends(providers), file_service: FileService = Depends(files)) -> MediaJobResponse:
    """说明：tts 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    trace_id = uuid4().hex
    started = time.perf_counter()
    path = file_service.output_path(".mp3")
    output = await registry.resolve("auto").text_to_speech(payload.text, path)
    return MediaJobResponse(trace_id=trace_id, output_url=f"/outputs/{output.name}", message="TTS \u4efb\u52a1\u5df2\u5b8c\u6210\u3002", latency_ms=_latency(started))


@router.post("/image")
async def image(payload: ImageRequest, registry: ProviderRegistry = Depends(providers), file_service: FileService = Depends(files)) -> MediaJobResponse:
    """说明：image 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    trace_id = uuid4().hex
    started = time.perf_counter()
    path = file_service.output_path(".txt")
    output = await registry.resolve("auto").generate_image(payload.prompt, path)
    return MediaJobResponse(trace_id=trace_id, output_url=f"/outputs/{output.name}", message="\u6587\u751f\u56fe\u4efb\u52a1\u5df2\u5b8c\u6210\u3002", latency_ms=_latency(started))


@router.post("/audio/transcribe")
async def transcribe(
    audio: UploadFile,
    registry: ProviderRegistry = Depends(providers),
    file_service: FileService = Depends(files),
) -> dict:
    """说明：transcribe 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    trace_id = uuid4().hex
    started = time.perf_counter()
    path = await file_service.save_upload(audio, "audio", ALLOWED_AUDIO_TYPES)
    text = await registry.resolve("auto").transcribe_audio(path)
    return {"trace_id": trace_id, "text": text, "latency_ms": _latency(started)}


def _latency(started: float) -> int:
    """说明：_latency 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    return int((time.perf_counter() - started) * 1000)
