#!/bin/bash

# Kill RTL-SDR Processes Script
# This script finds and kills all processes using the RTL-SDR device

echo "🔍 Searching for RTL-SDR processes..."
echo ""

# Find Python processes that might be using RTL-SDR
echo "Python processes:"
ps aux | grep -E "[p]ython.*app.py|[p]ython.*rtl|[r]tl_test|[r]tl_tcp|[r]tl_fm|[r]tl_sdr" | grep -v grep

# Get PIDs
PIDS=$(ps aux | grep -E "[p]ython.*app.py|[p]ython.*rtl|[r]tl_test|[r]tl_tcp|[r]tl_fm|[r]tl_sdr" | grep -v grep | awk '{print $2}')

if [ -z "$PIDS" ]; then
    echo ""
    echo "✅ No RTL-SDR processes found."
    echo ""
    echo "If you're still getting usb_claim_interface error -6, try:"
    echo "  1. Unplug and replug the RTL-SDR device"
    echo "  2. Run: sudo rmmod dvb_usb_rtl28xxu rtl2832"
    echo "  3. Check if running in another terminal/session"
    exit 0
fi

echo ""
echo "💀 Found RTL-SDR processes with PIDs: $PIDS"
echo ""
read -p "Kill these processes? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    for PID in $PIDS; do
        echo "Killing PID $PID..."
        kill -9 $PID 2>/dev/null
        if [ $? -eq 0 ]; then
            echo "  ✓ Killed $PID"
        else
            echo "  ✗ Failed to kill $PID (may need sudo)"
        fi
    done
    echo ""
    echo "✅ Done! Wait 2 seconds for USB device to release..."
    sleep 2
    echo ""
    echo "You can now start your backend again."
else
    echo "Aborted. No processes killed."
fi

