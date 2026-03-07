"""Settings loaded from environment variables."""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # API auth
    api_key: str = "dev-secret-key-change-me"

    # Encryption master key (32 url-safe base64 chars → Fernet key)
    master_encryption_key: str = ""  # generated on first run if empty

    # Docker
    openclaw_image: str = "openclaw/openclaw:latest"
    openclaw_network: str = "openclaw-egress"
    data_base_path: str = "/data/users"

    # Database
    db_path: str = "/data/provisioning.db"

    # Resource limits per container
    container_memory_mb: int = 256
    container_cpu: float = 0.5
    container_pids: int = 100
    container_tmpfs_mb: int = 50

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
