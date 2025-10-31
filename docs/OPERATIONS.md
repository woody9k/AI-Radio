# Operations

## Start/Stop
- Start: `./start.sh`
- Stop: `./stop.sh`
- Stop with cache cleanup: `./stop.sh --clean-cache` or `./stop.sh --clean`

**When to clean caches:**
- After renaming/moving Python modules or changing imports
- When experiencing import errors or "module not found" issues
- After major refactoring or code reorganization
- When MyPy or Ruff show stale errors
- During normal iteration, cache cleaning is usually **not needed** (Python auto-recompiles on changes)

**What gets cleaned:**
- Python bytecode (`__pycache__/`, `*.pyc`, `*.pyo`) - speeds up startup but can cause issues after refactoring
- MyPy cache (`.mypy_cache/`) - type checker cache
- Ruff cache (`.ruff_cache/`) - linter cache
- Frontend build artifacts (`frontend/dist/`, `frontend/build/`) - production builds (only if exists)

## Health & Logs
- Health: `curl http://localhost:5000/api/health`
- Backend logs: `tail -f backend_output.log`
- Frontend started via Vite (dev server)

## Spectrum & Waterfall Operations
- High‑Res Zoom: backend endpoint `GET /api/spectrum/zoom?center={Hz}&span={Hz}&fft={N}` used when span < ~100 kHz.
- Frequency Axis: bottom labels reflect the current zoomed slice; left dBFS axis is ticked with a fixed top of −30 dBFS.
- Passband: drag overlay edges to adjust bandwidth; click/drag to tune.
- Waterfall: use Auto‑Gain and Rate controls to tune exposure and update rate.

## Troubleshooting
- See `TROUBLESHOOTING.md` in the repo root.
- Free RTL-SDR: `./quick_kill_rtlsdr.sh` or `./kill_rtlsdr_processes.sh`.

## Scripts
- Device test: `./test_rtlsdr.sh --clean`
- AI endpoint test: `./test_ai.sh`
