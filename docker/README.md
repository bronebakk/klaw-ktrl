# Docker — OpenClaw Multi-Tenant Isolation

This directory contains the Docker setup for running isolated OpenClaw instances on [klaw.ktrl.no](https://klaw.ktrl.no).

## Files

| File | Purpose |
|------|---------|
| `Dockerfile.openclaw` | Single-user OpenClaw container image |
| `docker-compose.test.yml` | Local test harness (one instance) |
| `setup-network.sh` | Egress-only network + iptables rules |

---

## Building the image

```bash
# From repo root
docker build -f docker/Dockerfile.openclaw -t openclaw-instance:latest .

# Tag for registry
docker tag openclaw-instance:latest ghcr.io/bronebakk/klaw-ktrl/openclaw:latest
```

---

## Testing locally

### 1. Create egress network (once per host)

```bash
sudo bash docker/setup-network.sh
```

### 2. Copy `.env.test` and fill in keys

```bash
cp docker/.env.test.example .env.test
# Edit .env.test with real API keys
```

### 3. Start test instance

```bash
docker compose -f docker/docker-compose.test.yml --env-file .env.test up
```

### 4. Check health

```bash
docker inspect --format='{{.State.Health.Status}}' openclaw-test-01
```

### Tear down

```bash
docker compose -f docker/docker-compose.test.yml down -v
sudo bash docker/setup-network.sh --teardown
```

---

## Security model

### Container isolation

| Layer | Mechanism |
|-------|-----------|
| **No root** | `--user <uid>:<gid>` at runtime; `USER openclaw` in image |
| **Immutable FS** | `read_only: true` + `tmpfs` for `/tmp` only |
| **No privilege escalation** | `no-new-privileges:true` + `cap_drop: ALL` |
| **Resource caps** | 256 MB RAM, 0.5 CPU (adjustable per tier) |

### Network isolation

The `openclaw-egress` Docker network is created with `--internal` (no default gateway). Custom iptables rules in `OPENCLAW-EGRESS` chain permit outbound HTTPS only to:

- `api.anthropic.com`
- `api.openai.com`
- `api.telegram.org`
- `generativelanguage.googleapis.com`
- `registry.npmjs.org`

All other egress and all inter-container traffic are **dropped**.

### Per-user isolation

Each user gets their own container with a unique UID, separate volume mounts for workspace and config, and an independent OpenClaw gateway process. Containers cannot communicate with each other.

---

## Production deployment

In production, the klaw.ktrl.no orchestrator (future) will:

1. Provision UID per user
2. `docker run --user <uid> -v <user-workspace>:/home/openclaw/.openclaw/workspace ...`
3. Proxy gateway traffic via HTTPS with per-user auth

See `/opt/klaw-ktrl/src/` for the orchestration SvelteKit app.

---

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Claude API key |
| `OPENAI_API_KEY` | No | OpenAI fallback |
| `TELEGRAM_BOT_TOKEN` | No | Telegram channel |
| `GOOGLE_API_KEY` | No | Gemini models |
| `OPENCLAW_TENANT_ID` | No | Logging/metrics ID |
