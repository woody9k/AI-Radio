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
- **Frequency Tuning**: Use the per-digit stepper (GHz/MHz/kHz/Hz buttons) or numeric input in the Spectrum header. Click-to-tune also works by clicking directly on the spectrum.
- **Mode and Bandwidth**: Select Mode (WFM/NFM/AM/SSB) and choose Bandwidth:
  - **Auto**: Uses sensible defaults per mode (e.g., WFM → 200kHz, NFM → 12.5kHz)
  - **Preset**: Quick-select common bandwidths for the selected mode
  - **Custom**: Enter your own value (validated per mode; persists when switching modes)
- Spectrum and waterfall views; click-to-tune or drag-to-select bandwidth.
- Presets panel for common bands (displayed below S-Meter in main column).

## Testing
- `./test_rtlsdr.sh --clean` to free device and run `rtl_test -t`.
- `./test_ai.sh` to check AI endpoint reachability.

## Stop
- `./stop.sh` to stop backend and frontend.
