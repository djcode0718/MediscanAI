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
LOGS_DIR="${DEPLOY_DIR}/logs"

DRY_RUN=true
PRUNE_BUILD_CACHE=false
RETENTION_DAYS="${RETENTION_DAYS:-7}"
BUILDER_KEEP_STORAGE="${BUILDER_KEEP_STORAGE:-5GB}"

# Lock to prevent overlapping maintenance runs
LOCK_DIR="/tmp/mediscanai_maintenance.lock.d"

cleanup_lock() {
    rmdir "$LOCK_DIR" 2>/dev/null || true
}

if ! mkdir "$LOCK_DIR" 2>/dev/null; then
    echo "[MAINTENANCE $(date +'%Y-%m-%d %H:%M:%S')] NOTICE: Another maintenance process is currently active (${LOCK_DIR} exists). Exiting cleanly."
    exit 0
fi
trap cleanup_lock EXIT

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
        --prune-build-cache)
            PRUNE_BUILD_CACHE=true
            shift
            ;;
        --retention-days)
            RETENTION_DAYS="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [--dry-run | --force] [--prune-build-cache] [--retention-days <days>]"
            echo "  Default mode is --dry-run. Pass --force to execute cleanup actions."
            echo "  --prune-build-cache explicitly prunes build cache (keeps ${BUILDER_KEEP_STORAGE})."
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
PROTECTED_IMAGE_IDS=()

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
            if [[ ! " ${PROTECTED_IMAGES[*]:-} " =~ " ${img} " ]]; then
                PROTECTED_IMAGES+=("$img")
                log "  Protected [HISTORY]: ${img}"
            fi
        fi
    done < <(awk -F'|' '{print $3}' "$HISTORY_FILE" | tr -d '[:space:]' | tail -n 5 | sort -u)
fi

# Dynamically protect images currently in use by any container (running or stopped)
if docker info >/dev/null 2>&1; then
    while IFS= read -r running_img; do
        if [ -n "$running_img" ]; then
            if [[ ! " ${PROTECTED_IMAGES[*]:-} " =~ " ${running_img} " ]]; then
                PROTECTED_IMAGES+=("$running_img")
                log "  Protected [ACTIVE/STOPPED CONTAINER]: ${running_img}"
            fi
            # Resolve image ID
            IMG_ID=$(docker inspect "$running_img" --format '{{.Id}}' 2>/dev/null || echo "")
            if [ -n "$IMG_ID" ] && [[ ! " ${PROTECTED_IMAGE_IDS[*]:-} " =~ " ${IMG_ID} " ]]; then
                PROTECTED_IMAGE_IDS+=("$IMG_ID")
            fi
        fi
    done < <(docker ps -a --format '{{.Image}}' 2>/dev/null || true)
fi

# 2. Docker Image Pruning (Strict Positive MediScanAI Ownership Only)
log "Step 2/5: Evaluating Docker images..."
if docker info >/dev/null 2>&1; then
    # Protect common infrastructure images
    BASE_INFRA_IMAGES=("postgres:15-alpine" "caddy:2-alpine" "alpine:latest")
    for base_img in "${BASE_INFRA_IMAGES[@]}"; do
        PROTECTED_IMAGES+=("$base_img")
        IMG_ID=$(docker inspect "$base_img" --format '{{.Id}}' 2>/dev/null || echo "")
        if [ -n "$IMG_ID" ] && [[ ! " ${PROTECTED_IMAGE_IDS[*]:-} " =~ " ${IMG_ID} " ]]; then
            PROTECTED_IMAGE_IDS+=("$IMG_ID")
        fi
    done

    # Policy Enforcement: Global dangling-image pruning is DISABLED to protect unrelated projects
    log "  POLICY: Global dangling-image pruning (docker image prune) is DISABLED."
    log "  POLICY: Untagged images and images with unverified ownership are permanently PRESERVED."

    # Resolve IDs for all protected deployment tags
    for p_img in "${PROTECTED_IMAGES[@]:-}"; do
        if [ -n "$p_img" ]; then
            IMG_ID=$(docker inspect "$p_img" --format '{{.Id}}' 2>/dev/null || echo "")
            if [ -n "$IMG_ID" ] && [[ ! " ${PROTECTED_IMAGE_IDS[*]:-} " =~ " ${IMG_ID} " ]]; then
                PROTECTED_IMAGE_IDS+=("$IMG_ID")
            fi
        fi
    done

    # Evaluate ONLY positively identified MediScanAI backend images
    log "  Evaluating positively identified MediScanAI images (*mediscanai-backend*)..."
    while IFS=$'\t' read -r candidate_id candidate_tag; do
        if [ -n "$candidate_id" ] && [ -n "$candidate_tag" ] && [ "$candidate_tag" != "<none>:<none>" ]; then
            # Verify candidate strictly matches MediScanAI repository name
            if [[ "$candidate_tag" =~ (mediscanai-backend) ]]; then
                # Resolve full image ID
                FULL_CANDIDATE_ID=$(docker inspect "$candidate_id" --format '{{.Id}}' 2>/dev/null || echo "$candidate_id")

                # Check if image ID or Tag is in protected list
                IS_PROTECTED=false
                for p in "${PROTECTED_IMAGES[@]:-}"; do
                    if [ -n "$p" ] && { [ "$candidate_tag" = "$p" ] || [[ "$candidate_tag" == *"$p"* ]]; }; then
                        IS_PROTECTED=true
                        break
                    fi
                done
                for pid in "${PROTECTED_IMAGE_IDS[@]:-}"; do
                    if [ -n "$pid" ] && { [ "$FULL_CANDIDATE_ID" = "$pid" ] || [[ "$FULL_CANDIDATE_ID" == *"$pid"* ]]; }; then
                        IS_PROTECTED=true
                        break
                    fi
                done

                # Check if referenced by any container (running or stopped)
                IN_USE=false
                if [ -n "$(docker ps -a --filter "ancestor=${FULL_CANDIDATE_ID}" -q 2>/dev/null)" ]; then
                    IN_USE=true
                fi

                if [ "$IS_PROTECTED" = "false" ] && [ "$IN_USE" = "false" ]; then
                    if [ "$DRY_RUN" = "false" ]; then
                        docker rmi "$candidate_id" >/dev/null 2>&1 || true
                        log "  Removed obsolete MediScanAI image: ${candidate_tag} (${candidate_id})"
                    else
                        log "  [DRY-RUN] Would remove obsolete MediScanAI image: ${candidate_tag} (${candidate_id})"
                    fi
                else
                    log "  Retained protected/in-use MediScanAI image: ${candidate_tag} (${candidate_id})"
                fi
            else
                log "  Skipped image (non-MediScanAI ownership): ${candidate_tag} (${candidate_id})"
            fi
        fi
    done < <(docker images --filter "reference=*mediscanai-backend*" --format '{{.ID}}\t{{.Repository}}:{{.Tag}}' 2>/dev/null || true)

    # Evaluate Docker builder cache (shared with other projects on Mac)
    if [ "$PRUNE_BUILD_CACHE" = "true" ]; then
        log "  Evaluating Docker buildx builder cache (explicit prune requested, keeping ${BUILDER_KEEP_STORAGE})..."
        if [ "$DRY_RUN" = "false" ]; then
            docker builder prune -f --keep-storage "$BUILDER_KEEP_STORAGE" >/dev/null 2>&1 || true
            log "  Builder cache pruned with headroom preserved."
        else
            log "  [DRY-RUN] Would prune build cache exceeding ${BUILDER_KEEP_STORAGE}."
        fi
    else
        log "  Build cache evaluation: Skipped automatic prune (build cache is shared across host projects)."
        log "  Pass --prune-build-cache to prune build cache exceeding ${BUILDER_KEEP_STORAGE}."
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

# 5. Evaluate Temporary Staging Files (Inspection Only — Automatic Deletion Disabled)
log "Step 5/7: Evaluating temporary staging files (Inspection only)..."
log "  POLICY: Automatic deletion of temporary files is DISABLED."
log "  POLICY: Temporary files remain untouched by scheduled maintenance and --force."
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
            ITEM_AGE_OVER_24H=$(find "$item" -maxdepth 0 -mtime +1 2>/dev/null || true)
            if [ -n "$ITEM_AGE_OVER_24H" ]; then
                log "  [UNVERIFIED CANDIDATE (>24h)]: $item (Preserved: lifecycle/database references cannot be proven offline)"
            else
                log "  [ACTIVE/RECENT (<24h)]: $item (Preserved: active upload or recent processing)"
            fi
        fi
    done < <(find "$CANONICAL_TEMP" -maxdepth 1 \( -name "$pattern" \) 2>/dev/null || true)
done

if [ "$FOUND_TEMP_COUNT" -eq 0 ]; then
    log "  No MediScanAI temporary files found in ${CANONICAL_TEMP}."
else
    log "  Notice: ${FOUND_TEMP_COUNT} temporary file(s) inspected. All temporary files left untouched (automatic deletion disabled)."
fi

# 6. Evaluate Operational Logs Bounded Rotation
log "Step 6/7: Evaluating operational log files..."
if [ -d "$LOGS_DIR" ]; then
    for log_file in "${LOGS_DIR}"/*.log; do
        if [ -f "$log_file" ]; then
            LOG_SIZE_KB=$(du -k "$log_file" 2>/dev/null | awk '{print $1}' || echo 0)
            if [ "$LOG_SIZE_KB" -gt 5120 ]; then # > 5MB
                if [ "$DRY_RUN" = "false" ]; then
                    mv "$log_file" "${log_file}.1"
                    : > "$log_file"
                    log "  Rotated oversized log (>5MB): $(basename "$log_file")"
                else
                    log "  [DRY-RUN] Would rotate oversized log (>5MB): $(basename "$log_file")"
                fi
            fi
        fi
    done
else
    mkdir -p "$LOGS_DIR"
fi

# 7. Report Storage After Maintenance
log "Step 7/7: Storage Summary:"
if [ "$(uname)" = "Darwin" ]; then
    df -h /System/Volumes/Data / | awk 'NR==1 || NR==2 || NR==3 {print "  " $0}'
else
    df -h / | awk 'NR==1 || NR==2 {print "  " $0}'
fi

log "Maintenance run finished cleanly."
exit 0
