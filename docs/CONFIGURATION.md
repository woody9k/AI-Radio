# Configuration

## Environment Variables
- `OPENAI_API_KEY`: API key for OpenAI. Optional if set via Settings UI.
- `OPENAI_MODEL`: override model (default: `gpt-4o-mini`).
- `PORT`: frontend port (default 3000) when passed to `start.sh` environment.

## Settings File
- `data/settings.json` is used by the backend to persist AI settings.
- API: `GET/POST /api/settings/ai` (key masked on GET).

## Network
- Frontend binds to `0.0.0.0` in dev for LAN access.
- Backend listens on `0.0.0.0:5000` in debug (Flask dev server).

## Platform Notes
- Linux recommended for RTL-SDR.
- For WSL2: use `usbipd wsl attach --busid <BUSID>`.
