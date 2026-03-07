"""
klaw.ktrl.no — Provisioning API
Manages OpenClaw Docker container lifecycle.
"""
import logging
import os
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from database import get_db, close_db, get_all_instances
import database as db
import httpx

from models import (
    CreateInstanceRequest,
    UpdateConfigRequest,
    InstanceResponse,
    InstanceStatus,
    HealthResponse,
)
from services.secrets import encrypt_secrets, decrypt_secrets, delete_secrets, secrets_exist
from services.config_gen import create_user_dirs, generate_openclaw_config
from services import docker_manager

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ── App lifecycle ─────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    # Ensure base data directory exists
    os.makedirs(settings.data_base_path, exist_ok=True)
    os.makedirs(os.path.dirname(settings.db_path), exist_ok=True)
    # Init DB
    await get_db()
    logger.info("Provisioning API started")
    yield
    await close_db()
    logger.info("Provisioning API shutdown")


app = FastAPI(
    title="klaw.ktrl.no Provisioning API",
    description="Manages OpenClaw Docker container lifecycle for multi-tenant hosting",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3098", "https://klaw.ktrl.no"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Auth ──────────────────────────────────────────────────────────────────────

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)


async def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    settings = get_settings()
    if api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )
    return api_key


AuthDep = Annotated[str, Security(verify_api_key)]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _map_container_status(container_status: str | None) -> InstanceStatus:
    mapping = {
        "running": InstanceStatus.running,
        "exited": InstanceStatus.stopped,
        "stopped": InstanceStatus.stopped,
        "paused": InstanceStatus.stopped,
        "created": InstanceStatus.pending,
    }
    return mapping.get(container_status or "", InstanceStatus.error)


async def _build_instance_response(record: dict | None, user_id: str) -> InstanceResponse:
    if not record:
        raise HTTPException(status_code=404, detail=f"Instance '{user_id}' not found")

    container_info = await docker_manager.get_container_status(user_id)

    if container_info:
        live_status = _map_container_status(container_info["status"])
    else:
        raw_status = record.get("status", "error")
        live_status = InstanceStatus(raw_status) if raw_status in InstanceStatus.__members__ else InstanceStatus.error

    return InstanceResponse(
        user_id=user_id,
        status=live_status,
        container_id=container_info["container_id"] if container_info else record.get("container_id"),
        container_name=record.get("container_name"),
        created_at=record.get("created_at"),
        started_at=container_info["started_at"] if container_info else None,
        uptime_seconds=container_info["uptime_seconds"] if container_info else None,
        health=container_info["health"] if container_info else None,
    )


# ── Routes ────────────────────────────────────────────────────────────────────

@app.post("/api/validate/telegram-token", tags=["Validation"])
async def validate_telegram_token(body: dict):
    """
    Validate a Telegram bot token against the Telegram API.
    Returns bot name and username on success. No auth required.
    """
    token = body.get("token", "").strip()
    if not token:
        raise HTTPException(status_code=400, detail="token is required")

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(f"https://api.telegram.org/bot{token}/getMe")
            data = resp.json()
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=f"Telegram API unreachable: {e}")

    if not data.get("ok"):
        err = data.get("description", "Invalid token")
        raise HTTPException(status_code=400, detail=err)

    bot = data["result"]
    return {
        "ok": True,
        "bot_name": bot.get("first_name", ""),
        "bot_username": bot.get("username", ""),
        "bot_id": bot.get("id"),
    }


@app.post("/api/validate/ai-key", tags=["Validation"])
async def validate_ai_key(body: dict):
    """
    Test an AI provider API key. No auth required.
    provider: "anthropic" | "openai" | "google"
    """
    provider = body.get("provider", "").strip()
    key = body.get("key", "").strip()

    if not provider or not key:
        raise HTTPException(status_code=400, detail="provider and key are required")

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            if provider == "anthropic":
                resp = await client.get(
                    "https://api.anthropic.com/v1/models",
                    headers={"x-api-key": key, "anthropic-version": "2023-06-01"},
                )
                if resp.status_code == 200:
                    models = [m.get("id") for m in resp.json().get("data", [])[:3]]
                    return {"ok": True, "models": models, "provider": "Anthropic"}
                else:
                    detail = resp.json().get("error", {}).get("message", "Invalid API key")
                    raise HTTPException(status_code=400, detail=detail)

            elif provider == "openai":
                resp = await client.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {key}"},
                )
                if resp.status_code == 200:
                    all_models = [m["id"] for m in resp.json().get("data", [])]
                    preferred = [m for m in all_models if "gpt-4" in m][:3] or all_models[:3]
                    return {"ok": True, "models": preferred, "provider": "OpenAI"}
                else:
                    detail = resp.json().get("error", {}).get("message", "Invalid API key")
                    raise HTTPException(status_code=400, detail=detail)

            elif provider == "google":
                resp = await client.get(
                    f"https://generativelanguage.googleapis.com/v1beta/models?key={key}",
                )
                if resp.status_code == 200:
                    models = [m.get("name", "").split("/")[-1] for m in resp.json().get("models", [])[:3]]
                    return {"ok": True, "models": models, "provider": "Google"}
                else:
                    detail = resp.json().get("error", {}).get("message", "Invalid API key")
                    raise HTTPException(status_code=400, detail=detail)

            else:
                raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")

        except HTTPException:
            raise
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=f"Provider API unreachable: {e}")


@app.get("/api/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """System health — no auth required."""
    docker_ok = await docker_manager.docker_available()
    instances = await get_all_instances()
    running = await docker_manager.count_running_containers()

    return HealthResponse(
        status="ok" if docker_ok else "degraded",
        docker_available=docker_ok,
        total_instances=len(instances),
        running_instances=running,
    )


@app.post(
    "/api/instances",
    response_model=InstanceResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Instances"],
)
async def create_instance(body: CreateInstanceRequest, _: AuthDep):
    """
    Provision a new OpenClaw instance for a user.
    - Creates directory structure
    - Encrypts and stores secrets
    - Generates OpenClaw config
    - Starts Docker container
    """
    user_id = body.user_id

    # Check for existing active instance
    existing = await db.get_instance(user_id)
    if existing and existing.get("status") in ("running", "pending"):
        raise HTTPException(
            status_code=409,
            detail=f"Instance '{user_id}' already exists (status: {existing['status']}). "
                   "Delete or restart it first.",
        )

    logger.info(f"Provisioning instance for user: {user_id}")

    try:
        # 1. Create user & record
        await db.upsert_user(user_id)
        await db.create_instance_record(user_id, body.ai_provider.value)

        # 2. Create directories
        create_user_dirs(user_id)

        # 3. Encrypt and store secrets
        secrets = {
            "telegram_token": body.telegram_token,
            "ai_api_key": body.ai_api_key,
            "ai_provider": body.ai_provider.value,
        }
        encrypt_secrets(user_id, secrets)

        # 4. Generate OpenClaw config
        generate_openclaw_config(
            user_id=user_id,
            telegram_token=body.telegram_token,
            ai_provider=body.ai_provider.value,
            personality=body.personality,
        )

        # 5. Start container
        container_id = await docker_manager.create_container(user_id, body.ai_provider.value)

        await db.update_instance(
            user_id,
            status="running",
            container_id=container_id,
        )

        logger.info(f"Instance {user_id} provisioned successfully")

    except Exception as e:
        logger.error(f"Failed to provision instance {user_id}: {e}", exc_info=True)
        await db.update_instance(user_id, status="error", error_message=str(e))
        raise HTTPException(status_code=500, detail=f"Provisioning failed: {e}")

    record = await db.get_instance(user_id)
    return await _build_instance_response(record, user_id)


@app.get(
    "/api/instances/{user_id}",
    response_model=InstanceResponse,
    tags=["Instances"],
)
async def get_instance(user_id: str, _: AuthDep):
    """Get status of a specific instance."""
    record = await db.get_instance(user_id)
    return await _build_instance_response(record, user_id)


@app.post(
    "/api/instances/{user_id}/restart",
    response_model=InstanceResponse,
    tags=["Instances"],
)
async def restart_instance(user_id: str, _: AuthDep):
    """Restart a running or stopped instance."""
    record = await db.get_instance(user_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Instance '{user_id}' not found")

    logger.info(f"Restarting instance: {user_id}")

    restarted = await docker_manager.restart_container(user_id)
    if not restarted:
        # Container gone — re-create it
        if not secrets_exist(user_id):
            raise HTTPException(
                status_code=400,
                detail="No secrets found. Please delete and re-create the instance.",
            )
        try:
            ai_provider = record.get("ai_provider", "anthropic")
            container_id = await docker_manager.create_container(user_id, ai_provider)
            await db.update_instance(user_id, status="running", container_id=container_id)
        except Exception as e:
            await db.update_instance(user_id, status="error", error_message=str(e))
            raise HTTPException(status_code=500, detail=f"Restart failed: {e}")
    else:
        await db.update_instance(user_id, status="running")

    record = await db.get_instance(user_id)
    return await _build_instance_response(record, user_id)


@app.delete(
    "/api/instances/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Instances"],
)
async def delete_instance(user_id: str, keep_data: bool = True, _: AuthDep = None):
    """
    Stop and archive an instance.
    - `keep_data=true` (default): preserves workspace & secrets
    - `keep_data=false`: removes secrets (workspace kept for GDPR export)
    """
    record = await db.get_instance(user_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Instance '{user_id}' not found")

    logger.info(f"Deleting instance: {user_id} (keep_data={keep_data})")

    await docker_manager.stop_container(user_id)

    if not keep_data:
        try:
            delete_secrets(user_id)
        except Exception as e:
            logger.warning(f"Failed to delete secrets for {user_id}: {e}")

    await db.update_instance(user_id, status="archived")
    # Optionally remove DB record fully
    # await db.delete_instance_record(user_id)


@app.put(
    "/api/instances/{user_id}/config",
    response_model=InstanceResponse,
    tags=["Instances"],
)
async def update_instance_config(user_id: str, body: UpdateConfigRequest, _: AuthDep):
    """
    Update instance configuration.
    Applies changes and restarts the container.
    """
    record = await db.get_instance(user_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Instance '{user_id}' not found")

    logger.info(f"Updating config for instance: {user_id}")

    try:
        # Load existing secrets and merge updates
        try:
            existing_secrets = decrypt_secrets(user_id)
        except FileNotFoundError:
            existing_secrets = {}

        updated = False

        if body.telegram_token:
            existing_secrets["telegram_token"] = body.telegram_token
            updated = True
        if body.ai_api_key:
            existing_secrets["ai_api_key"] = body.ai_api_key
            updated = True
        if body.ai_provider:
            existing_secrets["ai_provider"] = body.ai_provider.value
            updated = True

        if updated:
            encrypt_secrets(user_id, existing_secrets)

        ai_provider = (
            body.ai_provider.value
            if body.ai_provider
            else existing_secrets.get("ai_provider", record.get("ai_provider", "anthropic"))
        )
        telegram_token = (
            body.telegram_token
            or existing_secrets.get("telegram_token", "")
        )

        generate_openclaw_config(
            user_id=user_id,
            telegram_token=telegram_token,
            ai_provider=ai_provider,
            personality=body.personality,
        )

        if body.ai_provider:
            await db.update_instance(user_id, ai_provider=ai_provider)

        # Restart to pick up new config
        await docker_manager.restart_container(user_id)

    except Exception as e:
        logger.error(f"Config update failed for {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Config update failed: {e}")

    record = await db.get_instance(user_id)
    return await _build_instance_response(record, user_id)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8100, reload=False, log_level="info")
