#!/bin/bash

# Scoratis - Local Development Server
# Runs backend and frontend locally (PostgreSQL/Redis via Docker)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${CYAN}================================================${NC}"
echo -e "${CYAN}     SCORATIS - Local Development Mode${NC}"
echo -e "${CYAN}================================================${NC}"
echo ""

# Check if Docker services are running
echo -e "${BLUE}Checking Docker services...${NC}"
if ! docker ps | grep -q scoratis-postgres; then
    echo -e "${YELLOW}Starting PostgreSQL and Redis...${NC}"
    docker compose up -d postgres redis
    sleep 3
fi

if docker ps | grep -q scoratis-postgres && docker ps | grep -q scoratis-redis; then
    echo -e "${GREEN}PostgreSQL and Redis are running${NC}"
else
    echo -e "${RED}Failed to start Docker services${NC}"
    exit 1
fi

# Check Ollama
echo -e "${BLUE}Checking Ollama...${NC}"
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo -e "${GREEN}Ollama is running${NC}"
else
    echo -e "${YELLOW}Warning: Ollama is not running. Start it with: ollama serve${NC}"
fi

# Kill existing processes
echo -e "${BLUE}Stopping existing dev servers...${NC}"
pkill -f "uvicorn main:app" 2>/dev/null || true
pkill -f "vite" 2>/dev/null || true
sleep 1

# Start Backend
echo -e "${CYAN}Starting FastAPI backend...${NC}"
cd backend
if [ -d "../.venv" ]; then
    source ../.venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi
uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

# Wait for backend
echo -e "${BLUE}Waiting for backend to start...${NC}"
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}Backend is ready${NC}"
        break
    fi
    sleep 1
done

# Start Frontend
echo -e "${CYAN}Starting Vite frontend...${NC}"
cd frontend
npm run dev -- --host 0.0.0.0 &
FRONTEND_PID=$!
cd ..

sleep 3

echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}     Scoratis is running!${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo -e "  Frontend:  ${CYAN}http://localhost:5173${NC}"
echo -e "  Backend:   ${CYAN}http://localhost:8000${NC}"
echo -e "  API Docs:  ${CYAN}http://localhost:8000/docs${NC}"
echo ""
echo -e "  PostgreSQL: localhost:5433"
echo -e "  Redis:      localhost:6379"
echo ""
echo -e "  ${YELLOW}Press Ctrl+C to stop all servers${NC}"
echo ""

# Cleanup on exit
cleanup() {
    echo -e "\n${BLUE}Stopping servers...${NC}"
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    echo -e "${GREEN}Servers stopped. Docker services still running.${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Wait for processes
wait
