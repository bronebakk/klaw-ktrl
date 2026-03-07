"""Pydantic request/response models."""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class AIProvider(str, Enum):
    anthropic = "anthropic"
    openai = "openai"
    google = "google"


class InstanceStatus(str, Enum):
    pending = "pending"
    running = "running"
    stopped = "stopped"
    error = "error"
    archived = "archived"


# ── Request models ────────────────────────────────────────────────────────────

class CreateInstanceRequest(BaseModel):
    user_id: str = Field(..., pattern=r"^[a-zA-Z0-9_-]{3,64}$", description="Unique user identifier")
    telegram_token: str = Field(..., min_length=10, description="Telegram bot token")
    ai_provider: AIProvider = Field(default=AIProvider.anthropic)
    ai_api_key: str = Field(..., min_length=10, description="AI provider API key")
    personality: Optional[str] = Field(None, max_length=500, description="Optional SOUL.md content")


class UpdateConfigRequest(BaseModel):
    telegram_token: Optional[str] = Field(None, min_length=10)
    ai_provider: Optional[AIProvider] = None
    ai_api_key: Optional[str] = Field(None, min_length=10)
    personality: Optional[str] = Field(None, max_length=500)


# ── Response models ───────────────────────────────────────────────────────────

class InstanceResponse(BaseModel):
    user_id: str
    status: InstanceStatus
    container_id: Optional[str] = None
    container_name: Optional[str] = None
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    uptime_seconds: Optional[int] = None
    health: Optional[str] = None
    message: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    docker_available: bool
    total_instances: int
    running_instances: int
    version: str = "1.0.0"


class ErrorResponse(BaseModel):
    detail: str
    code: Optional[str] = None
