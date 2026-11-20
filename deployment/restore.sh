#!/bin/bash
# ==============================================================================
# MediScanAI Production Safe Database Restoration Script
# Defaults to restoring into an isolated test database to prevent data destruction
# To restore to production, must pass --force-production-restore explicitly
# ==============================================================================

set -e

DUMP_FILE="$1"
TARGET_MODE="${2:---test-db}"

if [ -z "$DUMP_FILE" ] || [ ! -f "$DUMP_FILE" ]; then
    echo "Usage: $0 <path_to_dump_file> [--test-db | --force-production-restore]"
    echo "  --test-db                  Restores into isolated database 'mediscanai_restore_test' (Default safe mode)"
    echo "  --force-production-restore Restores into live production database 'mediscanai' (DESTRUCTIVE)"
    exit 1
fi

CONTAINER_NAME="mediscanai-postgres"
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "ERROR: ${CONTAINER_NAME} is not running. Start PostgreSQL before restoring."
    exit 1
fi

# Ensure container restore temp file is cleaned up on exit
trap 'docker exec "$CONTAINER_NAME" rm -f /tmp/restore.dump >/dev/null 2>&1 || true' EXIT

echo "================================================================"
echo "          MediScanAI Database Restoration Procedure             "
echo "================================================================"

if [ "$TARGET_MODE" = "--force-production-restore" ]; then
    TARGET_DB="mediscanai"
    echo "⚠️  WARNING: Restoring directly to LIVE database '${TARGET_DB}'!"
    read -p "Type 'RESTORE_PRODUCTION' or 'RESTORE-PRODUCTION' to proceed: " CONFIRM
    if [ "$CONFIRM" != "RESTORE_PRODUCTION" ] && [ "$CONFIRM" != "RESTORE-PRODUCTION" ]; then
        echo "Aborted."
        exit 1
    fi
else
    TARGET_DB="mediscanai_restore_test"
    # Ensure test database is cleaned up on exit in safe test mode
    trap 'docker exec "$CONTAINER_NAME" rm -f /tmp/restore.dump >/dev/null 2>&1 || true; docker exec "$CONTAINER_NAME" psql -U mediscanai -d postgres -c "DROP DATABASE IF EXISTS ${TARGET_DB};" >/dev/null 2>&1 || true' EXIT
    echo "INFO: Safe mode: Restoring into isolated test database '${TARGET_DB}'."
    echo "      Creating test database if not exists..."
    docker exec "$CONTAINER_NAME" psql -U mediscanai -d postgres -c "DROP DATABASE IF EXISTS ${TARGET_DB};" >/dev/null 2>&1 || true
    docker exec "$CONTAINER_NAME" psql -U mediscanai -d postgres -c "CREATE DATABASE ${TARGET_DB};" >/dev/null
fi

echo "[1/3] Transferring dump file to container..."
docker cp "$DUMP_FILE" "${CONTAINER_NAME}:/tmp/restore.dump"

echo "[2/3] Executing pg_restore on '${TARGET_DB}'..."
docker exec "$CONTAINER_NAME" pg_restore --clean --if-exists --no-owner --no-privileges -U mediscanai -d "$TARGET_DB" /tmp/restore.dump || {
    echo "INFO: pg_restore completed with warnings (expected for pre-existing objects)."
}
docker exec "$CONTAINER_NAME" rm -f /tmp/restore.dump

echo "[3/3] Verifying restored schema and row counts in '${TARGET_DB}'..."
docker exec "$CONTAINER_NAME" psql -U mediscanai -d "$TARGET_DB" -c "
SELECT 'users' as table_name, count(*) as row_count FROM users
UNION ALL
SELECT 'analyses' as table_name, count(*) as row_count FROM analyses
UNION ALL
SELECT 'audit_logs' as table_name, count(*) as row_count FROM audit_logs;
"

if [ "$TARGET_MODE" = "--test-db" ]; then
    echo "----------------------------------------------------------------"
    echo "SUCCESS: Test restoration verified cleanly without touching live data."
    echo "Cleaning up isolated test database '${TARGET_DB}'..."
    docker exec "$CONTAINER_NAME" psql -U mediscanai -d postgres -c "DROP DATABASE ${TARGET_DB};" >/dev/null
    echo "Cleanup complete."
fi
echo "================================================================"
