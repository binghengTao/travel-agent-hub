"""
旅行助手 源码组件。


"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Header, HTTPException, status

from app.core.config import get_settings


async def require_admin(x_admin_token: str | None = Header(default=None)) -> None:
    """说明：require_admin 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    settings = get_settings()
    if not x_admin_token or x_admin_token != settings.admin_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin token is required for this operation.",
        )


def hash_password(password: str) -> str:
    """说明：hash_password 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    salt = os.urandom(16)
    iterations = 210_000
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return "pbkdf2_sha256${}${}${}".format(
        iterations,
        base64.urlsafe_b64encode(salt).decode("ascii"),
        base64.urlsafe_b64encode(digest).decode("ascii"),
    )


def verify_password(password: str, stored_hash: str) -> bool:
    """说明：verify_password 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    try:
        algorithm, raw_iterations, raw_salt, raw_digest = stored_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(raw_iterations)
        salt = base64.urlsafe_b64decode(raw_salt.encode("ascii"))
        expected = base64.urlsafe_b64decode(raw_digest.encode("ascii"))
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False


def create_access_token(subject: str, *, username: str = "") -> tuple[str, int]:
    """说明：create_access_token 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {
        "sub": subject,
        "username": username,
        "exp": int(expires_at.timestamp()),
        "iat": int(time.time()),
    }
    return _encode_jwt(payload, settings.jwt_secret_key), settings.jwt_expire_minutes * 60


def decode_access_token(token: str) -> dict[str, Any]:
    """说明：decode_access_token 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    settings = get_settings()
    try:
        header_b64, payload_b64, signature_b64 = token.split(".")
        signed = f"{header_b64}.{payload_b64}".encode("ascii")
        expected = _sign(signed, settings.jwt_secret_key)
        actual = _b64decode(signature_b64)
        if not hmac.compare_digest(expected, actual):
            raise ValueError("bad signature")
        payload = json.loads(_b64decode(payload_b64))
        if int(payload.get("exp", 0)) < int(time.time()):
            raise ValueError("expired token")
        return payload
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token.") from exc


def _encode_jwt(payload: dict[str, Any], secret: str) -> str:
    """说明：_encode_jwt 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = _b64encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = _sign(f"{header_b64}.{payload_b64}".encode("ascii"), secret)
    return f"{header_b64}.{payload_b64}.{_b64encode(signature)}"


def _sign(data: bytes, secret: str) -> bytes:
    """说明：_sign 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    return hmac.new(secret.encode("utf-8"), data, hashlib.sha256).digest()


def _b64encode(data: bytes) -> str:
    """说明：_b64encode 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64decode(data: str) -> bytes:
    """说明：_b64decode 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + padding).encode("ascii"))
