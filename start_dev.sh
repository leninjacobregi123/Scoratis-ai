#!/bin/bash

# Scoratis Development Server Starter
# Starts FastAPI backend and Vite React frontend

echo "================================================"
echo "     SCORATIS - Development Environment"
echo "================================================"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Kill existing processes
echo -e "${BLUE}Stopping existing processes...${NC}"
pkill -f "uvicorn" 2>/dev/null
pkill -f "vite" 2>/dev/null
sleep 1

# Start FastAPI backend
echo -e "${CYAN}Starting FastAPI backend on port 8000...${NC}"
cd backend
source ../.venv/bin/activate 2>/dev/null || python3 -m venv ../.venv && source ../.venv/bin/activate
pip install -r requirements.txt -q
uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!
cd ..

# Wait for backend to start
sleep 3

# Start Vite React frontend
echo -e "${CYAN}Starting Vite React frontend on port 5173...${NC}"
cd frontend
npm install 2>/dev/null
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}     Scoratis is running!${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo -e "  Frontend: ${CYAN}http://localhost:5173${NC}"
echo -e "  Backend:  ${CYAN}http://localhost:8000${NC}"
echo -e "  API Docs: ${CYAN}http://localhost:8000/docs${NC}"
echo ""
echo -e "  Press Ctrl+C to stop all servers"
echo ""

# Wait for processes
wait
