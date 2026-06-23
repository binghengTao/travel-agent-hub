"""
旅行助手 源码组件。


"""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.core.config import Settings, get_settings


ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}
ALLOWED_AUDIO_TYPES = {"audio/mpeg", "audio/wav", "audio/x-wav", "audio/mp4", "audio/webm"}
ALLOWED_PDF_TYPES = {"application/pdf"}


class FileService:
    """FileService"""
    def __init__(self, settings: Settings | None = None):
        """说明：__init__ 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        self.settings = settings or get_settings()

    async def save_upload(self, upload: UploadFile, category: str, allowed_types: set[str]) -> Path:
        """说明：save_upload 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        if upload.content_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Unsupported file type: {upload.content_type}",
            )
        suffix = Path(upload.filename or "").suffix.lower()
        safe_name = f"{uuid.uuid4().hex}{suffix}"
        target_dir = self.settings.upload_dir / category
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / safe_name
        max_bytes = self.settings.max_upload_mb * 1024 * 1024
        size = 0
        with target.open("wb") as handle:
            while chunk := await upload.read(1024 * 1024):
                size += len(chunk)
                if size > max_bytes:
                    target.unlink(missing_ok=True)
                    raise HTTPException(status_code=413, detail="Uploaded file is too large.")
                handle.write(chunk)
        return target

    def output_path(self, suffix: str) -> Path:
        """说明：output_path 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        self.settings.output_dir.mkdir(parents=True, exist_ok=True)
        return self.settings.output_dir / f"{uuid.uuid4().hex}{suffix}"

