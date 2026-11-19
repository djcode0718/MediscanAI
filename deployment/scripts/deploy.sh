#!/usr/bin/env bash
# ==============================================================================
# MediScanAI Production Deployment Script (MacBook Air M4 Target)
# Deploys immutable Docker image to production Compose stack.
# Checks disk thresholds (70%/80%/90%), preserves persistent volumes,
# performs pre-deployment database backup, and verifies health.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
PROJECT_ROOT="$(cd "${DEPLOY_DIR}/.." && pwd)"

COMPOSE_FILE="${DEPLOY_DIR}/compose.yaml"
ENV_FILE="${DEPLOY_DIR}/.env"
CURRENT_DEPLOY_FILE="${DEPLOY_DIR}/.current_deployment"
HISTORY_FILE="${DEPLOY_DIR}/.deployment_history"

IMAGE_TAG=""
DRY_RUN=false
SKIP_PULL=false
SKIP_BACKUP=false

log() {
    echo "[DEPLOY $(date +'%Y-%m-%d %H:%M:%S')] $*"
}

log_err() {
    echo "[DEPLOY ERROR $(date +'%Y-%m-%d %H:%M:%S')] $*" >&2
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --image|-i)
            IMAGE_TAG="$2"
            shift 2
            ;;
        --compose-file)
            COMPOSE_FILE="$2"
            shift 2
            ;;
        --env-file)
            ENV_FILE="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --skip-pull)
            SKIP_PULL=true
            shift
            ;;
        --skip-backup)
            SKIP_BACKUP=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 --image <image_ref> [--dry-run] [--skip-pull] [--skip-backup]"
            exit 0
            ;;
        *)
            if [ -z "$IMAGE_TAG" ]; then
                IMAGE_TAG="$1"
                shift
            else
                log_err "Unknown option: $1"
                exit 1
            fi
            ;;
    esac
done

if [ -z "$IMAGE_TAG" ]; then
    log_err "Missing target image reference. Specify with --image <image_ref>."
    exit 1
fi

log "Target deployment image: ${IMAGE_TAG}"
log "Compose file: ${COMPOSE_FILE}"
log "Environment file: ${ENV_FILE}"

# 1. Validate Docker Daemon
log "Step 1/7: Validating Docker daemon availability..."
if ! docker info >/dev/null 2>&1; then
    log_err "Docker daemon is not running or socket is unreachable."
    exit 1
fi
log "Docker daemon is active and responding."

# 2. Check Host Storage Capacity & Thresholds
log "Step 2/7: Checking host SSD storage capacity against safety thresholds..."
# Calculate root filesystem usage percentage
if [ "$(uname)" = "Darwin" ]; then
    USED_PCT=$(df -k / | awk 'NR==2 {gsub("%","",$5); print $5}')
    AVAIL_HUMAN=$(df -h / | awk 'NR==2 {print $4}')
else
    USED_PCT=$(df -k / | awk 'NR==2 {gsub("%","",$5); print $5}')
    AVAIL_HUMAN=$(df -h / | awk 'NR==2 {print $4}')
fi

log "Root filesystem storage: ${USED_PCT}% used (${AVAIL_HUMAN} available)."

if [ "$USED_PCT" -ge 90 ]; then
    log_err "CRITICAL: Storage capacity is at ${USED_PCT}% (>= 90% threshold). Blocking deployment to prevent system freeze."
    exit 1
elif [ "$USED_PCT" -ge 80 ]; then
    log "WARNING: Storage utilization elevated at ${USED_PCT}% (>= 80% threshold). Recommend running maintenance.sh."
elif [ "$USED_PCT" -ge 70 ]; then
    log "NOTICE: Storage utilization at ${USED_PCT}% (>= 70% threshold)."
fi

# 3. Validate Configuration Environment
log "Step 3/7: Validating environment configuration..."
if [ ! -f "$ENV_FILE" ]; then
    log_err "Production configuration file '${ENV_FILE}' not found."
    exit 1
fi

# Check permissions
if [ "$(uname)" = "Darwin" ]; then
    PERMS=$(stat -f "%Lp" "$ENV_FILE" 2>/dev/null || echo "")
else
    PERMS=$(stat -c "%a" "$ENV_FILE" 2>/dev/null || echo "")
fi

if [ "$PERMS" != "600" ] && [ "$PERMS" != "400" ]; then
    log "NOTICE: Normalizing file permissions on ${ENV_FILE} to 600..."
    chmod 600 "$ENV_FILE" 2>/dev/null || true
fi

# 4. Record Current Deployment State
log "Step 4/7: Recording current deployment reference for rollback protection..."
PREVIOUS_IMAGE="unknown"
if [ -f "$CURRENT_DEPLOY_FILE" ]; then
    PREVIOUS_IMAGE=$(cat "$CURRENT_DEPLOY_FILE" | tr -d '[:space:]')
fi
log "Current/previous image recorded: ${PREVIOUS_IMAGE}"

if [ "$DRY_RUN" = "true" ]; then
    log "DRY RUN MODE: Would pull '${IMAGE_TAG}', apply Compose update, and verify health."
    log "DRY RUN completed successfully. No changes applied."
    exit 0
fi

# 5. Pre-Deployment Database Backup
if [ "$SKIP_BACKUP" != "true" ]; then
    log "Step 5/7: Executing pre-deployment PostgreSQL safety backup..."
    if [ -x "${SCRIPT_DIR}/backup-postgres.sh" ]; then
        "${SCRIPT_DIR}/backup-postgres.sh" --retention-days 7 || {
            log "WARNING: Pre-deployment backup failed or postgres was offline. Proceeding cautiously..."
        }
    else
        log "WARNING: backup-postgres.sh not executable or not found. Skipping backup."
    fi
else
    log "Step 5/7: Skipping pre-deployment database backup (--skip-backup passed)."
fi

# 6. Pull Target Image & Apply Compose Update
log "Step 6/7: Deploying backend service..."
if [ "$SKIP_PULL" != "true" ]; then
    log "Pulling target image: ${IMAGE_TAG}..."
    docker pull "$IMAGE_TAG"
fi

export MEDISCANAI_IMAGE="$IMAGE_TAG"

# Update backend container while keeping postgres and networks intact
log "Applying Docker Compose update (backend service only)..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d --no-deps backend

# Update current deployment marker
echo "$IMAGE_TAG" > "$CURRENT_DEPLOY_FILE"
echo "$(date +'%Y-%m-%d %H:%M:%S') | DEPLOY | ${IMAGE_TAG} | prev: ${PREVIOUS_IMAGE}" >> "$HISTORY_FILE"

# 7. Post-Deployment Health Verification
log "Step 7/7: Executing post-deployment health check..."
if [ -x "${SCRIPT_DIR}/health-check.sh" ]; then
    if ! "${SCRIPT_DIR}/health-check.sh" --retries 10 --delay 4; then
        log_err "Health verification FAILED after deploying ${IMAGE_TAG}!"
        log_err "Automated rollback recommended using: ${SCRIPT_DIR}/rollback.sh --image ${PREVIOUS_IMAGE}"
        exit 1
    fi
else
    log "WARNING: health-check.sh not found. Polling /api/health directly..."
    sleep 5
    curl -f http://localhost:8000/api/health || {
        log_err "Direct health probe failed."
        exit 1
    }
fi

log "================================================================"
log "Deployment of ${IMAGE_TAG} COMPLETED and VERIFIED successfully."
log "================================================================"
exit 0
