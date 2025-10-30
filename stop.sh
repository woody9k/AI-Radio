#!/bin/bash

echo "🛑 Stopping AI-Radio..."
pkill -f "python app.py" 2>/dev/null || true
pkill -f "vite" 2>/dev/null || true
pkill -f "npm run dev" 2>/dev/null || true
echo "✅ Stopped"


