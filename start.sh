#!/bin/bash

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting MediScanAI...${NC}"

# 1. Check/Start Ollama (Local LLM Backend)
echo -e "${GREEN}🔍 Checking local Ollama LLM service...${NC}"

OLLAMA_RUNNING=false
# Check if Ollama is already running on port 11434
if curl -s http://localhost:11434 >/dev/null; then
    echo -e "${GREEN}✅ Ollama is already running.${NC}"
    OLLAMA_RUNNING=true
else
    echo -e "${YELLOW}⚠️ Ollama is not running. Attempting to start it...${NC}"
    
    # Try starting Ollama Desktop App on macOS
    if [ -d "/Applications/Ollama.app" ]; then
        echo -e "${GREEN}📱 Found Ollama.app, launching...${NC}"
        open -a Ollama
    elif command -v ollama &> /dev/null; then
        echo -e "${GREEN}⚙️ Found ollama CLI, starting service in background...${NC}"
        ollama serve > /dev/null 2>&1 &
    else
        echo -e "${RED}❌ Ollama is not installed or not in PATH.${NC}"
        echo -e "${YELLOW}Please install Ollama from https://ollama.com and make sure it is running.${NC}"
    fi

    # Wait for Ollama to start up
    echo -n "Waiting for Ollama to respond"
    for i in {1..20}; do
        if curl -s http://localhost:11434 >/dev/null; then
            echo -e "\n${GREEN}✅ Ollama started successfully!${NC}"
            OLLAMA_RUNNING=true
            break
        fi
        echo -n "."
        sleep 1
    done
    echo ""
fi

# 2. Check and pull the required LLM model
if [ "$OLLAMA_RUNNING" = true ] && command -v ollama &> /dev/null; then
    REQUIRED_MODEL="mistral"
    echo -e "${GREEN}🔍 Checking for model: $REQUIRED_MODEL...${NC}"
    if ollama list | grep -q "$REQUIRED_MODEL"; then
        echo -e "${GREEN}✅ Model $REQUIRED_MODEL is already installed.${NC}"
    else
        echo -e "${YELLOW}📥 Model $REQUIRED_MODEL not found. Pulling it now (this might take a while)...${NC}"
        ollama pull "$REQUIRED_MODEL"
    fi
fi

# 3. Determine how to run Streamlit (Conda environment vs. local python/streamlit)
CONDA_ENV="med-env"
RUN_CMD=""

if command -v streamlit &> /dev/null; then
    # Streamlit is already in path (active env)
    echo -e "${GREEN}✅ Streamlit detected in active environment.${NC}"
    RUN_CMD="streamlit run frontend/app_new.py"
elif command -v conda &> /dev/null; then
    # Conda is available, check if the environment exists
    if conda env list | grep -q "$CONDA_ENV"; then
        echo -e "${GREEN}📦 Found conda environment '$CONDA_ENV'. Running app using conda run...${NC}"
        RUN_CMD="conda run --no-capture-output -n $CONDA_ENV streamlit run frontend/app_new.py"
    fi
fi

if [ -z "$RUN_CMD" ]; then
    echo -e "${RED}❌ Streamlit not found in current PATH, and conda environment '$CONDA_ENV' could not be used automatically.${NC}"
    echo -e "${YELLOW}Attempting to run 'streamlit run frontend/app_new.py' directly as fallback...${NC}"
    RUN_CMD="streamlit run frontend/app_new.py"
fi

# 4. Start the frontend Streamlit application
echo -e "${GREEN}🎨 Starting Streamlit Frontend...${NC}"
eval "$RUN_CMD"
