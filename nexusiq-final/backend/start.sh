#!/bin/bash
# NexusIQ — Production startup script
# Runs DB migrations then starts the server.
# This ensures Railway/Docker always has an up-to-date schema on every deploy.
set -e

echo "🔄 Running database migrations..."
# Use synchronous alembic env — it reads DATABASE_URL from env
# The config.py validator ensures asyncpg:// format for the app,
# but alembic needs the plain postgresql+asyncpg:// URL too (set in alembic.ini or env.py).
alembic upgrade head
echo "✅ Migrations complete"

echo "🚀 Starting NexusIQ backend..."
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers "${UVICORN_WORKERS:-1}"
