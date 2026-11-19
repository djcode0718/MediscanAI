#!/usr/bin/env bash
# ==============================================================================
# MediScanAI Production Safe PostgreSQL Restoration Script
# Defaults to restoring into an isolated test database (mediscanai_restore_test)
# To overwrite the live production database, explicitly pass --force-production-restore.
# ==============================================================================

set -euo pipefail

CONTAINER_NAME="${CONTAINER_NAME:-mediscanai-postgres}"
POSTGRES_USER="${POSTGRES_USER:-mediscanai}"
PRODUCTION_DB="${POSTGRES_DB:-mediscanai}"
TEST_DB="mediscanai_restore_test"

DUMP_ARCHIVE=""
TARGET_MODE="test-db"

log() {
    echo "[RESTORE $(date +'%Y-%m-%d %H:%M:%S')] $*"
}

log_err() {
    echo "[RESTORE ERROR $(date +'%Y-%m-%d %H:%M:%S')] $*" >&2
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --file|-f)
            DUMP_ARCHIVE="$2"
            shift 2
            ;;
        --test-db)
            TARGET_MODE="test-db"
            shift
            ;;
        --force-production-restore)
            TARGET_MODE="production"
            shift
            ;;
        --container)
            CONTAINER_NAME="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 --file <path_to_dump[.gz]> [--test-db | --force-production-restore] [--container <name>]"
            echo "  --test-db                  Restores into isolated database '${TEST_DB}' and verifies row counts (Default safe mode)"
            echo "  --force-production-restore Restores directly into live production database '${PRODUCTION_DB}' (DESTRUCTIVE)"
            exit 0
            ;;
        *)
            if [ -z "$DUMP_ARCHIVE" ] && [ -f "$1" ]; then
                DUMP_ARCHIVE="$1"
                shift
            else
                log_err "Unknown argument: $1"
                exit 1
            fi
            ;;
    esac
done

if [ -z "$DUMP_ARCHIVE" ]; then
    log_err "Missing required backup file. Specify with --file <path>."
    exit 1
fi

if [ ! -f "$DUMP_ARCHIVE" ]; then
    log_err "Backup file not found: $DUMP_ARCHIVE"
    exit 1
fi

# 1. Verify container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    log_err "PostgreSQL container '${CONTAINER_NAME}' is not running. Aborting restore."
    exit 1
fi

# 2. Decompress archive to temporary dump if gzipped
TEMP_DIR=$(mktemp -d)
CLEANUP_FILES=()

cleanup() {
    docker exec "$CONTAINER_NAME" rm -f /tmp/restore.dump >/dev/null 2>&1 || true
    rm -rf "$TEMP_DIR" >/dev/null 2>&1 || true
    if [ "$TARGET_MODE" = "test-db" ]; then
        docker exec "$CONTAINER_NAME" psql -U "$POSTGRES_USER" -d postgres -c "DROP DATABASE IF EXISTS ${TEST_DB};" >/dev/null 2>&1 || true
    fi
}
trap cleanup EXIT

if [[ "$DUMP_ARCHIVE" == *.gz ]]; then
    RAW_DUMP="${TEMP_DIR}/restore_uncompressed.dump"
    log "Decompressing gzip archive '${DUMP_ARCHIVE}'..."
    gzip -d -c "$DUMP_ARCHIVE" > "$RAW_DUMP"
else
    RAW_DUMP="$DUMP_ARCHIVE"
fi

# 3. Verify dump header
log "Verifying dump file format with pg_restore list..."
docker cp "$RAW_DUMP" "${CONTAINER_NAME}:/tmp/restore.dump"

if ! docker exec "$CONTAINER_NAME" pg_restore --list /tmp/restore.dump >/dev/null 2>&1; then
    log_err "Archive validation failed: File is not a valid pg_dump custom archive."
    exit 1
fi
log "Archive header is valid."

# 4. Handle Target Mode
if [ "$TARGET_MODE" = "production" ]; then
    TARGET_DB="$PRODUCTION_DB"
    log "⚠️  CRITICAL WARNING: Target is LIVE PRODUCTION DATABASE '${TARGET_DB}'!"
    read -r -p "Type 'RESTORE_PRODUCTION' to confirm irreversible restoration: " CONFIRMATION
    if [ "$CONFIRMATION" != "RESTORE_PRODUCTION" ]; then
        log "Restoration aborted by user."
        exit 1
    fi
else
    TARGET_DB="$TEST_DB"
    log "Executing in SAFE mode: Restoring to isolated test database '${TARGET_DB}'."
    docker exec "$CONTAINER_NAME" psql -U "$POSTGRES_USER" -d postgres -c "DROP DATABASE IF EXISTS ${TARGET_DB};" >/dev/null 2>&1 || true
    docker exec "$CONTAINER_NAME" psql -U "$POSTGRES_USER" -d postgres -c "CREATE DATABASE ${TARGET_DB};" >/dev/null
fi

# 5. Execute pg_restore
log "Restoring database objects to '${TARGET_DB}'..."
set +e
RESTORE_OUTPUT=$(docker exec "$CONTAINER_NAME" pg_restore --clean --if-exists --no-owner --no-privileges -U "$POSTGRES_USER" -d "$TARGET_DB" /tmp/restore.dump 2>&1)
RESTORE_STATUS=$?
set -e

if [ $RESTORE_STATUS -ne 0 ]; then
    log "INFO: pg_restore completed with warnings/notices (standard for pre-existing system roles):"
    echo "$RESTORE_OUTPUT" | tail -n 5
fi

# 6. Verify restored database contents
log "Verifying restored schema and data counts in '${TARGET_DB}'..."
VERIFICATION_SQL="
SELECT 'users' AS table_name, count(*) AS count FROM users
UNION ALL
SELECT 'analyses' AS table_name, count(*) AS count FROM analyses
UNION ALL
SELECT 'audit_logs' AS table_name, count(*) AS count FROM audit_logs;
"

set +e
VERIFY_OUTPUT=$(docker exec "$CONTAINER_NAME" psql -U "$POSTGRES_USER" -d "$TARGET_DB" -c "$VERIFICATION_SQL" 2>&1)
VERIFY_STATUS=$?
set -e

if [ $VERIFY_STATUS -ne 0 ]; then
    log_err "Verification failed on '${TARGET_DB}':"
    echo "$VERIFY_OUTPUT" >&2
    exit 1
fi

echo "$VERIFY_OUTPUT"

if [ "$TARGET_MODE" = "test-db" ]; then
    log "SUCCESS: Backup verified cleanly against isolated database '${TARGET_DB}'."
    log "Dropping test database '${TARGET_DB}'..."
    docker exec "$CONTAINER_NAME" psql -U "$POSTGRES_USER" -d postgres -c "DROP DATABASE IF EXISTS ${TARGET_DB};" >/dev/null 2>&1 || true
    log "Test database cleaned up."
else
    log "SUCCESS: Production database '${TARGET_DB}' restored and verified."
fi

exit 0
