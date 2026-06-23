"""
旅行助手 配置模块，统一管理环境变量和应用设置。
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Settings"""
    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "旅行助手"
    environment: str = "local"
    api_prefix: str = "/api"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    admin_token: str = "change-me"  # ⚠️ 必须在 .env 中修改为强口令
    database_url: str = f"sqlite:///{ROOT_DIR / 'storage' / 'travel_assistant.db'}"
    jwt_secret_key: str = "change-me-jwt-secret"  # ⚠️ 必须在 .env 中修改，至少 32 位随机字符串
    jwt_expire_minutes: int = 60 * 24 * 7

    default_provider: Literal["qwen", "deepseek", "local"] = "qwen"
    qwen_api_key: str | None = Field(default=None, alias="DASHSCOPE_API_KEY")
    qwen_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    qwen_chat_model: str = "qwen3.6-plus"
    qwen_fast_model: str = "qwen3.6-flash"
    qwen_reasoning_model: str = "qwen3.6-max-preview"
    qwen_embedding_model: str = "text-embedding-v4"
    qwen_rerank_model: str = "qwen3-rerank"
    qwen_vision_model: str = "qwen-vl-max-latest"
    qwen_image_model: str = "qwen-image-2.0-pro"
    qwen_tts_model: str = "cosyvoice-v3-plus"
    qwen_asr_model: str = "qwen3-asr-flash-realtime"

    deepseek_api_key: str | None = Field(default=None, alias="DEEPSEEK_API_KEY")
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_chat_model: str = "deepseek-v4-flash"
    deepseek_reasoning_model: str = "deepseek-v4-pro"

    local_openai_api_key: str = "local"
    local_openai_base_url: str | None = None
    local_chat_model: str = "qwen3:8b"
    local_embedding_model: str = "Qwen3-Embedding-0.6B"

    redis_url: str = "redis://localhost:6379/0"
    session_ttl_seconds: int = 60 * 60 * 24
    rate_limit_per_minute: int = 60
    tool_cache_ttl_seconds: int = 60 * 10
    max_context_tokens: int = 12000
    recent_history_tokens: int = 3000
    memory_summary_tokens: int = 1500
    rag_context_tokens: int = 4000
    web_context_tokens: int = 2500
    compression_trigger_tokens: int = 8000

    dataset_dir: Path = ROOT_DIR / "data" / "dataset"
    storage_dir: Path = ROOT_DIR / "storage"
    chroma_dir: Path = ROOT_DIR / "storage" / "chroma"
    bm25_dir: Path = ROOT_DIR / "storage" / "bm25"
    upload_dir: Path = ROOT_DIR / "storage" / "uploads"
    output_dir: Path = ROOT_DIR / "storage" / "outputs"

    chunk_size: int = 1000
    chunk_overlap: int = 180
    dense_top_k: int = 40
    bm25_top_k: int = 40
    rerank_top_k: int = 20
    final_top_k: int = 6
    embedding_dimension: int = 1024

    tavily_api_key: str | None = Field(default=None, alias="TAVILY_API_KEY")
    amap_key: str | None = Field(default=None, alias="AMAP_KEY")
    qweather_key: str | None = Field(default=None, alias="QWEATHER_KEY")
    openweather_api_key: str | None = Field(default=None, alias="OPENWEATHER_API_KEY")

    max_upload_mb: int = 25

    def ensure_directories(self) -> None:
        """说明：ensure_directories 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        for path in [
            self.storage_dir,
            self.chroma_dir,
            self.bm25_dir,
            self.upload_dir,
            self.output_dir,
        ]:
            path.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """说明：get_settings 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    settings = Settings()
    settings.ensure_directories()
    return settings
