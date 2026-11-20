#!/usr/bin/env bash
# ==============================================================================
# MediScanAI Production Rollback Script (MacBook Air M4 Target)
# Restores backend service to previous known-good immutable Docker image.
# Preserves PostgreSQL data and verifies health post-rollback.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

COMPOSE_FILE="${DEPLOY_DIR}/compose.yaml"
ENV_FILE="${DEPLOY_DIR}/.env"
CURRENT_DEPLOY_FILE="${DEPLOY_DIR}/.current_deployment"
HISTORY_FILE="${DEPLOY_DIR}/.deployment_history"

ROLLBACK_IMAGE=""
DRY_RUN=false

log() {
    echo "[ROLLBACK $(date +'%Y-%m-%d %H:%M:%S')] $*"
}

log_err() {
    echo "[ROLLBACK ERROR $(date +'%Y-%m-%d %H:%M:%S')] $*" >&2
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --image|-i)
            ROLLBACK_IMAGE="$2"
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
        -h|--help)
            echo "Usage: $0 [--image <target_image>] [--dry-run]"
            exit 0
            ;;
        *)
            if [ -z "$ROLLBACK_IMAGE" ]; then
                ROLLBACK_IMAGE="$1"
                shift
            else
                log_err "Unknown option: $1"
                exit 1
            fi
            ;;
    esac
done

# If no target image provided, determine previous image from deployment history
if [ -z "$ROLLBACK_IMAGE" ]; then
    if [ -f "$HISTORY_FILE" ]; then
        # Find the second-to-last deployed image or previous tag recorded
        ROLLBACK_IMAGE=$(tail -n 2 "$HISTORY_FILE" | head -n 1 | awk -F'|' '{print $3}' | tr -d '[:space:]' || echo "")
    fi
fi

if [ -z "$ROLLBACK_IMAGE" ] || [ "$ROLLBACK_IMAGE" = "unknown" ]; then
    log_err "Could not resolve a previous known-good image from ${HISTORY_FILE}."
    log_err "Please supply an explicit target image via --image <image_ref>."
    exit 1
fi

log "Initiating rollback to known-good image: ${ROLLBACK_IMAGE}"

# 1. Validate Docker Daemon
if ! docker info >/dev/null 2>&1; then
    log_err "Docker daemon is unreachable. Cannot execute rollback."
    exit 1
fi

if [ "$DRY_RUN" = "true" ]; then
    log "DRY RUN MODE: Would roll back backend service to '${ROLLBACK_IMAGE}'."
    log "DRY RUN completed successfully."
    exit 0
fi

# 2. Check if image exists locally; pull if missing
if ! docker image inspect "$ROLLBACK_IMAGE" >/dev/null 2>&1; then
    log "Image '${ROLLBACK_IMAGE}' not found locally. Attempting to pull from registry..."
    docker pull "$ROLLBACK_IMAGE" || {
        log_err "Failed to pull rollback image '${ROLLBACK_IMAGE}'."
        exit 1
    }
fi

CURRENT_BEFORE_ROLLBACK="unknown"
if [ -f "$CURRENT_DEPLOY_FILE" ]; then
    CURRENT_BEFORE_ROLLBACK=$(cat "$CURRENT_DEPLOY_FILE" | tr -d '[:space:]')
fi

# 3. Apply Compose Update
export MEDISCANAI_IMAGE="$ROLLBACK_IMAGE"

log "Restarting backend service with rollback image (preserving PostgreSQL)..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d --no-deps backend

# 4. Update Deployment Record
echo "$ROLLBACK_IMAGE" > "$CURRENT_DEPLOY_FILE"
echo "$(date +'%Y-%m-%d %H:%M:%S') | ROLLBACK | ${ROLLBACK_IMAGE} | from: ${CURRENT_BEFORE_ROLLBACK}" >> "$HISTORY_FILE"

# 5. Verify Health Post-Rollback
log "Verifying health post-rollback..."
if [ -x "${SCRIPT_DIR}/health-check.sh" ]; then
    if ! "${SCRIPT_DIR}/health-check.sh" --retries 8 --delay 3; then
        log_err "CRITICAL: Health check FAILED after rollback to ${ROLLBACK_IMAGE}!"
        exit 1
    fi
fi

log "================================================================"
log "Rollback to ${ROLLBACK_IMAGE} COMPLETED and VERIFIED successfully."
log "================================================================"
exit 0
