#!/usr/bin/env bash

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
TEAL='\033[0;36m'
NC='\033[0m' # No Color

clear

echo -e "${TEAL}🏥 ============================================${NC}"
echo -e "${TEAL}🏥          MediScanAI Unified Test Runner      ${NC}"
echo -e "${TEAL}🏥 ============================================${NC}"
echo ""

CONDA_ENV="med-env"
RUN_CMD=""

if command -v conda &> /dev/null; then
  if conda env list | grep -q "$CONDA_ENV"; then
    RUN_CMD="conda run --no-capture-output -n $CONDA_ENV"
  fi
fi

if [ -z "$RUN_CMD" ]; then
  echo -e "${RED}[✘] Conda environment '$CONDA_ENV' not found.${NC}"
  echo "    Please make sure conda is installed and the environment exists."
  exit 1
fi

MODE="${1:-fast}"

if [ "$MODE" == "--all" ] || [ "$MODE" == "all" ]; then
  echo -e "${YELLOW}🔄 Running ALL test suites (including real AI/RAG models)...${NC}"
  $RUN_CMD pytest -v
  EXIT_CODE=$?
elif [ "$MODE" == "--integration" ] || [ "$MODE" == "integration" ]; then
  echo -e "${YELLOW}🔄 Running real AI/ML integration test suite...${NC}"
  $RUN_CMD pytest tests/integration -v -m integration
  EXIT_CODE=$?
else
  echo -e "${YELLOW}🔄 Running fast deterministic test suite (Unit, API, Database, E2E Smoke)...${NC}"
  $RUN_CMD pytest tests/unit tests/api tests/database tests/test_e2e_smoke.py -v
  EXIT_CODE=$?
fi

echo "=================================================="
if [ $EXIT_CODE -eq 0 ]; then
  echo -e "${GREEN}✅ Test suite passed successfully!${NC}"
  exit 0
else
  echo -e "${RED}❌ Test suite reported failures.${NC}"
  exit $EXIT_CODE
fi
