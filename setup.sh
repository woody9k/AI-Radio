#!/bin/bash

# AI-Radio Setup Script
echo "🔧 Setting up AI-Radio..."

# Check if we're in the right directory
if [ ! -f "requirements.txt" ]; then
    echo "❌ Please run this script from the AI-Radio root directory"
    exit 1
fi

# Install system dependencies
echo "📦 Installing system dependencies..."
sudo apt update
sudo apt install -y python3-venv python3-pip nodejs npm

# Install RTL-SDR dependencies
echo "📡 Installing RTL-SDR system dependencies..."
sudo apt install -y rtl-sdr librtlsdr0 rtl-sdr-dev libusb-1.0-0 libusb-1.0-0-dev

# Install udev rules for RTL-SDR (allows non-root access)
echo "🔧 Setting up RTL-SDR udev rules..."
sudo bash -c 'wget -O /etc/udev/rules.d/20-rtlsdr.rules https://raw.githubusercontent.com/osmocom/rtl-sdr/master/rtl-sdr.rules'
sudo udevadm control --reload-rules
sudo udevadm trigger

echo "⚠️  RTL-SDR udev rules installed. You may need to:"
echo "   - Unplug and re-plug your RTL-SDR device, OR"
echo "   - Re-attach via usbipd if using WSL2"

# Create virtual environment
echo "🐍 Creating Python virtual environment..."
python3 -m venv venv

# Activate virtual environment and install Python dependencies
echo "📚 Installing Python dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Install Node.js dependencies
echo "📦 Installing Node.js dependencies..."
cd frontend
npm install
cd ..

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p data/samples
mkdir -p data/datasets
mkdir -p ml-models
mkdir -p docs

# Test RTL-SDR installation
echo "🧪 Testing RTL-SDR installation..."
if command -v rtl_test &> /dev/null; then
    echo "✅ RTL-SDR tools installed successfully"
    echo "📡 To test your RTL-SDR device, run: rtl_test -t"
else
    echo "⚠️  RTL-SDR tools not found. Please check the installation."
fi

echo "✅ Setup complete!"
echo ""
echo "🚀 To start AI-Radio, run: ./start.sh"
echo "📡 Backend will be available at: http://localhost:5000"
echo "🌐 Frontend will be available at: http://localhost:3000"
echo ""
echo "📋 Next steps:"
echo "1. Connect your RTL-SDR device"
echo "2. Test your device: rtl_test -t"
echo "3. Run ./start.sh to start the application"
echo "4. Open http://localhost:3000 in your browser"
echo ""
echo "🔧 Troubleshooting:"
echo "- If you get 'usb_claim_interface error -6', another process is using the device"
echo "- For WSL2 users: Use 'usbipd wsl attach' to connect your RTL-SDR"
echo "- If device not found, try unplugging and re-plugging the device"


