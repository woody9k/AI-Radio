#!/bin/bash

# Option to clean caches
CLEAN_CACHE=false
while [[ $# -gt 0 ]]; do
  case $1 in
    --clean-cache|--clean) CLEAN_CACHE=true; shift ;;
    *) shift ;;
  esac
done

echo "🛑 Stopping AI-Radio..."
pkill -f "python app.py" 2>/dev/null || true
pkill -f "vite" 2>/dev/null || true
pkill -f "npm run dev" 2>/dev/null || true

# Wait a moment for processes to terminate
sleep 1

# Clean caches if requested
if [ "$CLEAN_CACHE" = true ]; then
  echo "🧹 Cleaning caches..."
  
  # Python bytecode cache
  find . -type d -name "__pycache__" -not -path "./venv/*" -exec rm -rf {} + 2>/dev/null || true
  find . -type f -name "*.pyc" -not -path "./venv/*" -delete 2>/dev/null || true
  find . -type f -name "*.pyo" -not -path "./venv/*" -delete 2>/dev/null || true
  
  # Tool caches
  [ -d ".mypy_cache" ] && rm -rf .mypy_cache && echo "  ✓ Removed .mypy_cache"
  [ -d ".ruff_cache" ] && rm -rf .ruff_cache && echo "  ✓ Removed .ruff_cache"
  
  # Frontend build artifacts (if exists)
  [ -d "frontend/dist" ] && rm -rf frontend/dist && echo "  ✓ Removed frontend/dist"
  [ -d "frontend/build" ] && rm -rf frontend/build && echo "  ✓ Removed frontend/build"
  
  echo "✅ Caches cleaned"
fi

echo "✅ Stopped"


