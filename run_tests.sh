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

TESTS=(
  "tests/test_utils.py"
  "tests/test_embeddings.py"
  "tests/test_retriever.py"
  "tests/test_ocr.py"
  "tests/test_whisper.py"
  "tests/test_llm.py"
  "tests/test_pipeline.py"
)

PASSED=0
FAILED=0
FAILED_LIST=()

for test_file in "${TESTS[@]}"; do
  echo -e "${YELLOW}🔄 Running: $test_file...${NC}"
  echo "--------------------------------------------------"
  
  $RUN_CMD python "$test_file"
  
  if [ $? -eq 0 ]; then
    echo -e "${GREEN}✔ $test_file PASSED${NC}"
    echo ""
    PASSED=$((PASSED + 1))
  else
    echo -e "${RED}✘ $test_file FAILED${NC}"
    echo ""
    FAILED=$((FAILED + 1))
    FAILED_LIST+=("$test_file")
  fi
done

echo "=================================================="
echo -e "${TEAL}📊 Test Summary:${NC}"
echo -e "   - ${GREEN}Passed:${NC} $PASSED"
echo -e "   - ${RED}Failed:${NC} $FAILED"

if [ $FAILED -gt 0 ]; then
  echo ""
  echo -e "${RED}❌ Some tests failed:${NC}"
  for failed_test in "${FAILED_LIST[@]}"; do
    echo -e "   - $failed_test"
  done
  exit 1
else
  echo ""
  echo -e "${GREEN}✅ All tests passed successfully!${NC}"
  exit 0
fi
