#!/usr/bin/env bash
set -e

cd /opt/bots/telegram-max-bot

echo "=== Pull latest code ==="
git pull

echo "=== Build and restart bot ==="
docker compose up -d --build

echo "=== Compose status ==="
docker compose ps

echo "=== Last logs ==="
docker compose logs --tail=50
