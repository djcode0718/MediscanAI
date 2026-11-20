#!/usr/bin/env bash
# ==============================================================================
# MediScanAI Production Health Check Script
# Probes backend liveness (/api/health) and readiness (/api/ready)
# Safe logging: Never displays secrets, credentials, or internal query parameters.
# ==============================================================================

set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-10}"
MAX_RETRIES="${MAX_RETRIES:-5}"
RETRY_DELAY="${RETRY_DELAY:-3}"
QUIET="${QUIET:-false}"

log() {
    if [ "$QUIET" != "true" ]; then
        echo "[HEALTH-CHECK] $*"
    fi
}

log_err() {
    echo "[HEALTH-CHECK ERROR] $*" >&2
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --url)
            BASE_URL="$2"
            shift 2
            ;;
        --timeout)
            TIMEOUT_SECONDS="$2"
            shift 2
            ;;
        --retries)
            MAX_RETRIES="$2"
            shift 2
            ;;
        --delay)
            RETRY_DELAY="$2"
            shift 2
            ;;
        --quiet)
            QUIET="true"
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [--url <base_url>] [--timeout <sec>] [--retries <count>] [--delay <sec>] [--quiet]"
            exit 0
            ;;
        *)
            log_err "Unknown argument: $1"
            exit 1
            ;;
    esac
done

# Strip trailing slash from BASE_URL
BASE_URL="${BASE_URL%/}"

HEALTH_ENDPOINT="${BASE_URL}/api/health"
READY_ENDPOINT="${BASE_URL}/api/ready"

log "Targeting base URL: ${BASE_URL}"
log "Checking liveness: ${HEALTH_ENDPOINT}"
log "Checking readiness: ${READY_ENDPOINT}"

# 1. Probe Liveness (/api/health)
log "Step 1/2: Verifying application liveness..."
LIVENESS_PASSED=false

for attempt in $(seq 1 "$MAX_RETRIES"); do
    HTTP_CODE=$(curl -s -o /tmp/mediscanai_health.json -w "%{http_code}" --max-time "$TIMEOUT_SECONDS" "$HEALTH_ENDPOINT" 2>/dev/null || echo "000")
    if [ "$HTTP_CODE" = "200" ]; then
        STATUS_VAL=$(grep -o '"status"[[:space:]]*:[[:space:]]*"[^"]*"' /tmp/mediscanai_health.json 2>/dev/null | cut -d'"' -f4 || echo "")
        if [ "$STATUS_VAL" = "alive" ]; then
            log "Liveness check passed on attempt ${attempt}/${MAX_RETRIES} (HTTP 200, status: alive)."
            LIVENESS_PASSED=true
            break
        fi
    fi
    log "Liveness probe attempt ${attempt}/${MAX_RETRIES} returned HTTP ${HTTP_CODE}. Retrying in ${RETRY_DELAY}s..."
    sleep "$RETRY_DELAY"
done

rm -f /tmp/mediscanai_health.json 2>/dev/null || true

if [ "$LIVENESS_PASSED" != "true" ]; then
    log_err "Liveness check failed after ${MAX_RETRIES} attempts against ${HEALTH_ENDPOINT}."
    exit 1
fi

# 2. Probe Readiness (/api/ready)
log "Step 2/2: Verifying application readiness (database, models, pipeline)..."
READINESS_PASSED=false

for attempt in $(seq 1 "$MAX_RETRIES"); do
    HTTP_CODE=$(curl -s -o /tmp/mediscanai_ready.json -w "%{http_code}" --max-time "$TIMEOUT_SECONDS" "$READY_ENDPOINT" 2>/dev/null || echo "000")
    if [ "$HTTP_CODE" = "200" ]; then
        STATUS_VAL=$(grep -o '"status"[[:space:]]*:[[:space:]]*"[^"]*"' /tmp/mediscanai_ready.json 2>/dev/null | cut -d'"' -f4 || echo "")
        if [ "$STATUS_VAL" = "ready" ]; then
            log "Readiness check passed on attempt ${attempt}/${MAX_RETRIES} (HTTP 200, status: ready)."
            READINESS_PASSED=true
            break
        fi
    fi
    log "Readiness probe attempt ${attempt}/${MAX_RETRIES} returned HTTP ${HTTP_CODE}. Retrying in ${RETRY_DELAY}s..."
    sleep "$RETRY_DELAY"
done

if [ "$READINESS_PASSED" != "true" ]; then
    if [ -f /tmp/mediscanai_ready.json ]; then
        log_err "Readiness check payload details:"
        cat /tmp/mediscanai_ready.json >&2
        echo "" >&2
    fi
    rm -f /tmp/mediscanai_ready.json 2>/dev/null || true
    log_err "Readiness check failed after ${MAX_RETRIES} attempts against ${READY_ENDPOINT}."
    exit 1
fi

rm -f /tmp/mediscanai_ready.json 2>/dev/null || true

log "All health and readiness checks PASSED successfully."
exit 0
