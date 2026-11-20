#!/bin/bash
# ==============================================================================
# MediScanAI Production Deployment Preflight Validation
# Validates host environment, secrets, file permissions, and data mounts
# DOES NOT print or leak sensitive secret values in console output
# ==============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

ERRORS=0
WARNINGS=0

echo -e "${BLUE}================================================================${NC}"
echo -e "${BLUE}        MediScanAI Production Preflight Validation Gating        ${NC}"
echo -e "${BLUE}================================================================${NC}"

# 1. Check deployment/.env existence
ENV_FILE="${1:-.env}"
if [ ! -f "$ENV_FILE" ] && [ -f "deployment/.env" ]; then
    ENV_FILE="deployment/.env"
fi

if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}[FAIL] Configuration file '$ENV_FILE' not found.${NC}"
    echo -e "       Create it from deployment/.env.example before starting Compose."
    exit 1
fi
echo -e "${GREEN}[PASS] Configuration file found: ${ENV_FILE}${NC}"

# 2. Check file permissions on .env (should be 600 or 400)
if [ "$(uname)" = "Darwin" ]; then
    PERMS=$(stat -f "%Lp" "$ENV_FILE" 2>/dev/null || echo "")
else
    PERMS=$(stat -c "%a" "$ENV_FILE" 2>/dev/null || echo "")
fi

if [ "$PERMS" != "600" ] && [ "$PERMS" != "400" ]; then
    echo -e "${YELLOW}[WARN] Insecure file permissions on ${ENV_FILE}: ${PERMS}. Recommended: 600 (chmod 600 ${ENV_FILE})${NC}"
    WARNINGS=$((WARNINGS + 1))
else
    echo -e "${GREEN}[PASS] Restrictive permissions verified on ${ENV_FILE} (${PERMS})${NC}"
fi

# Load variables safely from env file without evaluating untrusted shell code
load_env_val() {
    grep -E "^[[:space:]]*$1=" "$ENV_FILE" | head -n 1 | cut -d '=' -f2- | tr -d '\r"' | tr -d "'"
}

# 3. Validate POSTGRES_PASSWORD
PG_PASS=$(load_env_val "POSTGRES_PASSWORD")
if [ -z "$PG_PASS" ]; then
    echo -e "${RED}[FAIL] POSTGRES_PASSWORD is not set in ${ENV_FILE}.${NC}"
    ERRORS=$((ERRORS + 1))
elif [ "$PG_PASS" = "CHANGE_THIS_TO_A_SECURE_RANDOM_PASSWORD_32_CHARS" ] || [ "$PG_PASS" = "postgres_secure_pass" ] || [ "$PG_PASS" = "postgres" ]; then
    echo -e "${RED}[FAIL] POSTGRES_PASSWORD is set to an insecure default/placeholder.${NC}"
    ERRORS=$((ERRORS + 1))
elif [ ${#PG_PASS} -lt 16 ]; then
    echo -e "${YELLOW}[WARN] POSTGRES_PASSWORD is shorter than 16 characters (${#PG_PASS} chars).${NC}"
    WARNINGS=$((WARNINGS + 1))
else
    echo -e "${GREEN}[PASS] POSTGRES_PASSWORD is configured with strong length (${#PG_PASS} chars).${NC}"
fi

# 4. Validate JWT_SECRET_KEY
JWT_SEC=$(load_env_val "JWT_SECRET_KEY")
if [ -z "$JWT_SEC" ]; then
    echo -e "${RED}[FAIL] JWT_SECRET_KEY is not set in ${ENV_FILE}.${NC}"
    ERRORS=$((ERRORS + 1))
elif [ "$JWT_SEC" = "CHANGE_THIS_TO_A_SECURE_RANDOM_SECRET_KEY_64_CHARS" ] || [ "$JWT_SEC" = "secret" ]; then
    echo -e "${RED}[FAIL] JWT_SECRET_KEY is set to a placeholder.${NC}"
    ERRORS=$((ERRORS + 1))
elif [ ${#JWT_SEC} -lt 32 ]; then
    echo -e "${YELLOW}[WARN] JWT_SECRET_KEY is shorter than 32 characters (${#JWT_SEC} chars).${NC}"
    WARNINGS=$((WARNINGS + 1))
else
    echo -e "${GREEN}[PASS] JWT_SECRET_KEY is configured with strong length (${#JWT_SEC} chars).${NC}"
fi

# 5. Validate LLM_MODE and API Credentials
LLM_MODE=$(load_env_val "LLM_MODE")
LLM_MODE=${LLM_MODE:-online}

if [ "$LLM_MODE" = "online" ]; then
    GEMINI_KEY=$(load_env_val "GEMINI_API_KEY")
    GROQ_KEY=$(load_env_val "GROQ_API_KEY")

    VALID_ONLINE_KEYS=0

    if [ -n "$GEMINI_KEY" ] && [ "$GEMINI_KEY" != "YOUR_GEMINI_API_KEY_HERE" ] && [ "$GEMINI_KEY" != "YOUR_GEMINI_API_KEY" ]; then
        VALID_ONLINE_KEYS=$((VALID_ONLINE_KEYS + 1))
        echo -e "${GREEN}[PASS] Google Gemini API Key configured.${NC}"
    fi

    if [ -n "$GROQ_KEY" ] && [ "$GROQ_KEY" != "YOUR_GROQ_API_KEY_HERE" ] && [ "$GROQ_KEY" != "YOUR_GROQ_API_KEY" ]; then
        VALID_ONLINE_KEYS=$((VALID_ONLINE_KEYS + 1))
        echo -e "${GREEN}[PASS] Groq Cloud API Key configured.${NC}"
    fi

    if [ $VALID_ONLINE_KEYS -eq 0 ]; then
        echo -e "${RED}[FAIL] LLM_MODE='online' requires at least one active API key (GEMINI_API_KEY or GROQ_API_KEY).${NC}"
        ERRORS=$((ERRORS + 1))
    fi
elif [ "$LLM_MODE" = "offline" ]; then
    echo -e "${YELLOW}[WARN] LLM_MODE='offline' requires local Ollama instance (high RAM/CPU consumption).${NC}"
else
    echo -e "${RED}[FAIL] Unknown LLM_MODE='${LLM_MODE}'. Expected 'online' or 'offline'.${NC}"
    ERRORS=$((ERRORS + 1))
fi

# 6. Validate CORS_ORIGINS in production
APP_ENV=$(load_env_val "APP_ENV")
APP_ENV=${APP_ENV:-production}
CORS_ORIG=$(load_env_val "CORS_ORIGINS")

if [ "$APP_ENV" = "production" ]; then
    if [[ "$CORS_ORIG" == *"*"* ]]; then
        echo -e "${RED}[FAIL] CORS_ORIGINS contains wildcard '*' while APP_ENV=production.${NC}"
        ERRORS=$((ERRORS + 1))
    else
        echo -e "${GREEN}[PASS] Production CORS configuration validated (no wildcard).${NC}"
    fi
fi

# 7. Validate Data and Index Mount Assets on Host
DATA_DIR="../data"
INDEX_DIR="../indexes"
if [ ! -d "$DATA_DIR" ] && [ -d "data" ]; then
    DATA_DIR="data"
    INDEX_DIR="indexes"
fi

if [ -d "$DATA_DIR" ] && [ -n "$(ls -A "$DATA_DIR" 2>/dev/null)" ]; then
    echo -e "${GREEN}[PASS] Static dataset directory verified (${DATA_DIR}).${NC}"
else
    echo -e "${YELLOW}[WARN] Static dataset directory '${DATA_DIR}' is empty or missing. Ensure data/ is synced.${NC}"
    WARNINGS=$((WARNINGS + 1))
fi

if [ -d "$INDEX_DIR" ] && [ -n "$(ls -A "$INDEX_DIR" 2>/dev/null)" ]; then
    echo -e "${GREEN}[PASS] Precomputed FAISS indices verified (${INDEX_DIR}).${NC}"
else
    echo -e "${YELLOW}[WARN] FAISS indices directory '${INDEX_DIR}' is empty or missing. Ensure indexes/ is synced.${NC}"
    WARNINGS=$((WARNINGS + 1))
fi

# 8. Check Docker and Docker Compose availability
if command -v docker >/dev/null 2>&1; then
    DOCKER_VER=$(docker --version 2>/dev/null || echo "docker available")
    echo -e "${GREEN}[PASS] ${DOCKER_VER}${NC}"

    if docker compose version >/dev/null 2>&1; then
        COMPOSE_VER=$(docker compose version 2>/dev/null || echo "Docker Compose v2 available")
        echo -e "${GREEN}[PASS] ${COMPOSE_VER}${NC}"
    else
        echo -e "${RED}[FAIL] Docker Compose v2 is unavailable ('docker compose version' failed).${NC}"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo -e "${RED}[FAIL] docker CLI not found.${NC}"
    ERRORS=$((ERRORS + 1))
fi

echo -e "${BLUE}----------------------------------------------------------------${NC}"
if [ $ERRORS -gt 0 ]; then
    echo -e "${RED}Preflight validation FAILED with ${ERRORS} error(s) and ${WARNINGS} warning(s).${NC}"
    echo -e "${RED}Resolve required configuration errors before starting the stack.${NC}"
    exit 1
else
    echo -e "${GREEN}Preflight validation PASSED successfully with ${WARNINGS} warning(s).${NC}"
    exit 0
fi
