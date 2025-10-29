#!/bin/bash

# RTL-SDR Test Script
echo "🧪 Testing RTL-SDR Setup..."

# Check if rtl_test is available
if ! command -v rtl_test &> /dev/null; then
    echo "❌ rtl_test not found. Please run ./setup.sh first."
    exit 1
fi

echo "✅ RTL-SDR tools found"

# Optional pre-clean to avoid usb_claim_interface error -6
if [ "$1" = "--clean" ]; then
  echo "🧼 Pre-cleaning RTL-SDR related processes..."
  ./quick_kill_rtlsdr.sh
fi

# Test device detection
echo "📡 Scanning for RTL-SDR devices..."
rtl_test -t

echo ""
echo "📋 Test Results:"
echo "- If you see 'Found X device(s)' above, your RTL-SDR is detected"
echo "- If you see 'No E4000 tuner found, aborting', that's normal for RTL-SDR Blog V4"
echo "- If you see 'usb_claim_interface error -6', another process is using the device"
echo ""
echo "🔧 Troubleshooting:"
echo "- Kill any running AI-Radio processes: ./stop.sh or pkill -f 'python app.py'"
echo "- For WSL2: Use 'usbipd wsl attach' to connect your RTL-SDR"
echo "- Try unplugging and re-plugging your RTL-SDR device"
if [ -f /etc/udev/rules.d/20-rtlsdr.rules ]; then
  echo "- udev rules present: non-root access should work"
else
  echo "- udev rules missing: run ./setup.sh to install RTL-SDR udev rules"
fi
