#!/usr/bin/env bash
set -euo pipefail

# YouTube Clone — one-command installer for clean Ubuntu.
# Usage: sudo ./install.sh

if [ "$(id -u)" -ne 0 ]; then
  echo "Run as root: sudo ./install.sh"
  exit 1
fi

cd "$(dirname "$0")"

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
    .env.example > .env
fi

# 3. Build and start
echo "Building and starting services..."
docker compose up -d --build

# 4. Wait for API health
echo "Waiting for API health..."
for i in $(seq 1 60); do
  if curl -fsS http://localhost/api/health >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

# 5. Seed demo data (idempotent)
echo "Seeding demo data..."
docker compose exec -T api python -m app.main seed || true

echo
echo "Done. Open http://$(hostname -I 2>/dev/null | awk '{print $1}'):80"
echo "Demo logins (seeded): admin / moderator / user — see README."