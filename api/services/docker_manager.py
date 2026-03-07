"""Docker container lifecycle management."""
import logging
import asyncio
from datetime import datetime
from typing import Optional

import docker
from docker.errors import NotFound, APIError, ImageNotFound
from docker.models.containers import Container

from config import get_settings
from services.config_gen import get_volume_mounts, get_container_env
from services.secrets import decrypt_secrets

logger = logging.getLogger(__name__)


def _get_docker_client() -> docker.DockerClient:
    """Return Docker client, raising RuntimeError if unavailable."""
    try:
        client = docker.from_env()
        client.ping()
        return client
    except Exception as e:
        raise RuntimeError(f"Docker is not available: {e}")


def _container_name(user_id: str) -> str:
    return f"openclaw-{user_id}"


def _ensure_network(client: docker.DockerClient, network_name: str) -> None:
    """Create the Docker network if it doesn't exist."""
    try:
        client.networks.get(network_name)
    except NotFound:
        logger.info(f"Creating Docker network: {network_name}")
        client.networks.create(
            network_name,
            driver="bridge",
            options={"com.docker.network.bridge.enable_icc": "false"},
        )


async def create_container(user_id: str, ai_provider: str) -> str:
    """
    Create and start an OpenClaw container for a user.
    Returns the container ID.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _create_container_sync, user_id, ai_provider)


def _create_container_sync(user_id: str, ai_provider: str) -> str:
    settings = get_settings()
    client = _get_docker_client()
    name = _container_name(user_id)

    # Remove stale container if it exists
    try:
        old = client.containers.get(name)
        logger.info(f"Removing stale container: {name}")
        old.remove(force=True)
    except NotFound:
        pass

    # Ensure egress network exists
    _ensure_network(client, settings.openclaw_network)

    # Decrypt secrets for env injection
    try:
        secrets = decrypt_secrets(user_id)
    except FileNotFoundError:
        secrets = {}

    env = get_container_env(user_id, ai_provider, secrets)
    volumes = get_volume_mounts(user_id)

    # Ensure host paths exist
    import os
    for host_path in volumes:
        os.makedirs(host_path, exist_ok=True)

    container: Container = client.containers.run(
        image=settings.openclaw_image,
        name=name,
        detach=True,
        environment=env,
        volumes=volumes,
        network=settings.openclaw_network,
        mem_limit=f"{settings.container_memory_mb}m",
        nano_cpus=int(settings.container_cpu * 1e9),
        pids_limit=settings.container_pids,
        read_only=True,
        tmpfs={"/tmp": f"size={settings.container_tmpfs_mb}m,mode=1777"},
        cap_drop=["ALL"],
        security_opt=["no-new-privileges:true"],
        restart_policy={"Name": "unless-stopped"},
        labels={
            "klaw.user_id": user_id,
            "klaw.managed": "true",
        },
    )

    logger.info(f"Started container {name} ({container.short_id}) for user {user_id}")
    return container.id


async def stop_container(user_id: str) -> bool:
    """Stop a container. Returns True if stopped, False if not found."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _stop_container_sync, user_id)


def _stop_container_sync(user_id: str) -> bool:
    client = _get_docker_client()
    name = _container_name(user_id)
    try:
        container = client.containers.get(name)
        container.stop(timeout=10)
        container.remove()
        logger.info(f"Stopped and removed container {name}")
        return True
    except NotFound:
        return False


async def restart_container(user_id: str) -> bool:
    """Restart an existing container."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _restart_container_sync, user_id)


def _restart_container_sync(user_id: str) -> bool:
    client = _get_docker_client()
    name = _container_name(user_id)
    try:
        container = client.containers.get(name)
        container.restart(timeout=10)
        logger.info(f"Restarted container {name}")
        return True
    except NotFound:
        return False


async def get_container_status(user_id: str) -> Optional[dict]:
    """
    Return container status dict or None if not found.
    Dict keys: status, container_id, started_at, uptime_seconds, health
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _get_container_status_sync, user_id)


def _get_container_status_sync(user_id: str) -> Optional[dict]:
    client = _get_docker_client()
    name = _container_name(user_id)
    try:
        container = client.containers.get(name)
        container.reload()

        state = container.attrs.get("State", {})
        status = state.get("Status", "unknown")

        started_at_str = state.get("StartedAt", "")
        uptime_seconds = None
        started_at = None
        if started_at_str and started_at_str != "0001-01-01T00:00:00Z":
            try:
                # Parse ISO 8601 with nanoseconds — truncate to microseconds
                ts = started_at_str[:26] + "Z"
                started_at = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                from datetime import timezone
                now = datetime.now(timezone.utc)
                uptime_seconds = int((now - started_at).total_seconds())
            except Exception:
                pass

        health = None
        health_state = container.attrs.get("State", {}).get("Health", {})
        if health_state:
            health = health_state.get("Status", "none")

        return {
            "status": status,
            "container_id": container.id,
            "started_at": started_at,
            "uptime_seconds": uptime_seconds,
            "health": health,
        }
    except NotFound:
        return None


async def docker_available() -> bool:
    """Check if Docker is reachable."""
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _get_docker_client)
        return True
    except RuntimeError:
        return False


async def count_running_containers() -> int:
    """Count managed running containers."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _count_running_containers_sync)


def _count_running_containers_sync() -> int:
    try:
        client = _get_docker_client()
        containers = client.containers.list(filters={"label": "klaw.managed=true"})
        return len(containers)
    except Exception:
        return 0
