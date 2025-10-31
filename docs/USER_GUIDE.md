# User Guide

## Install
- Run `./setup.sh` (installs Python/Node, RTL-SDR deps, creates venv, installs packages).

## Start
- Run `./start.sh`.
- Frontend: http://localhost:3000 (binds to 0.0.0.0; use your IP on LAN)
- Backend health: http://localhost:5000/api/health

## Settings
- Open the Settings tab and add your OpenAI API key; or export `OPENAI_API_KEY` before starting.

## Using AI Chat
- Examples: "tune to 104.1", "scan FM", "weather station", "tune to hydrogen line".
- AI explains actions and tunes/scan accordingly.

## Manual Radio
- Device connect, start/stop streaming.
- **Frequency Tuning**: Use the per-digit stepper (GHz/MHz/kHz/Hz buttons) or numeric input in the Spectrum header. Click to tune directly on the spectrum; double‑click to center; snap‑to‑step.
- **Mode and Bandwidth**: Select Mode (WFM/NFM/AM/SSB) and choose Bandwidth:
  - **Auto**: Uses sensible defaults per mode (e.g., WFM → 200kHz, NFM → 12.5kHz)
  - **Preset**: Quick-select common bandwidths for the selected mode
  - **Custom**: Enter your own value (validated per mode; persists when switching modes)
- Spectrum and waterfall views; click to tune or drag to select bandwidth. A passband overlay appears around the tuned frequency—drag its edges to adjust bandwidth.

### Spectrum Display Controls
- Wheel zoom (Shift for faster zoom), Alt+wheel to fine pan
- Right‑side vertical sliders:
  - **Zoom**: controls horizontal span (also updates wheel zoom)
  - **Range**: sets dBFS bottom (top fixed at −30 dBFS)
- Bottom axis: labels reflect the current zoomed slice; left axis shows dBFS ticks/labels
- Average and Peak overlays: enable in Spectrum Info panel
- Debug overlay: shows SR, FFT, Hz/bin, FPS

### High‑Resolution Zoom
- When zooming below ~100 kHz span, the app fetches a high‑resolution FFT slice for finer detail.

### Waterfall Controls
- Auto‑Gain toggle and a Rate control (Every frame, 1/2, 1/3, 1/5) to adjust update rate
- Presets panel for common bands (displayed below S-Meter in main column).

## Testing
- `./test_rtlsdr.sh --clean` to free device and run `rtl_test -t`.
- `./test_ai.sh` to check AI endpoint reachability.

## Stop
- `./stop.sh` to stop backend and frontend.
