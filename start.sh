#!/bin/bash

# AI-Radio Startup Script
echo "🚀 Starting AI-Radio..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run setup first."
    exit 1
fi

# Start backend
echo "🔧 Starting backend server..."
export PYTHONPATH="$(pwd)"
cd backend
source ../venv/bin/activate
PYTHONPATH="$(dirname "$(pwd)")" python app.py &
BACKEND_PID=$!
cd ..

# Wait a moment for backend to start
sleep 3

# Start frontend
echo "🎨 Starting frontend server..."
cd frontend
if ! command -v npm >/dev/null 2>&1; then
  echo "❌ npm not found. Run ./setup.sh or: sudo apt install npm nodejs"
  exit 1
fi
npm run dev -- --port ${PORT:-3000} --host 0.0.0.0 &
FRONTEND_PID=$!
cd ..

echo "✅ AI-Radio is starting up!"
echo "📡 Backend: http://localhost:5000"
echo "🌐 Frontend: http://localhost:${PORT:-3000}"
echo ""
echo "Press Ctrl+C to stop both servers"

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Stopping servers..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    echo "✅ Servers stopped"
    exit 0
}

# Set trap to cleanup on script exit
trap cleanup SIGINT SIGTERM

# Wait for user to stop
wait


