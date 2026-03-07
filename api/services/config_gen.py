"""Generate OpenClaw configuration files for a user instance."""
import json
import logging
from pathlib import Path
from config import get_settings

logger = logging.getLogger(__name__)


def _user_config_dir(user_id: str) -> Path:
    settings = get_settings()
    return Path(settings.data_base_path) / user_id / "config"


def _user_workspace_dir(user_id: str) -> Path:
    settings = get_settings()
    return Path(settings.data_base_path) / user_id / "workspace"


def create_user_dirs(user_id: str) -> None:
    """Create all required directories for a user."""
    settings = get_settings()
    base = Path(settings.data_base_path) / user_id

    dirs = [
        base / "config",
        base / "workspace",
        base / "secrets",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        d.chmod(0o700)

    logger.info(f"Created directories for user {user_id}")


def generate_openclaw_config(
    user_id: str,
    telegram_token: str,
    ai_provider: str,
    personality: str | None = None,
) -> None:
    """
    Write openclaw.json (gateway config) to the user's config dir.
    OpenClaw reads this at startup.
    """
    config_dir = _user_config_dir(user_id)
    config_dir.mkdir(parents=True, exist_ok=True)

    # Map provider names to OpenClaw model strings
    provider_defaults = {
        "anthropic": "anthropic/claude-sonnet-4-6",
        "openai": "openai/gpt-4o",
        "google": "google/gemini-2.0-flash",
    }
    default_model = provider_defaults.get(ai_provider, "anthropic/claude-sonnet-4-6")

    config = {
        "channels": {
            "telegram": {
                "enabled": True,
                "token": telegram_token,
            }
        },
        "model": default_model,
        "provider": ai_provider,
    }

    config_path = config_dir / "openclaw.json"
    config_path.write_text(json.dumps(config, indent=2))
    config_path.chmod(0o600)

    # Write SOUL.md if personality provided
    workspace_dir = _user_workspace_dir(user_id)
    workspace_dir.mkdir(parents=True, exist_ok=True)

    soul_path = workspace_dir / "SOUL.md"
    if personality:
        soul_path.write_text(personality)
        soul_path.chmod(0o600)
    elif not soul_path.exists():
        # Default minimal soul
        soul_path.write_text(
            "# SOUL.md\n\nYou are a helpful AI assistant. Be concise, helpful, and friendly.\n"
        )

    logger.info(f"Generated OpenClaw config for user {user_id} (provider: {ai_provider})")


def get_volume_mounts(user_id: str) -> dict:
    """Return Docker volume mount spec for a user container."""
    settings = get_settings()
    base = Path(settings.data_base_path) / user_id

    return {
        str(base / "workspace"): {
            "bind": "/home/openclaw/.openclaw/workspace",
            "mode": "rw",
        },
        str(base / "config"): {
            "bind": "/home/openclaw/.openclaw",
            "mode": "ro",
        },
    }


def get_container_env(user_id: str, ai_provider: str, secrets: dict) -> dict:
    """Build environment variables to inject into the container."""
    env = {
        "OPENCLAW_USER_ID": user_id,
        "NODE_ENV": "production",
    }

    provider_env_map = {
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "google": "GOOGLE_AI_API_KEY",
    }

    env_key = provider_env_map.get(ai_provider)
    if env_key and "ai_api_key" in secrets:
        env[env_key] = secrets["ai_api_key"]

    if "telegram_token" in secrets:
        env["TELEGRAM_BOT_TOKEN"] = secrets["telegram_token"]

    return env
