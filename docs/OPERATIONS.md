# Operations

## Start/Stop
- Start: `./start.sh`
- Stop: `./stop.sh`

## Health & Logs
- Health: `curl http://localhost:5000/api/health`
- Backend logs: `tail -f backend_output.log`
- Frontend started via Vite (dev server)

## Troubleshooting
- See `TROUBLESHOOTING.md` in the repo root.
- Free RTL-SDR: `./quick_kill_rtlsdr.sh` or `./kill_rtlsdr_processes.sh`.

## Scripts
- Device test: `./test_rtlsdr.sh --clean`
- AI endpoint test: `./test_ai.sh`
