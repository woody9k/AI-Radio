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

## Database Configuration
- SQLite database location: `instance/ai_radio.db`
- Database is automatically created on first startup
- Tables: `signals`, `classifications`, `recordings`
- Access via SQLAlchemy ORM models in `backend/database/models.py`

## Recording Configuration
- Recording directory: `data/recordings/` (auto-created)
- Recordings stored as binary IQ files (complex64 format)
- Metadata stored in database and JSON files

## ML Model Configuration
- Model directory: `ml-models/` (auto-created)
- Models stored as `.pkl` files (scikit-learn format)
- Feature scaler: `ml-models/feature_scaler.pkl`
- Model metadata: `ml-models/signal_classifier_model_metadata.json`

## Error Handling
- Retry logic: 3 attempts with exponential backoff (default)
- Circuit breaker: Opens after 3 failures, recovers after 5 seconds
- WebSocket reconnection: 5 attempts with exponential backoff (1-5 seconds)

## Platform Notes
- Linux recommended for RTL-SDR.
- For WSL2: use `usbipd wsl attach --busid <BUSID>`.
