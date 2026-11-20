#!/bin/bash
# ==============================================================================
# MediScanAI Production Automated Backup Script
# Performs logical dumps of PostgreSQL, environment config, and TLS certificates
# Enforces strict 600 permissions on output archives
# ==============================================================================

set -e

BACKUP_DIR="${1:-./backups}"
RETENTION_DAYS="${2}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
TARGET_DIR="${BACKUP_DIR}/mediscanai_backup_${TIMESTAMP}"

mkdir -p "$TARGET_DIR"
chmod 700 "$TARGET_DIR"

# Clean up container temp files on exit
CONTAINER_NAME="mediscanai-postgres"
trap 'docker exec "$CONTAINER_NAME" rm -f /tmp/backup.dump >/dev/null 2>&1 || true' EXIT
if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "[1/3] Creating logical dump of PostgreSQL database..."
    DUMP_FILE="${TARGET_DIR}/mediscanai_postgres_${TIMESTAMP}.dump"
    docker exec "$CONTAINER_NAME" pg_dump -U mediscanai -d mediscanai --format=custom -f /tmp/backup.dump
    docker cp "${CONTAINER_NAME}:/tmp/backup.dump" "$DUMP_FILE"
    docker exec "$CONTAINER_NAME" rm /tmp/backup.dump
    chmod 600 "$DUMP_FILE"
    echo "      Database dump created: $(du -h "$DUMP_FILE" | cut -f1)"
else
    echo "[1/3] WARNING: ${CONTAINER_NAME} is not running. Skipping DB dump."
fi

# 2. Environment Configuration Backup
if [ -f "deployment/.env" ]; then
    echo "[2/3] Backing up deployment configuration..."
    cp deployment/.env "${TARGET_DIR}/mediscanai_env_${TIMESTAMP}.bak"
    chmod 600 "${TARGET_DIR}/mediscanai_env_${TIMESTAMP}.bak"
    echo "      Configuration backup saved."
elif [ -f ".env" ]; then
    echo "[2/3] Backing up deployment configuration..."
    cp .env "${TARGET_DIR}/mediscanai_env_${TIMESTAMP}.bak"
    chmod 600 "${TARGET_DIR}/mediscanai_env_${TIMESTAMP}.bak"
    echo "      Configuration backup saved."
else
    echo "[2/3] WARNING: .env file not found. Skipping config backup."
fi

# 3. Caddy TLS Certificates Backup
CADDY_CONTAINER="mediscanai-caddy"
if docker ps --format '{{.Names}}' | grep -q "^${CADDY_CONTAINER}$"; then
    echo "[3/3] Backing up Caddy TLS certificates and data..."
    docker cp "${CADDY_CONTAINER}:/data" "${TARGET_DIR}/caddy_data" 2>/dev/null || true
    chmod -R 600 "${TARGET_DIR}/caddy_data" 2>/dev/null || true
    echo "      Caddy data saved."
else
    echo "[3/3] INFO: Caddy container not active. Skipping TLS cert backup."
fi

echo "----------------------------------------------------------------"
echo "Backup completed successfully at: ${TARGET_DIR}"
ls -lh "$TARGET_DIR"

# 4. Optional Retention Pruning (if retention days passed as argument 2)
if [ -n "$RETENTION_DAYS" ] && [ "$RETENTION_DAYS" -gt 0 ] 2>/dev/null; then
    echo "Pruning backups older than ${RETENTION_DAYS} days in ${BACKUP_DIR}..."
    find "$BACKUP_DIR" -maxdepth 1 -mindepth 1 -type d -name "mediscanai_backup_*" -mtime "+${RETENTION_DAYS}" -exec rm -rf {} + 2>/dev/null || true
    echo "Pruning complete."
fi

echo "================================================================"
