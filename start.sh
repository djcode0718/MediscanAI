#!/usr/bin/env bash

# Define colors for clinical theme output
TEAL='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Clear terminal screen for clean presentation
clear

echo -e "${TEAL}🏥 ============================================${NC}"
echo -e "${TEAL}🏥             MediScanAI Starter               ${NC}"
echo -e "${TEAL}🏥    Privacy-First Multimodal Health Copilot   ${NC}"
echo -e "${TEAL}🏥 ============================================${NC}"
echo ""

# Helper to print step status
function print_status() {
  local status="$1"
  local msg="$2"
  case "$status" in
    "pending") echo -e "  ${YELLOW}[⋯]${NC} $msg..." ;;
    "success") echo -e "  ${GREEN}[✔]${NC} $msg" ;;
    "error")   echo -e "  ${RED}[✘]${NC} $msg" ;;
  esac
}

BACKEND_PID=""
FRONTEND_PID=""

# Cleanup function to kill background processes on Ctrl+C
function cleanup() {
  echo ""
  echo -e "${YELLOW}🛑 Shutting down MediScanAI processes safely...${NC}"
  
  if [ -n "$BACKEND_PID" ]; then
    kill "$BACKEND_PID" 2>/dev/null
    print_status "success" "Stopped FastAPI backend server"
  fi
  
  if [ -n "$FRONTEND_PID" ]; then
    kill "$FRONTEND_PID" 2>/dev/null
    print_status "success" "Stopped Vite frontend dev server"
  fi
  
  echo -e "${GREEN}✅ All processes closed. Stay healthy!${NC}"
  exit 0
}

# Trap Ctrl+C (SIGINT) and exit signals
trap cleanup SIGINT SIGTERM EXIT

# --- Step 1: Check and Start Ollama ---
print_status "pending" "Checking local Ollama LLM service"
OLLAMA_RUNNING=false

if curl -s http://localhost:11434 >/dev/null; then
  OLLAMA_RUNNING=true
  print_status "success" "Ollama service is active and running"
else
  print_status "pending" "Ollama is offline. Attempting to start Ollama App"
  if [ -d "/Applications/Ollama.app" ]; then
    open -a Ollama
  elif command -v ollama &> /dev/null; then
    ollama serve >/dev/null 2>&1 &
  else
    print_status "error" "Ollama installation not found. Please download from https://ollama.com"
    exit 1
  fi
  
  # Wait loop
  for i in {1..20}; do
    if curl -s http://localhost:11434 >/dev/null; then
      OLLAMA_RUNNING=true
      break
    fi
    sleep 1
  done
  
  if [ "$OLLAMA_RUNNING" = true ]; then
    print_status "success" "Ollama started successfully"
  else
    print_status "error" "Timed out waiting for Ollama. Please launch it manually."
    exit 1
  fi
fi

# --- Step 2: Check Model ---
print_status "pending" "Verifying Mistral model in Ollama"
if command -v ollama &> /dev/null; then
  if ollama list | grep -q "mistral"; then
    print_status "success" "Mistral LLM model is ready"
  else
    print_status "pending" "Model 'mistral' not found. Pulling now (this will take a while)"
    ollama pull mistral
    print_status "success" "Mistral model pulled successfully"
  fi
else
  print_status "warning" "Ollama CLI not in PATH. Assuming 'mistral' model is loaded."
fi

# --- Step 3: Check Conda Environment ---
CONDA_ENV="med-env"
RUN_CMD=""

print_status "pending" "Validating conda environment '$CONDA_ENV'"
if command -v conda &> /dev/null; then
  if conda env list | grep -q "$CONDA_ENV"; then
    print_status "success" "Found conda environment '$CONDA_ENV'"
    RUN_CMD="conda run --no-capture-output -n $CONDA_ENV"
  fi
fi

if [ -z "$RUN_CMD" ]; then
  print_status "error" "Conda environment '$CONDA_ENV' not found."
  echo -e "      Please configure the '$CONDA_ENV' environment or install python packages."
  exit 1
fi

# --- Step 4: Check Frontend Node Modules ---
print_status "pending" "Checking frontend node dependencies"
if [ ! -d "frontend/node_modules" ]; then
  print_status "pending" "node_modules folder missing. Running 'npm install' in frontend/"
  (cd frontend && npm install >/dev/null 2>&1)
  print_status "success" "Installed frontend node packages successfully"
else
  print_status "success" "Frontend node packages are ready"
fi

# --- Step 5: Launch Backend Server ---
print_status "pending" "Starting FastAPI server on http://127.0.0.1:8000"
# Clear previous logs if they exist
> backend_server.log
$RUN_CMD python -u -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 > backend_server.log 2>&1 &
BACKEND_PID=$!

# Stream logs until uvicorn is up
echo -e "${TEAL}--- Backend Startup Logs ---${NC}"
last_line=1
BACKEND_HEALTHY=false
while true; do
  if [ -f backend_server.log ]; then
    total_lines=$(wc -l < backend_server.log)
    if [ "$total_lines" -ge "$last_line" ]; then
      sed -n "${last_line},${total_lines}p" backend_server.log | while read -r line; do
        echo -e "  ${TEAL}api:${NC} $line"
      done
      last_line=$((total_lines + 1))
    fi
  fi

  # Check if backend is healthy
  if curl -s http://127.0.0.1:8000/ >/dev/null; then
    BACKEND_HEALTHY=true
    break
  fi

  # Check if process died
  if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    echo -e "${RED}✘ FastAPI backend failed to start. Logs:${NC}"
    if [ -f backend_server.log ]; then
      cat backend_server.log
    fi
    exit 1
  fi
  sleep 0.5
done
echo -e "${TEAL}-----------------------------${NC}"
print_status "success" "FastAPI backend server is listening on port 8000"

# --- Step 6: Launch Frontend Server ---
print_status "pending" "Starting Vite React development server on http://localhost:5173"
# Clear previous logs if they exist
> frontend_server.log
(cd frontend && npm run dev > ../frontend_server.log 2>&1) &
FRONTEND_PID=$!

# Stream logs until Vite is up
echo -e "${TEAL}--- Frontend Startup Logs ---${NC}"
last_line_fe=1
FRONTEND_UP=false
while true; do
  if [ -f frontend_server.log ]; then
    total_lines_fe=$(wc -l < frontend_server.log)
    if [ "$total_lines_fe" -ge "$last_line_fe" ]; then
      sed -n "${last_line_fe},${total_lines_fe}p" frontend_server.log | while read -r line; do
        echo -e "  ${GREEN}ui:${NC} $line"
      done
      last_line_fe=$((total_lines_fe + 1))
    fi
  fi

  # Check if frontend is healthy
  if curl -s http://localhost:5173/ >/dev/null; then
    FRONTEND_UP=true
    break
  fi

  # Check if process died
  if ! kill -0 "$FRONTEND_PID" 2>/dev/null; then
    echo -e "${RED}✘ Vite frontend dev server failed to start. Logs:${NC}"
    if [ -f frontend_server.log ]; then
      cat frontend_server.log
    fi
    exit 1
  fi
  sleep 0.5
done
echo -e "${TEAL}------------------------------${NC}"
print_status "success" "Vite React frontend server is listening on port 5173"

# --- Step 7: Open in Browser ---
print_status "pending" "Launching browser to MediScanAI workspace"
sleep 1
if command -v open &> /dev/null; then
  open "http://localhost:5173/"
elif command -v xdg-open &> /dev/null; then
  xdg-open "http://localhost:5173/"
fi
print_status "success" "App opened successfully in browser"

echo ""
echo -e "${TEAL}🚀 MediScanAI is ready!${NC}"
echo -e "   - Frontend UI:   ${GREEN}http://localhost:5173${NC}"
echo -e "   - Backend API:   ${GREEN}http://127.0.0.1:8000${NC}"
echo -e "   - Server logs:   backend_server.log | frontend_server.log"
echo ""
echo -e "${YELLOW}👉 Press [Ctrl+C] to stop all servers and exit safely.${NC}"
echo ""

# Stream live backend request logs in the foreground
echo -e "${TEAL}📋 Streaming live backend API request logs...${NC}"
echo "--------------------------------------------------"
tail -n 0 -f backend_server.log
