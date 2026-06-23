"""
旅行助手 源码组件。


"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from app.core.config import Settings, get_settings
from app.core.security import hash_password, verify_password


class Base(DeclarativeBase):
    """Base"""
    pass


class UserModel(Base):
    """UserModel"""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, index=True, nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class AuthenticatedUser:
    """AuthenticatedUser"""
    id: int
    username: str
    email: str | None = None
    created_at: datetime | None = None

    @property
    def user_id(self) -> str:
        """说明：user_id 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        return str(self.id)

    def to_dict(self) -> dict:
        """说明：to_dict 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AuthService:
    """AuthService"""
    def __init__(self, settings: Settings | None = None):
        """说明：__init__ 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        self.settings = settings or get_settings()
        self.settings.storage_dir.mkdir(parents=True, exist_ok=True)
        connect_args = {"check_same_thread": False} if self.settings.database_url.startswith("sqlite") else {}
        self.engine = create_engine(self.settings.database_url, connect_args=connect_args)
        self.SessionLocal = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, expire_on_commit=False)

    def init_db(self) -> None:
        """说明：init_db 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        Base.metadata.create_all(bind=self.engine)

    def register(self, *, username: str, password: str, email: str | None = None) -> AuthenticatedUser:
        """说明：register 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        username = username.strip()
        email = email.strip() if email else None
        with self.session() as db:
            if db.scalar(select(UserModel).where(UserModel.username == username)):
                raise ValueError("Username already exists.")
            if email and db.scalar(select(UserModel).where(UserModel.email == email)):
                raise ValueError("Email already exists.")
            user = UserModel(username=username, email=email, password_hash=hash_password(password))
            db.add(user)
            db.commit()
            db.refresh(user)
            return _to_user(user)

    def authenticate(self, *, username: str, password: str) -> AuthenticatedUser | None:
        """说明：authenticate 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        with self.session() as db:
            user = db.scalar(select(UserModel).where(UserModel.username == username.strip()))
            if not user or not verify_password(password, user.password_hash):
                return None
            return _to_user(user)

    def get_user(self, user_id: str | int) -> AuthenticatedUser | None:
        """说明：get_user 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        try:
            parsed_id = int(user_id)
        except (TypeError, ValueError):
            return None
        with self.session() as db:
            user = db.get(UserModel, parsed_id)
            return _to_user(user) if user else None

    def session(self) -> Session:
        """说明：session 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        return self.SessionLocal()


def _to_user(user: UserModel) -> AuthenticatedUser:
    """说明：_to_user 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    return AuthenticatedUser(id=user.id, username=user.username, email=user.email, created_at=user.created_at)
