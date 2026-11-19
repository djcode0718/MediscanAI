#!/usr/bin/env bash
# ==============================================================================
# MediScanAI Production Operations Status Dashboard
# Displays running container health, SSD disk thresholds, current image tag,
# Docker storage utilization, and database backup state.
# Safe: Never reveals secrets, passwords, or authentication keys.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

COMPOSE_FILE="${DEPLOY_DIR}/compose.yaml"
CURRENT_DEPLOY_FILE="${DEPLOY_DIR}/.current_deployment"
HISTORY_FILE="${DEPLOY_DIR}/.deployment_history"
BACKUP_DIR="${DEPLOY_DIR}/backups"

BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================================================${NC}"
echo -e "${BLUE}          MediScanAI Production Operations Status               ${NC}"
echo -e "${BLUE}  Host: $(hostname) | Date: $(date +'%Y-%m-%d %H:%M:%S')  ${NC}"
echo -e "${BLUE}================================================================${NC}"

# 1. Host Storage & SSD Capacity
echo -e "\n${BLUE}[1/6] Host SSD Storage Utilization (MacBook Air M4):${NC}"
if [ "$(uname)" = "Darwin" ]; then
    TARGET_VOL="/System/Volumes/Data"
    if [ ! -d "$TARGET_VOL" ]; then
        TARGET_VOL="$DEPLOY_DIR"
    fi
    TOTAL_SIZE=$(df -h "$TARGET_VOL" | awk 'NR==2 {print $2}')
    USED_SIZE=$(df -h "$TARGET_VOL" | awk 'NR==2 {print $3}')
    AVAIL_SIZE=$(df -h "$TARGET_VOL" | awk 'NR==2 {print $4}')
    TOTAL_KB=$(df -k "$TARGET_VOL" | awk 'NR==2 {print $2}')
    AVAIL_KB=$(df -k "$TARGET_VOL" | awk 'NR==2 {print $4}')
    USED_PCT=$(( (TOTAL_KB - AVAIL_KB) * 100 / TOTAL_KB ))
    VOL_LABEL="APFS Container (${TARGET_VOL})"
else
    TOTAL_SIZE=$(df -h / | awk 'NR==2 {print $2}')
    USED_SIZE=$(df -h / | awk 'NR==2 {print $3}')
    AVAIL_SIZE=$(df -h / | awk 'NR==2 {print $4}')
    TOTAL_KB=$(df -k / | awk 'NR==2 {print $2}')
    AVAIL_KB=$(df -k / | awk 'NR==2 {print $4}')
    USED_PCT=$(( (TOTAL_KB - AVAIL_KB) * 100 / TOTAL_KB ))
    VOL_LABEL="Root Filesystem (/)"
fi

echo "  ${VOL_LABEL}: ${USED_SIZE} used / ${TOTAL_SIZE} total (${AVAIL_SIZE} available, ${USED_PCT}% capacity)"

if [ "$USED_PCT" -ge 90 ]; then
    echo -e "  Threshold Status: ${RED}CRITICAL (${USED_PCT}% used >= 90% limit). Deployments blocked.${NC}"
elif [ "$USED_PCT" -ge 80 ]; then
    echo -e "  Threshold Status: ${YELLOW}HIGH WARNING (${USED_PCT}% used >= 80%). Cleanup recommended.${NC}"
elif [ "$USED_PCT" -ge 70 ]; then
    echo -e "  Threshold Status: ${YELLOW}WARNING (${USED_PCT}% used >= 70%).${NC}"
else
    echo -e "  Threshold Status: ${GREEN}NORMAL (${USED_PCT}% used < 70%). Headroom healthy.${NC}"
fi

# 2. Docker Daemon & Engine Status
echo -e "\n${BLUE}[2/6] Docker Daemon State:${NC}"
if docker info >/dev/null 2>&1; then
    DOCKER_VER=$(docker version --format '{{.Server.Version}}' 2>/dev/null || echo "Active")
    echo -e "  Docker Engine: ${GREEN}ONLINE (v${DOCKER_VER})${NC}"
    DOCKER_AVAILABLE=true
else
    echo -e "  Docker Engine: ${RED}OFFLINE (Socket unreachable)${NC}"
    DOCKER_AVAILABLE=false
fi

# 3. Production Containers Status
echo -e "\n${BLUE}[3/6] Container Services:${NC}"
if [ "$DOCKER_AVAILABLE" = "true" ]; then
    docker compose -f "$COMPOSE_FILE" ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || docker ps --filter "name=mediscanai" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
else
    echo "  Containers cannot be inspected because Docker daemon is offline."
fi

# 4. Backend Application Health & Readiness
echo -e "\n${BLUE}[4/6] API Health & Readiness Probes:${NC}"
if curl -s -f http://localhost:8000/api/health >/dev/null 2>&1; then
    HEALTH_RESP=$(curl -s http://localhost:8000/api/health 2>/dev/null || echo "{}")
    echo -e "  Liveness  (/api/health): ${GREEN}PASSED (HTTP 200)${NC}"
else
    echo -e "  Liveness  (/api/health): ${RED}UNAVAILABLE (Connection refused / timeout)${NC}"
fi

if curl -s -f http://localhost:8000/api/ready >/dev/null 2>&1; then
    READY_RESP=$(curl -s http://localhost:8000/api/ready 2>/dev/null || echo "{}")
    echo -e "  Readiness (/api/ready):  ${GREEN}READY (HTTP 200)${NC}"
else
    echo -e "  Readiness (/api/ready):  ${YELLOW}NOT READY / OFFLINE${NC}"
fi

# 5. Deployed Image Reference & History
echo -e "\n${BLUE}[5/6] Deployed Image & Recent Deployments:${NC}"
if [ -f "$CURRENT_DEPLOY_FILE" ]; then
    CURRENT_IMG=$(cat "$CURRENT_DEPLOY_FILE" | tr -d '[:space:]')
    echo "  Active Image Tag: ${CURRENT_IMG}"
else
    echo "  Active Image Tag: None recorded (first deployment pending)"
fi

if [ -f "$HISTORY_FILE" ]; then
    echo "  Recent History (last 3 events):"
    tail -n 3 "$HISTORY_FILE" | while IFS= read -r line; do
        echo "    $line"
    done
fi

# 6. Database Backups & Model Cache Storage
echo -e "\n${BLUE}[6/6] PostgreSQL Backups & Storage Volumes:${NC}"
if [ -d "$BACKUP_DIR" ]; then
    BACKUP_COUNT=$(find "$BACKUP_DIR" -type f -name "mediscanai_postgres_*.dump.gz" 2>/dev/null | wc -l | tr -d ' ')
    if [ "$BACKUP_COUNT" -gt 0 ]; then
        LATEST_BACKUP=$(ls -t "${BACKUP_DIR}"/mediscanai_postgres_*.dump.gz 2>/dev/null | head -n 1 || echo "")
        LATEST_SIZE=$(du -h "$LATEST_BACKUP" 2>/dev/null | cut -f1 || echo "unknown")
        echo -e "  Backups: ${GREEN}${BACKUP_COUNT} archive(s) present.${NC}"
        echo "  Latest Backup: $(basename "$LATEST_BACKUP") (${LATEST_SIZE})"
    else
        echo -e "  Backups: ${YELLOW}No backup archives found in ${BACKUP_DIR}.${NC}"
    fi
else
    echo "  Backup directory does not exist yet."
fi

if [ "$DOCKER_AVAILABLE" = "true" ]; then
    echo -e "\n  Docker Disk Usage (docker system df):"
    docker system df 2>/dev/null || true
fi

echo -e "\n${BLUE}================================================================${NC}"
exit 0
