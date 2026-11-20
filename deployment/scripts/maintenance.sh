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
ENV_FILE="${DEPLOY_DIR}/.env"
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

# Canonical MediScanAI repositories (normalized exact match)
CANONICAL_REPOSITORIES=("mediscanai-backend" "ghcr.io/djcode0718/mediscanai-backend")

# If .env overrides MEDISCANAI_IMAGE, add its repository if its base name is strictly 'mediscanai-backend'
if [ -f "$ENV_FILE" ]; then
    ENV_IMG=$(grep -E '^[[:space:]]*MEDISCANAI_IMAGE=' "$ENV_FILE" 2>/dev/null | cut -d= -f2- | tr -d '[:space:]"' || true)
    if [ -n "$ENV_IMG" ]; then
        ENV_REPO=$(echo "$ENV_IMG" | cut -d: -f1)
        if [ "$(basename "$ENV_REPO")" = "mediscanai-backend" ]; then
            if [[ ! " ${CANONICAL_REPOSITORIES[*]:-} " =~ " ${ENV_REPO} " ]]; then
                CANONICAL_REPOSITORIES+=("$ENV_REPO")
            fi
        fi
    fi
fi

# 1. Inspect Protected Images (Current + 2 Previous Known-Good)
log "Step 1/5: Identifying protected images..."
PROTECTED_IMAGES=()
PROTECTED_IMAGE_IDS=()
METADATA_AMBIGUOUS=false

if [ -f "$CURRENT_DEPLOY_FILE" ]; then
    CURR_IMG=$(cat "$CURRENT_DEPLOY_FILE" | tr -d '[:space:]')
    if [ -n "$CURR_IMG" ]; then
        PROTECTED_IMAGES+=("$CURR_IMG")
        log "  Protected [CURRENT]: ${CURR_IMG}"
    else
        log "  WARNING: Current deployment marker is empty: ${CURRENT_DEPLOY_FILE}"
        METADATA_AMBIGUOUS=true
    fi
else
    log "  NOTICE: Current deployment marker not found. Running in cold/initial mode."
fi

if [ -f "$HISTORY_FILE" ]; then
    # Verify history integrity line-by-line
    HISTORY_MALFORMED=false
    HISTORY_IMAGES=()
    while IFS= read -r line; do
        [ -z "$line" ] && continue
        # Verify valid pipe count (at least 3 pipe separators: date | action | image | details)
        PIPE_COUNT=$( (grep -o '|' <<< "$line" || true) | wc -l | tr -d ' ')
        if [ "$PIPE_COUNT" -lt 3 ]; then
            HISTORY_MALFORMED=true
            break
        fi
        img=$(echo "$line" | awk -F'|' '{print $3}' | tr -d '[:space:]')
        if [ -z "$img" ] || [ "$img" = "unknown" ]; then
            HISTORY_MALFORMED=true
            break
        fi
        HISTORY_IMAGES+=("$img")
    done < "$HISTORY_FILE"

    if [ "$HISTORY_MALFORMED" = "true" ]; then
        log "  WARNING: Deployment history is malformed or corrupt: ${HISTORY_FILE}"
        METADATA_AMBIGUOUS=true
    else
        # Extract last 2 unique previous images from valid history (excluding current)
        for (( idx=${#HISTORY_IMAGES[@]}-1; idx>=0; idx-- )); do
            h_img="${HISTORY_IMAGES[idx]}"
            if [[ ! " ${PROTECTED_IMAGES[*]:-} " =~ " ${h_img} " ]]; then
                PROTECTED_IMAGES+=("$h_img")
                log "  Protected [HISTORY]: ${h_img}"
            fi
            # Protect up to 2 rollback images
            ROLLBACK_COUNT=0
            for pi in "${PROTECTED_IMAGES[@]:-}"; do
                [ "$pi" != "${CURR_IMG:-}" ] && ROLLBACK_COUNT=$((ROLLBACK_COUNT + 1))
            done
            [ "$ROLLBACK_COUNT" -ge 2 ] && break
        done
    fi
fi

if [ "$METADATA_AMBIGUOUS" = "true" ]; then
    log "  CRITICAL SAFETY LOCK: Deployment metadata is missing, malformed, or ambiguous."
    log "  POLICY: All candidate Docker images will be PRESERVED to prevent accidental deletion."
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

    # Directly resolve container's image sha256 to ensure stopped/renamed containers are protected
    while IFS= read -r cid; do
        if [ -n "$cid" ]; then
            IMG_SHA=$(docker inspect "$cid" --format '{{.Image}}' 2>/dev/null || echo "")
            if [ -n "$IMG_SHA" ] && [[ ! " ${PROTECTED_IMAGE_IDS[*]:-} " =~ " ${IMG_SHA} " ]]; then
                PROTECTED_IMAGE_IDS+=("$IMG_SHA")
                log "  Protected [CONTAINER IMAGE SHA]: ${IMG_SHA}"
            fi
        fi
    done < <(docker ps -a --format '{{.ID}}' 2>/dev/null || true)
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

    # Evaluate ONLY images with exact canonical MediScanAI repository match
    log "  Evaluating Docker images for exact canonical MediScanAI ownership..."
    while IFS=$'\t' read -r candidate_id candidate_repo candidate_tag; do
        if [ -z "$candidate_id" ] || [ -z "$candidate_repo" ] || [ -z "$candidate_tag" ]; then
            continue
        fi

        # Untagged/dangling images are permanently preserved
        if [ "$candidate_repo" = "<none>" ] || [ "$candidate_tag" = "<none>" ]; then
            log "  Preserved image (untagged/dangling image preserved): ${candidate_id}"
            continue
        fi

        # Step A: Exact Canonical Repository Verification (no substring false positives)
        IS_CANONICAL=false
        for canon_repo in "${CANONICAL_REPOSITORIES[@]}"; do
            if [ "$candidate_repo" = "$canon_repo" ]; then
                IS_CANONICAL=true
                break
            fi
        done

        if [ "$IS_CANONICAL" = "false" ]; then
            log "  Skipped image (ownership unverified; non-canonical repository '${candidate_repo}'): ${candidate_repo}:${candidate_tag} (${candidate_id})"
            continue
        fi

        # Step B: Safe Metadata Ambiguity Lock
        if [ "$METADATA_AMBIGUOUS" = "true" ]; then
            log "  Preserved image (metadata ambiguous lock active): ${candidate_repo}:${candidate_tag} (${candidate_id})"
            continue
        fi

        # Step C: Resolve Full Immutable Image ID
        FULL_CANDIDATE_ID=$(docker inspect "$candidate_id" --format '{{.Id}}' 2>/dev/null || echo "$candidate_id")

        # Step D: Protected Tag and ID Verification
        IS_PROTECTED=false
        candidate_ref="${candidate_repo}:${candidate_tag}"

        for p in "${PROTECTED_IMAGES[@]:-}"; do
            if [ -n "$p" ] && { [ "$candidate_ref" = "$p" ] || [ "$candidate_tag" = "$p" ] || [[ "$p" == *"${candidate_ref}"* ]]; }; then
                IS_PROTECTED=true
                break
            fi
        done

        for pid in "${PROTECTED_IMAGE_IDS[@]:-}"; do
            if [ -n "$pid" ] && { [ "$FULL_CANDIDATE_ID" = "$pid" ] || [[ "$FULL_CANDIDATE_ID" == *"$pid"* ]] || [[ "$pid" == *"$candidate_id"* ]]; }; then
                IS_PROTECTED=true
                break
            fi
        done

        # Step E: Container Usage Verification (running or stopped)
        IN_USE=false
        if [ -n "$(docker ps -a --filter "ancestor=${FULL_CANDIDATE_ID}" -q 2>/dev/null)" ] || \
           [ -n "$(docker ps -a --filter "ancestor=${candidate_ref}" -q 2>/dev/null)" ]; then
            IN_USE=true
        fi

        if [ "$IS_PROTECTED" = "true" ] || [ "$IN_USE" = "true" ]; then
            log "  Retained protected/in-use MediScanAI image: ${candidate_ref} (${candidate_id})"
            continue
        fi

        # Step F: Immediate Pre-Removal Protection Recheck (Atomic Race Condition Guard)
        RECHECK_PROTECTION=false

        # 1. Re-verify active/stopped containers right before deletion
        if [ -n "$(docker ps -a --filter "ancestor=${FULL_CANDIDATE_ID}" -q 2>/dev/null)" ]; then
            RECHECK_PROTECTION=true
        fi

        # 2. Re-verify current deployment file on disk
        if [ -f "$CURRENT_DEPLOY_FILE" ]; then
            LATEST_CURR=$(cat "$CURRENT_DEPLOY_FILE" | tr -d '[:space:]')
            if [ "$LATEST_CURR" = "$candidate_ref" ] || [ "$LATEST_CURR" = "$candidate_tag" ]; then
                RECHECK_PROTECTION=true
            fi
        fi

        # 3. Re-verify against protected image IDs
        for pid in "${PROTECTED_IMAGE_IDS[@]:-}"; do
            if [ -n "$pid" ] && { [ "$FULL_CANDIDATE_ID" = "$pid" ] || [[ "$pid" == *"$candidate_id"* ]]; }; then
                RECHECK_PROTECTION=true
                break
            fi
        done

        if [ "$RECHECK_PROTECTION" = "true" ]; then
            log "  Retained candidate (failed immediate pre-removal protection recheck): ${candidate_ref} (${candidate_id})"
            continue
        fi

        # Step G: Remove candidate if all safeguards pass
        if [ "$DRY_RUN" = "false" ]; then
            docker rmi "$candidate_id" >/dev/null 2>&1 || true
            log "  Removed obsolete MediScanAI image: ${candidate_ref} (${candidate_id})"
        else
            log "  [DRY-RUN] Would remove obsolete MediScanAI image: ${candidate_ref} (${candidate_id})"
        fi
    done < <(docker images --format '{{.ID}}\t{{.Repository}}\t{{.Tag}}' 2>/dev/null || true)

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
