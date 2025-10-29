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
- Spectrum and waterfall views; click-to-tune via Controls.
- Presets panel for common bands.

## Testing
- `./test_rtlsdr.sh --clean` to free device and run `rtl_test -t`.
- `./test_ai.sh` to check AI endpoint reachability.

## Stop
- `./stop.sh` to stop backend and frontend.
