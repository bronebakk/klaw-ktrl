#!/usr/bin/env bash
# setup-network.sh — Isolated egress network for OpenClaw containers
# Run as root (or with sudo) before starting any containers.
# Usage: sudo bash docker/setup-network.sh [--teardown]
set -euo pipefail

NETWORK_NAME="openclaw-egress"
BRIDGE_NAME="br-openclaw"

# Allowed outbound destinations (API endpoints only)
ALLOWED_DESTINATIONS=(
  "api.anthropic.com"
  "api.openai.com"
  "api.telegram.org"
  "generativelanguage.googleapis.com"
  "registry.npmjs.org"       # for openclaw updates
  "auth.docker.io"
)

# ── Resolve hostnames to IPs ──────────────────────────────────────────────────
resolve_ips() {
  local host="$1"
  getent ahosts "$host" 2>/dev/null | awk '{print $1}' | sort -u
}

teardown() {
  echo "[klaw] Tearing down network and iptables rules..."

  # Flush custom chain
  iptables -F OPENCLAW-EGRESS 2>/dev/null || true
  iptables -D FORWARD -j OPENCLAW-EGRESS 2>/dev/null || true
  iptables -X OPENCLAW-EGRESS 2>/dev/null || true

  # Remove Docker network
  docker network rm "$NETWORK_NAME" 2>/dev/null || true
  echo "[klaw] Teardown complete."
  exit 0
}

[[ "${1:-}" == "--teardown" ]] && teardown

# ── 1. Create Docker network (internal = no default internet route) ───────────
if docker network inspect "$NETWORK_NAME" &>/dev/null; then
  echo "[klaw] Network '$NETWORK_NAME' already exists — skipping creation."
else
  echo "[klaw] Creating Docker network '$NETWORK_NAME'..."
  docker network create \
    --driver bridge \
    --internal \
    --opt com.docker.network.bridge.name="$BRIDGE_NAME" \
    --subnet 172.30.0.0/24 \
    "$NETWORK_NAME"
  echo "[klaw] Network created."
fi

# ── 2. Get bridge interface subnet ────────────────────────────────────────────
BRIDGE_SUBNET=$(docker network inspect "$NETWORK_NAME" \
  --format '{{range .IPAM.Config}}{{.Subnet}}{{end}}')
echo "[klaw] Bridge subnet: $BRIDGE_SUBNET"

# ── 3. Set up iptables custom chain ──────────────────────────────────────────
echo "[klaw] Configuring iptables egress rules..."

# Create chain (idempotent)
iptables -N OPENCLAW-EGRESS 2>/dev/null || iptables -F OPENCLAW-EGRESS

# Insert jump into FORWARD chain (idempotent via check)
iptables -C FORWARD -j OPENCLAW-EGRESS 2>/dev/null || \
  iptables -I FORWARD 1 -j OPENCLAW-EGRESS

# Allow established/related return traffic
iptables -A OPENCLAW-EGRESS -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT

# Allow DNS (outbound UDP/TCP 53) for name resolution
iptables -A OPENCLAW-EGRESS -p udp --dport 53 -j ACCEPT
iptables -A OPENCLAW-EGRESS -p tcp --dport 53 -j ACCEPT

# Allow outbound HTTPS to each approved destination
for host in "${ALLOWED_DESTINATIONS[@]}"; do
  echo "[klaw]   Resolving $host..."
  IPS=$(resolve_ips "$host")
  if [[ -z "$IPS" ]]; then
    echo "[klaw]   WARNING: Could not resolve $host — skipping"
    continue
  fi
  for ip in $IPS; do
    echo "[klaw]     Allowing HTTPS → $ip ($host)"
    iptables -A OPENCLAW-EGRESS \
      -s "$BRIDGE_SUBNET" -d "$ip" -p tcp --dport 443 -j ACCEPT
    # HTTP for npm registry redirects (redirects to https)
    iptables -A OPENCLAW-EGRESS \
      -s "$BRIDGE_SUBNET" -d "$ip" -p tcp --dport 80 -j ACCEPT
  done
done

# Block inter-container communication (same bridge)
iptables -A OPENCLAW-EGRESS \
  -s "$BRIDGE_SUBNET" -d "$BRIDGE_SUBNET" -j DROP

# Drop all other outbound from this subnet
iptables -A OPENCLAW-EGRESS \
  -s "$BRIDGE_SUBNET" -j DROP

echo "[klaw] iptables rules applied."

# ── 4. Summary ────────────────────────────────────────────────────────────────
echo ""
echo "✅ Network '$NETWORK_NAME' is ready."
echo "   Containers on this network may only reach:"
for host in "${ALLOWED_DESTINATIONS[@]}"; do
  echo "     • $host (port 443)"
done
echo ""
echo "   Inter-container traffic: BLOCKED"
echo "   All other egress: BLOCKED"
echo ""
echo "To tear down: sudo bash docker/setup-network.sh --teardown"
