"""
旅行助手 源码组件。


"""

import shutil
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.security import create_access_token, decode_access_token, hash_password, verify_password
from app.api.deps import current_user
from app.services.auth_service import AuthService


def _test_root() -> Path:
    """说明：_test_root 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    root = Path(__file__).resolve().parents[1] / "test_runtime" / uuid4().hex
    root.mkdir(parents=True, exist_ok=True)
    return root


def test_password_hash_and_jwt_roundtrip():
    """说明：test_password_hash_and_jwt_roundtrip 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    hashed = hash_password("secret123")
    assert verify_password("secret123", hashed)
    assert not verify_password("bad-secret", hashed)

    token, expires_in = create_access_token("42", username="alice")
    payload = decode_access_token(token)
    assert payload["sub"] == "42"
    assert payload["username"] == "alice"
    assert expires_in > 0


def test_auth_service_register_login_and_duplicate_user():
    """说明：test_auth_service_register_login_and_duplicate_user 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    root = _test_root()
    try:
        settings = Settings(storage_dir=root / "storage", database_url=f"sqlite:///{root / 'travel_assistant.db'}")
        service = AuthService(settings)
        service.init_db()

        user = service.register(username="alice", password="secret123", email="alice@example.com")
        assert user.username == "alice"
        assert service.authenticate(username="alice", password="secret123") is not None
        assert service.authenticate(username="alice", password="wrong") is None
        assert service.get_user(user.user_id).username == "alice"

        with pytest.raises(ValueError):
            service.register(username="alice", password="secret123")
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_current_user_dependency_requires_and_accepts_bearer_token():
    """说明：test_current_user_dependency_requires_and_accepts_bearer_token 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    root = _test_root()
    try:
        settings = Settings(storage_dir=root / "storage", database_url=f"sqlite:///{root / 'travel_assistant.db'}")
        service = AuthService(settings)
        service.init_db()
        user = service.register(username="bob", password="secret123")
        token, _ = create_access_token(user.user_id, username=user.username)

        app = FastAPI()
        app.state.auth = service

        @app.get("/protected")
        async def protected(current=Depends(current_user)):
            """说明：protected 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
            return {"user_id": current.user_id}

        client = TestClient(app)
        assert client.get("/protected").status_code == 401
        response = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        assert response.json()["user_id"] == user.user_id
    finally:
        shutil.rmtree(root, ignore_errors=True)
