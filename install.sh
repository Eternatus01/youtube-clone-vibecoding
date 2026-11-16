#!/usr/bin/env bash
set -euo pipefail

# YouTube Clone — one-command installer for clean Ubuntu.
# Usage: sudo ./install.sh

if [ "$(id -u)" -ne 0 ]; then
  echo "Run as root: sudo ./install.sh"
  exit 1
fi

cd "$(dirname "$0")"

# 0. Preflight
if [ ! -f docker-compose.yml ]; then
  echo "ERROR: docker-compose.yml not found. Run from the project root."
  exit 1
fi
if [ ! -f .env.example ]; then
  echo "ERROR: .env.example not found."
  exit 1
fi

AVAIL_GB=$(df -BG --output=avail . | tail -1 | tr -d ' G')
if [ "${AVAIL_GB:-0}" -lt 5 ]; then
  echo "WARNING: less than 5 GB free disk space (${AVAIL_GB} GB). Build may fail."
fi

# 1. Install Docker if missing
if ! command -v docker >/dev/null 2>&1; then
  echo "Installing Docker..."
  apt-get update -y
  apt-get install -y ca-certificates curl
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" > /etc/apt/sources.list.d/docker.list
  apt-get update -y
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  systemctl enable --now docker
fi

# Verify Compose plugin works
if ! docker compose version >/dev/null 2>&1; then
  echo "ERROR: docker compose plugin not available. Install docker-compose-plugin."
  exit 1
fi

# 2. Generate .env with random secrets if missing
if [ ! -f .env ]; then
  echo "Generating .env with random secrets..."
  gen() { head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n' | head -c 32; }
  POSTGRES_PASSWORD="$(gen)"
  JWT_SECRET="$(gen)"
  REFRESH_SECRET="$(gen)"
  S3_SECRET_KEY="$(gen)"
  sed \
    -e "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=${POSTGRES_PASSWORD}|" \
    -e "s|^JWT_SECRET=.*|JWT_SECRET=${JWT_SECRET}|" \
    -e "s|^REFRESH_SECRET=.*|REFRESH_SECRET=${REFRESH_SECRET}|" \
    -e "s|^S3_SECRET_KEY=.*|S3_SECRET_KEY=${S3_SECRET_KEY}|" \
    -e "s|^DATABASE_URL=.*|DATABASE_URL=postgresql+asyncpg://yt:${POSTGRES_PASSWORD}@db:5432/yt|" \
    .env.example > .env
  chmod 600 .env
  echo ".env created with random secrets."
fi

# 3. Build and start
echo "Building and starting services..."
docker compose up -d --build

# 4. Wait for API health
echo "Waiting for API health (max 120s)..."
HEALTHY=0
for i in $(seq 1 60); do
  if curl -fsS http://localhost/api/health >/dev/null 2>&1; then
    HEALTHY=1
    break
  fi
  printf "."
  sleep 2
done
echo
if [ "$HEALTHY" -eq 0 ]; then
  echo "ERROR: API did not become healthy. Check logs: docker compose logs api"
  exit 1
fi

# 5. Seed demo data (idempotent)
echo "Seeding demo data..."
docker compose exec -T api python -m app.main seed || {
  echo "WARNING: seed failed (non-fatal). Check logs: docker compose logs api"
}

# Detect server IP
SERVER_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
if [ -z "$SERVER_IP" ]; then
  SERVER_IP="localhost"
fi

echo
echo "=============================================="
echo "  Done. Open http://${SERVER_IP}"
echo "  Demo logins: admin / moderator / alice"
echo "  All passwords: secret123"
echo "  API docs:     http://${SERVER_IP}/docs"
echo "=============================================="