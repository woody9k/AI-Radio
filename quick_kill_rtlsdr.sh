#!/bin/bash

# Quick Kill RTL-SDR Script (no confirmation)
# Immediately kills all RTL-SDR related processes

echo "💀 Killing all RTL-SDR processes..."

# Kill all python processes running app.py and rtl-related tools
pkill -9 -f "python.*app.py"
pkill -9 -f "rtl_test"
pkill -9 -f "rtl_tcp"
pkill -9 -f "rtl_fm"
pkill -9 -f "rtl_sdr"

echo "✅ Done! Waiting 2 seconds for USB device to release..."
sleep 2
echo "Ready to restart backend."

