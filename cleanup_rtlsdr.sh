#!/bin/bash

# RTL-SDR Cleanup Script
echo "🧹 Cleaning up RTL-SDR processes..."

# Kill any running AI-Radio backend processes
echo "🔄 Stopping AI-Radio backend processes..."
pkill -f 'python app.py' 2>/dev/null || echo "No AI-Radio processes found"

# Kill any rtl_test processes
echo "🔄 Stopping rtl_test processes..."
pkill -f 'rtl_test' 2>/dev/null || echo "No rtl_test processes found"

# Wait a moment for processes to terminate
sleep 2

echo "✅ Cleanup complete!"
echo "📡 You can now test your RTL-SDR device with: ./test_rtlsdr.sh"
echo "🚀 Or start AI-Radio with: ./start.sh"
