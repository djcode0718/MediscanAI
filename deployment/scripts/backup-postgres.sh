#!/usr/bin/env bash
# ==============================================================================
# MediScanAI Production Automated PostgreSQL Backup Script
# Creates a compressed, timestamped logical dump and verifies archive integrity.
# Enforces strict 600 file permissions. Safe logging: No passwords printed.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

BACKUP_DIR="${BACKUP_DIR:-${PROJECT_ROOT}/deployment/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
CONTAINER_NAME="${CONTAINER_NAME:-mediscanai-postgres}"
POSTGRES_USER="${POSTGRES_USER:-mediscanai}"
POSTGRES_DB="${POSTGRES_DB:-mediscanai}"

log() {
    echo "[BACKUP $(date +'%Y-%m-%d %H:%M:%S')] $*"
}

log_err() {
    echo "[BACKUP ERROR $(date +'%Y-%m-%d %H:%M:%S')] $*" >&2
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --backup-dir)
            BACKUP_DIR="$2"
            shift 2
            ;;
        --retention-days)
            RETENTION_DAYS="$2"
            shift 2
            ;;
        --container)
            CONTAINER_NAME="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [--backup-dir <dir>] [--retention-days <days>] [--container <name>]"
            exit 0
            ;;
        *)
            log_err "Unknown argument: $1"
            exit 1
            ;;
    esac
done

mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DUMP_FILENAME="mediscanai_postgres_${TIMESTAMP}.dump"
DUMP_PATH="${BACKUP_DIR}/${DUMP_FILENAME}"
GZ_PATH="${DUMP_PATH}.gz"

log "Starting database backup for database '${POSTGRES_DB}' on container '${CONTAINER_NAME}'..."
log "Destination directory: ${BACKUP_DIR}"

# 1. Verify container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    log_err "PostgreSQL container '${CONTAINER_NAME}' is not running. Aborting backup."
    exit 1
fi

# Ensure clean state in container
docker exec "$CONTAINER_NAME" rm -f /tmp/backup.dump >/dev/null 2>&1 || true

cleanup() {
    docker exec "$CONTAINER_NAME" rm -f /tmp/backup.dump >/dev/null 2>&1 || true
    rm -f "$DUMP_PATH" >/dev/null 2>&1 || true
}
trap cleanup EXIT

# 2. Execute pg_dump within container (custom format: compressed & restorable)
log "Executing pg_dump in container..."
docker exec "$CONTAINER_NAME" pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom -f /tmp/backup.dump

# 3. Copy dump out of container to host backup directory
log "Copying dump file from container to host..."
docker cp "${CONTAINER_NAME}:/tmp/backup.dump" "$DUMP_PATH"

# 4. Verify integrity of dump before compressing
log "Verifying dump integrity using pg_restore table of contents check..."
if ! docker exec -i "$CONTAINER_NAME" pg_restore --list /tmp/backup.dump >/dev/null 2>&1; then
    log_err "Integrity check failed: Dump file appears corrupt."
    exit 1
fi
log "Integrity verification PASSED."

# 5. Compress dump archive on host with gzip
log "Compressing backup archive with gzip..."
gzip -9 -c "$DUMP_PATH" > "$GZ_PATH"
chmod 600 "$GZ_PATH"

ARCHIVE_SIZE=$(du -h "$GZ_PATH" | cut -f1)
log "Backup successfully created: ${GZ_PATH} (${ARCHIVE_SIZE})"

# 6. Apply retention pruning (guarantee latest backup is permanently preserved)
if [ -n "$RETENTION_DAYS" ] && [ "$RETENTION_DAYS" -gt 0 ] 2>/dev/null; then
    log "Applying retention policy: Pruning backups older than ${RETENTION_DAYS} days..."
    # Identify newest backup to guarantee it is NEVER deleted regardless of age
    LATEST_ARCHIVE=$(ls -t "${BACKUP_DIR}"/mediscanai_postgres_*.dump.gz 2>/dev/null | head -n 1 || echo "")
    DELETED_COUNT=0
    while IFS= read -r old_file; do
        if [ -n "$old_file" ]; then
            if [ "$old_file" = "$LATEST_ARCHIVE" ]; then
                log "Preserving latest valid backup despite age threshold: $(basename "$old_file")"
                continue
            fi
            rm -f "$old_file"
            DELETED_COUNT=$((DELETED_COUNT + 1))
            log "Pruned old backup: $(basename "$old_file")"
        fi
    done < <(find "$BACKUP_DIR" -type f -name "mediscanai_postgres_*.dump.gz" -mtime "+${RETENTION_DAYS}" 2>/dev/null || true)
    log "Retention pruning finished (${DELETED_COUNT} archives removed)."
fi

# Save latest backup marker
echo "${GZ_PATH}" > "${BACKUP_DIR}/.latest_backup"

log "PostgreSQL backup completed successfully."
exit 0
