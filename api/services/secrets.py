"""Secrets encryption/decryption using Fernet (AES-128-CBC + HMAC)."""
import os
import json
import base64
import logging
from pathlib import Path
from cryptography.fernet import Fernet
from config import get_settings

logger = logging.getLogger(__name__)

# Module-level cache for the Fernet instance (survives within a process)
_fernet_instance: Fernet | None = None


def _get_fernet() -> Fernet:
    """Return cached Fernet instance, generating master key once if not set."""
    global _fernet_instance
    if _fernet_instance is not None:
        return _fernet_instance

    settings = get_settings()
    key = settings.master_encryption_key

    if not key:
        # Auto-generate once per process (dev mode only — production must set env var)
        key = Fernet.generate_key().decode()
        logger.warning(
            "No MASTER_ENCRYPTION_KEY set — generated ephemeral key. "
            "Secrets will be unreadable after restart. Set MASTER_ENCRYPTION_KEY in production."
        )
    else:
        # Validate it's a proper Fernet key
        try:
            key_bytes = key.encode() if isinstance(key, str) else key
            base64.urlsafe_b64decode(key_bytes + b"==")
        except Exception:
            raise ValueError("MASTER_ENCRYPTION_KEY must be a valid Fernet key (use: Fernet.generate_key())")

    _fernet_instance = Fernet(key.encode() if isinstance(key, str) else key)
    return _fernet_instance


def _secrets_path(user_id: str) -> Path:
    settings = get_settings()
    return Path(settings.data_base_path) / user_id / "secrets" / "keys.enc"


def encrypt_secrets(user_id: str, secrets: dict) -> None:
    """Encrypt and persist secrets dict to disk."""
    fernet = _get_fernet()
    payload = json.dumps(secrets).encode()
    encrypted = fernet.encrypt(payload)

    path = _secrets_path(user_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(encrypted)
    # Restrict file permissions
    path.chmod(0o600)
    logger.info(f"Secrets saved for user {user_id}")


def decrypt_secrets(user_id: str) -> dict:
    """Decrypt and return secrets dict from disk."""
    path = _secrets_path(user_id)
    if not path.exists():
        raise FileNotFoundError(f"No secrets found for user {user_id}")

    fernet = _get_fernet()
    encrypted = path.read_bytes()
    payload = fernet.decrypt(encrypted)
    return json.loads(payload.decode())


def delete_secrets(user_id: str) -> None:
    """Securely remove secrets file."""
    path = _secrets_path(user_id)
    if path.exists():
        # Overwrite before deletion
        size = path.stat().st_size
        path.write_bytes(b"\x00" * size)
        path.unlink()
        logger.info(f"Secrets deleted for user {user_id}")


def secrets_exist(user_id: str) -> bool:
    return _secrets_path(user_id).exists()
