#!/bin/sh
# Runs Alembic migrations once (only when RUN_MIGRATIONS=true, set by the
# `backend` service in docker-compose.prod.yml but not `worker` - avoids
# both containers racing to migrate on the same `docker compose up`), then
# execs whatever command the container was actually started with (uvicorn
# by default, or the worker's overridden celery command).
set -e

if [ "$RUN_MIGRATIONS" = "true" ]; then
    echo "Running database migrations..."
    python scripts/run_migrations.py upgrade
fi

exec "$@"
