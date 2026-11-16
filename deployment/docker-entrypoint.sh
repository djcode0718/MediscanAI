#!/bin/sh
set -e

# Wait for PostgreSQL if DATABASE_URL is configured
if [ -n "$DATABASE_URL" ] && [ "$WAIT_FOR_DB" = "true" ]; then
    echo "Waiting for database to be ready..."
    # A simple Python one-liner to ping DB before running migrations
    python3 -c "
import sys, time
from sqlalchemy import create_engine, text
db_url = '$DATABASE_URL'
for attempt in range(30):
    try:
        engine = create_engine(db_url)
        with engine.connect() as conn:
            conn.execute(text('SELECT 1'))
        print('Database connection established successfully.')
        sys.exit(0)
    except Exception as e:
        time.sleep(1)
print('Database connection timed out.')
sys.exit(1)
" || { echo "Database unreachable, proceeding anyway..."; }
fi

# Run database migrations if RUN_MIGRATIONS is true
if [ "$RUN_MIGRATIONS" = "true" ]; then
    echo "Applying Alembic database migrations..."
    alembic upgrade head
    echo "Database migrations applied successfully."
fi

# Hand over to CMD (typically uvicorn)
exec "$@"

