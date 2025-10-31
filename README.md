# AI-Powered RTL-SDR Web Interface

A modern web-based interface for RTL-SDR devices with AI-powered anomaly detection and intelligent signal scanning.

## Features

- **Real-time Spectrum Visualization**: Waterfall displays and frequency plots
- **Interactive Spectrum Tuning**: Click to tune; drag to select bandwidth (center + BW); double‑click to center; snap‑to‑step
- **SDR#‑style Zoom & Range**: Vertical Zoom and dBFS Range sliders with ticked dBFS axis (top fixed at −30 dBFS; adjustable bottom −40…−180)
- **Absolute Frequency Axis**: Frequency graduations reflect the current zoomed slice and tuned center
- **High‑Res Zoom**: Automatic zoom FFT for spans < 100 kHz for finer resolution
- **Tuned Frequency Marker**: Always-visible marker and label at the tuned frequency
- **AI Signal Classification**: Automatically identify signal types (AM, FM, digital, etc.)
- **Anomaly Detection**: Detect unusual signals and interference patterns
- **Smart Scanning**: AI-guided frequency scanning based on learned patterns
- **User-Friendly Interface**: Simple presets for beginners, advanced controls for hobbyists
- **SDR#-Style Controls**: Left panel split into Radio and Device sections (Mode, Bandwidth, AGC, Squelch, Bias‑T when available)
- **Signal Recording**: Capture and replay interesting signals
 - **Passband Overlay**: Visual passband with draggable edges to adjust bandwidth
 - **Average/Peak Traces**: Optional moving average and peak‑hold overlays
 - **Waterfall Controls**: Auto‑gain and frame rate controls
 - **Debug Overlay**: Shows SR, FFT size, Hz/bin, and FPS

## Quick Start

### Prerequisites

- Python 3.8+
- Node.js 16+
- RTL-SDR device (optional for testing)
- Linux/macOS/Windows with RTL-SDR drivers

### Installation

**Option 1: Automated Setup (Recommended)**
```bash
./setup.sh
```
This script will automatically install:
- Python 3.8+ and Node.js dependencies
- RTL-SDR system libraries and tools
- udev rules for non-root device access
- Python virtual environment with all packages
- Frontend dependencies

**Option 2: Manual Setup**
1. **Install system dependencies**:
   ```bash
   sudo apt update
   sudo apt install -y python3-venv python3-pip nodejs npm
   ```

2. **Create virtual environment and install Python dependencies**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Install Node.js dependencies**:
   ```bash
   cd frontend
   npm install
   cd ..
   ```

### Running the Application

**Start both servers**:
```bash
./start.sh
```

**Or start manually**:
1. **Backend** (Terminal 1):
   ```bash
   cd backend
   source ../venv/bin/activate
   python app.py
   ```

2. **Frontend** (Terminal 2):
   ```bash
   cd frontend
   npm run dev
   ```

3. **Access the Interface**:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:5000

## Project Structure

```
AI-Radio/
├── backend/           # Python Flask backend
├── frontend/          # React frontend
├── ml-models/         # Saved TensorFlow models
├── data/              # Training data & logs
└── docs/              # Documentation
```

## Current Status

### ✅ **Completed Features**
- **RTL-SDR Interface**: Device detection, connection, and control
- **Signal Processing**: Real-time FFT, spectrum analysis, peak detection
- **Web Interface**: Modern React frontend with real-time visualizations
- **Preset System**: 10+ built-in presets for common radio applications (now displayed below the S‑Meter)
- **Data Collection**: Automatic ML training data gathering
- **REST API**: Complete backend API with WebSocket streaming
- **Real-time Visualization**: Spectrum plots and waterfall display
 - **AI Chat**: Right-side assistant for intent parsing and command execution
 - **Interactive Spectrum**: Click-to-tune and drag-to-select bandwidth
 - **S‑Meter Improvements**: Windowed, noise‑robust S‑unit calculation around tuned frequency

### 🔄 **In Progress**
- AI anomaly detection models
- Signal classification system
- Smart scanning engine

### 📋 **Planned Features**
- Advanced recording and export capabilities
- Signal database and history
- Interactive tutorials and help system
- Mobile-responsive design improvements

## Development

This project follows a progressive enhancement approach:
1. Start with basic SDR control and visualization
2. Add AI models progressively
3. Implement advanced features as optional components

### Documentation & Standards
- Style Guide: `docs/STYLE_GUIDE.md`
- Coding Standards: `docs/CODING_STANDARDS.md`
- API Docs: `docs/API.md` (OpenAPI: `docs/openapi.yaml`)
- Architecture: `docs/ARCHITECTURE.md`
- User Guide: `docs/USER_GUIDE.md`
- Configuration: `docs/CONFIGURATION.md`
- Operations: `docs/OPERATIONS.md`
- Security: `docs/SECURITY.md`

### Session Init
For each dev session, run:
```bash
scripts/session_init.sh --fix
```
This checks conformance (lint/format), applies fixes, optionally tests device/AI, and starts services.

### Updated Controls (SDR#‑style)
- **Frequency Controls** (in Spectrum header):
  - Per-digit stepper (GHz/MHz/kHz/Hz with ▲/▼ buttons)
  - Numeric input (Enter or blur to tune)
- Radio Section (left panel):
  - Frequency display (read-only; actual tuning via Spectrum header)
  - Mode selector: WFM, NFM, AM, SSB
  - Filter/Bandwidth dropdown with:
    - **Auto** option (sets mode-specific defaults: WFM 200kHz, NFM 12.5kHz, AM 9kHz, SSB 2.4kHz)
    - **Preset** values per mode (WFM: 150-250kHz, NFM: 8-15kHz, AM: 6-12kHz, SSB: 2-3kHz)
    - **Custom** option with per-mode persistence and validation
  - Squelch toggle and threshold slider
  - AGC toggle
- Device Section:

### Spectrum & Waterfall
- Zoom: mouse wheel (Shift = faster), Alt+wheel for fine pan
- Zoom/Range sliders (right): vertical Zoom; dBFS Range (top fixed at −30 dBFS)
- Axis: bottom frequency labels reflect the current zoom slice; left dBFS axis shows ticks and labels
- Passband: draggable edges adjust bandwidth; click or drag‑select tunes center/BW
- High‑Res Zoom: for spans < ~100 kHz the app fetches a high‑resolution FFT slice
- Waterfall: auto‑gain toggle and rate control (drop frames client‑side)
- Debug: SR/FFT/Hz‑per‑bin/FPS shown in the spectrum corner
  - Gain selector (Auto or fixed values)
  - Sample rate selector (250 kS/s–3.072 MS/s)
  - Bias‑T toggle (if supported, e.g., RTL‑SDR Blog V4)

### Themes
- Choose a theme in Settings → Theme (Minimal, Slate, Graphite, Forest). Your choice persists and applies to the spectrum, labels, and UI panels.

### Layout & Navigation
- **CSS Grid Layout**: 3-column responsive grid (left: 260px, main: flexible, right: 280px)
- **Sticky Header/Nav**: Header (64px) and navigation bar (44px) remain visible while scrolling
- **Responsive**: Grid collapses to single column at ≤768px width
- **Page-level Scrolling**: Panels use page scroll instead of inner scrollbars
- **Frequency Controls**: Moved to Spectrum header for better accessibility and consistency

### AI Settings
- Set your OpenAI API key in Settings → AI Settings, or export `OPENAI_API_KEY`.
- Chat panel (right side) sends commands to `/api/ai/command`.
- System prompt guides intent mapping to radio commands.

## Testing Your RTL-SDR Setup

**Test your RTL-SDR device:**
```bash
./test_rtlsdr.sh
```

**If you get device busy errors:**
```bash
./cleanup_rtlsdr.sh  # Kills conflicting processes
./test_rtlsdr.sh     # Test again
```

**Manual testing:**
```bash
rtl_test -t
```

**Expected output for RTL-SDR Blog V4:**
```
Found 1 device(s):
  0:  RTLSDRBlog, Blog V4, SN: 00000001
Using device 0: Generic RTL2832U OEM
Found Rafael Micro R828D tuner
RTL-SDR Blog V4 Detected
No E4000 tuner found, aborting.  # This is normal!
```

## Troubleshooting

### RTL-SDR Device Issues

**"usb_claim_interface error -6" (Resource busy):**
```bash
./cleanup_rtlsdr.sh  # Kill conflicting processes
```

**"No devices found":**
- Ensure RTL-SDR is connected via USB
- For WSL2: Use `usbipd wsl attach --busid <BUSID>`
- Try unplugging and re-plugging the device
- Check udev rules: `ls -la /etc/udev/rules.d/20-rtlsdr.rules`

**"No E4000 tuner found, aborting":**
- This is **normal** for RTL-SDR Blog V4 devices
- Your device is working correctly

**Permission denied:**
- Run `sudo udevadm control --reload-rules && sudo udevadm trigger`
- Unplug and re-plug your RTL-SDR device

## Testing Without RTL-SDR

The application can run without an RTL-SDR device for testing the interface:
- The backend will show a warning about missing RTL-SDR
- The frontend will display "No devices found" 
- All UI components and API endpoints are functional
- Connect an RTL-SDR device to enable full functionality

## License

MIT License - see LICENSE file for details
