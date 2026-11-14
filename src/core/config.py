from functools import lru_cache

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    log_level: str = "INFO"
    database_url: str = "postgresql+asyncpg://rag:rag_dev_password@localhost:5432/rag"
    api_keys: str = ""
    openai_api_key: SecretStr | None = None
    openai_chat_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 768
    chunk_size: int = 900
    chunk_overlap: int = 120
    retrieval_top_k: int = 5
    max_upload_bytes: int = 20_000_000
    max_chunks_per_document: int = 1000
    cors_origins: list[str] = []

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("chunk_overlap")
    @classmethod
    def overlap_must_be_smaller_than_chunk(cls, value: int, info):
        chunk_size = info.data.get("chunk_size", 900)
        if value < 0 or value >= chunk_size:
            raise ValueError("chunk_overlap must be non-negative and smaller than chunk_size")
        return value

    @property
    def tenant_api_keys(self) -> dict[str, str]:
        parsed: dict[str, str] = {}
        for entry in self.api_keys.split(","):
            tenant_id, separator, secret = entry.partition(":")
            if separator and tenant_id.strip() and secret.strip():
                parsed[tenant_id.strip()] = secret.strip()
        return parsed


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
