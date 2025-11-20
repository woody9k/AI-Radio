# AI-Radio API Overview

OpenAPI spec: see `docs/openapi.yaml`.

## REST Endpoints (high-level)

- GET `/api/health` → `{ success, device_connected, streaming, timestamp }`
- GET `/api/devices` → `{ success, devices, device_info }`
- POST `/api/devices/{index}/connect` → connect device
- POST `/api/devices/{index}/disconnect` → disconnect device
- GET/POST `/api/settings` → SDR device settings (frequency, sample_rate, gain, bandwidth)
- POST `/api/stream/start` / `/api/stream/stop` → control spectrum streaming
- GET `/api/spectrum` → one-shot FFT + detected signals with classifications
  - Response includes: `frequencies` (relative), `absolute_frequencies`, `center_frequency`, `sample_rate`, `resolution_hz`, `spectrum`, `signals`, `timestamp`
- GET `/api/spectrum/zoom?center={Hz}&span={Hz}&fft={N}` → high‑resolution zoom slice via decimation
  - Returns `frequencies` (relative), `absolute_frequencies`, `center_frequency`, `sample_rate` (post‑decimation), `resolution_hz`, `spectrum`, `timestamp`
- GET `/api/presets` → list presets; POST `/api/presets` → create; POST `/api/presets/{name}/apply`
- DELETE `/api/presets/{name}` → delete custom preset
- GET `/api/data/statistics` → data collection stats
- GET/POST `/api/data/datasets` → list/create datasets
- GET `/api/classifications` / `/api/classifications/stats` → classification stats
- POST `/api/classifications/label` → label signal
- POST `/api/audio/start` / `/api/audio/stop` → demod audio
- POST `/api/tune_signal` → smart tune to a signal and start audio
- GET/POST `/api/settings/ai` → AI provider/model/key settings (key masked on GET)
- POST `/api/ai/command` → `{ text, dry_run? }` → `{ success, intent, executed?, result? }`
- POST `/api/recording/start` → start recording IQ samples
- POST `/api/recording/stop` → stop recording and save metadata
- GET `/api/recording/status` → get current recording status
- GET `/api/recording/list` → list all recordings
- GET `/api/recording/<filename>` → get recording metadata
- DELETE `/api/recording/<filename>/delete` → delete recording
- GET `/api/recording/<filename>/download` → download recording file
- POST `/api/recording/<filename>/playback` → playback recording samples
- POST `/api/ml/train` → train ML model from collected data
- GET `/api/ml/models` → list available trained models
- POST `/api/ml/models/<name>/load` → load a trained model
- GET `/api/signals` → get signals from database (with filtering)
- GET `/api/signals/search?q={term}` → search signals by description/category
- GET `/api/signals/<id>` → get specific signal by ID
- GET `/api/signals/stats` → get signal statistics
- POST `/api/scan/advanced` → start advanced multi-band scan
- POST `/api/scan/stop` → stop current scan
- GET `/api/scan/status` → get scan progress
- GET `/api/scan/history` → get scan history

## WebSocket Events
- `spectrum_data` → `{ frequencies, absolute_frequencies, center_frequency, sample_rate, resolution_hz, spectrum, signals, features, timestamp }`
- `waterfall_data` → `{ data, timestamp }`
- `status` → `{ message }`
- `device_error` → `{ error, timestamp }`
- `audio_samples` → `{ samples, sample_rate, mode }`
