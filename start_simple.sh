#!/bin/bash

# Simple startup script for Scoratis
cd "$(dirname "$0")"

echo "🚀 Starting Scoratis..."

# Kill existing processes
pkill -f "python main.py" 2>/dev/null
pkill -f "vite" 2>/dev/null
sleep 2

# Start Backend
echo "📡 Starting Backend..."
cd backend
nohup python main.py > /tmp/scoratis_backend.log 2>&1 &
BACKEND_PID=$!
echo "   Backend PID: $BACKEND_PID"
cd ..

# Wait for backend
sleep 5

# Start Frontend
echo "🎨 Starting Frontend..."
cd frontend
nohup npx vite --host 0.0.0.0 --port 5173 > /tmp/scoratis_frontend.log 2>&1 &
FRONTEND_PID=$!
echo "   Frontend PID: $FRONTEND_PID"
cd ..

sleep 3

echo ""
echo "✅ Scoratis is running!"
echo ""
echo "   Frontend: http://localhost:5173"
echo "   Backend:  http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"
echo ""
echo "   Model: Qwen2.5:72b"
echo ""
echo "📝 Logs:"
echo "   Backend:  tail -f /tmp/scoratis_backend.log"
echo "   Frontend: tail -f /tmp/scoratis_frontend.log"
echo ""
