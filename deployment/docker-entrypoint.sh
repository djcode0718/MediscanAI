#!/bin/sh
set -e

# Wait for PostgreSQL if DATABASE_URL is configured
if [ -n "$DATABASE_URL" ] && [ "$WAIT_FOR_DB" = "true" ]; then
    echo "[ENTRYPOINT] Probing PostgreSQL connectivity before starting application..."
    # Robust Python probe reading DATABASE_URL safely from environment without exposing secrets in logs
    python3 -c "
import os, sys, time
from sqlalchemy import create_engine, text

db_url = os.environ.get('DATABASE_URL')
if not db_url:
    print('[ENTRYPOINT] ERROR: DATABASE_URL is empty.', file=sys.stderr)
    sys.exit(1)

max_attempts = 30
for attempt in range(1, max_attempts + 1):
    try:
        engine = create_engine(db_url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text('SELECT 1'))
        print(f'[ENTRYPOINT] PostgreSQL connection verified successfully (attempt {attempt}/{max_attempts}).')
        sys.exit(0)
    except Exception as e:
        time.sleep(2)

print('[ENTRYPOINT] ERROR: PostgreSQL connection timed out after approximately 60 seconds (30 attempts). Aborting startup.', file=sys.stderr)
sys.exit(1)
"
fi

# Run database migrations if RUN_MIGRATIONS is true
if [ "$RUN_MIGRATIONS" = "true" ]; then
    echo "[ENTRYPOINT] Applying Alembic database migrations..."
    alembic upgrade head
    echo "[ENTRYPOINT] Database migrations applied successfully."
fi

# Hand over to CMD (typically uvicorn)
exec "$@"

