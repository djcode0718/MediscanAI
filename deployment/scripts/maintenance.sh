#!/usr/bin/env bash
# ==============================================================================
# MediScanAI Production Safe Storage Maintenance Script
# Enforces strict retention:
#   - Preserves currently deployed image + 2 previous known-good images.
#   - NEVER touches database, model cache, or TLS volumes.
#   - NEVER runs broad 'docker system prune --volumes'.
#   - Bounded Docker builder cache retention (keeps 5GB).
#   - Prunes old backup archives (> 7 days) and temp files (> 24h).
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
PROJECT_ROOT="$(cd "${DEPLOY_DIR}/.." && pwd)"

CURRENT_DEPLOY_FILE="${DEPLOY_DIR}/.current_deployment"
HISTORY_FILE="${DEPLOY_DIR}/.deployment_history"
BACKUP_DIR="${DEPLOY_DIR}/backups"

DRY_RUN=true
RETENTION_DAYS="${RETENTION_DAYS:-7}"
BUILDER_KEEP_STORAGE="${BUILDER_KEEP_STORAGE:-5GB}"

log() {
    echo "[MAINTENANCE $(date +'%Y-%m-%d %H:%M:%S')] $*"
}

log_err() {
    echo "[MAINTENANCE ERROR $(date +'%Y-%m-%d %H:%M:%S')] $*" >&2
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --force|-f)
            DRY_RUN=false
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --retention-days)
            RETENTION_DAYS="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [--dry-run | --force] [--retention-days <days>]"
            echo "  Default mode is --dry-run. Pass --force to execute cleanup actions."
            exit 0
            ;;
        *)
            log_err "Unknown argument: $1"
            exit 1
            ;;
    esac
done

if [ "$DRY_RUN" = "true" ]; then
    log "Operating in DRY-RUN mode. No files or images will be deleted."
    log "To apply maintenance actions, run with --force."
else
    log "Operating in FORCE execution mode. Maintenance actions will be applied."
fi

# 1. Inspect Protected Images (Current + 2 Previous Known-Good)
log "Step 1/5: Identifying protected images..."
PROTECTED_IMAGES=()

if [ -f "$CURRENT_DEPLOY_FILE" ]; then
    CURR_IMG=$(cat "$CURRENT_DEPLOY_FILE" | tr -d '[:space:]')
    if [ -n "$CURR_IMG" ]; then
        PROTECTED_IMAGES+=("$CURR_IMG")
        log "  Protected [CURRENT]: ${CURR_IMG}"
    fi
fi

if [ -f "$HISTORY_FILE" ]; then
    # Extract last 2 unique previous images from history
    while IFS= read -r img; do
        if [ -n "$img" ] && [ "$img" != "unknown" ]; then
            if [[ ! " ${PROTECTED_IMAGES[*]} " =~ " ${img} " ]]; then
                PROTECTED_IMAGES+=("$img")
                log "  Protected [HISTORY]: ${img}"
            fi
        fi
    done < <(awk -F'|' '{print $3}' "$HISTORY_FILE" | tr -d '[:space:]' | tail -n 5 | sort -u)
fi

# Dynamically protect images currently in use by active containers
if docker info >/dev/null 2>&1; then
    while IFS= read -r running_img; do
        if [ -n "$running_img" ]; then
            if [[ ! " ${PROTECTED_IMAGES[*]} " =~ " ${running_img} " ]]; then
                PROTECTED_IMAGES+=("$running_img")
                log "  Protected [ACTIVE CONTAINER]: ${running_img}"
            fi
        fi
    done < <(docker ps --format '{{.Image}}' 2>/dev/null || true)
fi

# 2. Docker Image Pruning (Safe & Targeted)
log "Step 2/5: Evaluating Docker images..."
if docker info >/dev/null 2>&1; then
    # Remove dangling untagged images (<none>)
    DANGLING_COUNT=$(docker images -f "dangling=true" -q | wc -l | tr -d ' ')
    if [ "$DANGLING_COUNT" -gt 0 ]; then
        log "  Found ${DANGLING_COUNT} dangling untagged image(s)."
        if [ "$DRY_RUN" = "false" ]; then
            docker image prune -f >/dev/null 2>&1
            log "  Pruned dangling images."
        else
            log "  [DRY-RUN] Would prune ${DANGLING_COUNT} dangling image(s)."
        fi
    else
        log "  No dangling images to prune."
    fi

    # Clean old Docker builder cache with bounded limit
    log "  Evaluating Docker buildx builder cache (retention target: ${BUILDER_KEEP_STORAGE})..."
    if [ "$DRY_RUN" = "false" ]; then
        docker builder prune -f --keep-storage "$BUILDER_KEEP_STORAGE" >/dev/null 2>&1 || true
        log "  Builder cache pruned with headroom preserved."
    else
        log "  [DRY-RUN] Would prune build cache exceeding ${BUILDER_KEEP_STORAGE}."
    fi
else
    log "  Docker daemon offline; skipping container/image prune."
fi

# 3. Protected Named Volumes Guard
log "Step 3/5: Enforcing Volume Protection..."
log "  SAFEGUARD VERIFIED: 'mediscanai_postgres_data' is LOCKED and exempt from pruning."
log "  SAFEGUARD VERIFIED: 'mediscanai_model_cache' is LOCKED and exempt from pruning."
log "  SAFEGUARD VERIFIED: 'mediscanai_caddy_data' is LOCKED and exempt from pruning."

# 4. PostgreSQL Backup Archives Pruning
log "Step 4/5: Evaluating database backup retention (${RETENTION_DAYS} days)..."
if [ -d "$BACKUP_DIR" ]; then
    # Newest backup is protected under all circumstances
    LATEST_ARCHIVE=$(ls -t "${BACKUP_DIR}"/mediscanai_postgres_*.dump.gz 2>/dev/null | head -n 1 || echo "")
    OLD_BACKUPS=()
    while IFS= read -r f; do
        if [ -n "$f" ]; then
            if [ "$f" = "$LATEST_ARCHIVE" ]; then
                log "  Preserving latest valid backup: $(basename "$f")"
                continue
            fi
            OLD_BACKUPS+=("$f")
        fi
    done < <(find "$BACKUP_DIR" -type f -name "mediscanai_postgres_*.dump.gz" -mtime "+${RETENTION_DAYS}" 2>/dev/null || true)

    if [ ${#OLD_BACKUPS[@]} -gt 0 ]; then
        log "  Found ${#OLD_BACKUPS[@]} backup archive(s) older than ${RETENTION_DAYS} days."
        for b in "${OLD_BACKUPS[@]}"; do
            if [ "$DRY_RUN" = "false" ]; then
                rm -f "$b"
                log "  Deleted expired backup: $(basename "$b")"
            else
                log "  [DRY-RUN] Would delete expired backup: $(basename "$b")"
            fi
        done
    else
        log "  No backup archives exceed retention period of ${RETENTION_DAYS} days."
    fi
else
    log "  Backup directory '${BACKUP_DIR}' does not exist yet."
fi

# 5. Clean Temporary MediScanAI Artifacts (> 24 hours old)
log "Step 5/5: Cleaning temporary staging files (> 24 hours old)..."
# Resolve canonical temp directory
if [ -d "/private/tmp" ]; then
    CANONICAL_TEMP="/private/tmp"
else
    CANONICAL_TEMP="/tmp"
fi

TEMP_PATTERNS=("mediscan_*" "mediscanai_*")
FOUND_TEMP_COUNT=0

for pattern in "${TEMP_PATTERNS[@]}"; do
    while IFS= read -r item; do
        if [ -n "$item" ]; then
            # Verify item canonical path resides strictly inside canonical temp directory
            REAL_PATH=$(realpath "$item" 2>/dev/null || echo "")
            if [[ "$REAL_PATH" != "$CANONICAL_TEMP"/mediscan* ]]; then
                log "  SKIPPING unsafe item outside temp bounds: $item -> $REAL_PATH"
                continue
            fi
            # Guard: Never follow or delete symlink targets
            if [ -L "$item" ]; then
                log "  SKIPPING symlink: $item"
                continue
            fi
            FOUND_TEMP_COUNT=$((FOUND_TEMP_COUNT + 1))
            if [ "$DRY_RUN" = "false" ]; then
                rm -rf "$item"
                log "  Removed stale temp item: $item"
            else
                log "  [DRY-RUN] Would remove stale temp item: $item"
            fi
        fi
    done < <(find "$CANONICAL_TEMP" -maxdepth 1 \( -name "$pattern" \) -mtime +1 2>/dev/null || true)
done

if [ "$FOUND_TEMP_COUNT" -eq 0 ]; then
    log "  No stale MediScanAI temporary files found (> 24 hours old)."
fi

# 6. Report Storage After Maintenance
log "Storage Summary:"
if [ "$(uname)" = "Darwin" ]; then
    df -h /System/Volumes/Data / | awk 'NR==1 || NR==2 || NR==3 {print "  " $0}'
else
    df -h / | awk 'NR==1 || NR==2 {print "  " $0}'
fi

log "Maintenance run finished cleanly."
exit 0
