# Architecture Overview

## Components
- Backend: Flask + Socket.IO; modules for SDR, signal processing, presets, ML, AI.
- Frontend: React (Vite) UI with Spectrum/Waterfall, Controls, AI Chat, Settings.
  - Layout: CSS Grid with sticky header/nav; responsive breakpoints.
  - Frequency controls: Per-digit stepper and numeric input in Spectrum header.
  - Mode/Bandwidth: Linked presets with Auto option and per-mode custom persistence.
- Device: RTL-SDR via pyrtlsdr.

## Data Flow (high-level)
```
User → Frontend (React) → REST/WS → Backend (Flask/Socket.IO) → SDR → Samples → Processing → WS Updates → Frontend
```

## Key Modules
- `backend/sdr_interface.py`: device control with retry logic
- `backend/signal_processor.py`: FFT, detection, features
- `backend/ml/*`: data collection, rule-based classification, ML training pipeline
- `backend/ml/trainer.py`: ML model training and inference
- `backend/ml/preprocessing.py`: Feature extraction and preprocessing
- `backend/ai/*`: OpenAI parsing, intent routing
- `backend/radio/*`: band scanners (FM/NOAA)
- `backend/scanning/advanced_scanner.py`: Multi-band scanning with progress tracking
- `backend/recording.py`: IQ sample recording and playback manager
- `backend/database/*`: SQLAlchemy models and database utilities for signal storage
- `backend/utils/error_handler.py`: Retry decorators and circuit breakers
- `backend/tests/*`: Comprehensive test suite with pytest
- `frontend/src/App.css`: CSS Grid layout, sticky header/nav, responsive breakpoints
- `frontend/src/components/SpectrumDisplay.jsx`: Spectrum/waterfall with absolute frequency axis, SDR#‑style zoom/range sliders, passband overlay, average/peak traces, high‑res zoom, and touch gestures
- `frontend/src/utils/websocket.js`: WebSocket manager with exponential backoff reconnection
## Spectrum Pipeline Details
- Backend computes FFT (`signal_processor.compute_fft`) and now includes absolute frequencies, `center_frequency`, `sample_rate`, and `resolution_hz` in both REST and WebSocket payloads.
- High‑res zoom endpoint `/api/spectrum/zoom` performs decimation and a larger FFT (e.g., 8192) around the current center for spans < ~100 kHz.
- Frontend switches to zoom data automatically when the visible span is below the threshold; otherwise it uses the live stream data.
- `frontend/src/components/Controls.jsx`: Mode/Bandwidth linkage with presets and validation

## AI Command Path
1. Frontend sends text to `/api/ai/command`.
2. OpenAI returns structured intent.
3. Router validates and executes (tune/scan/etc.).
4. Result returned; UI updates and/or starts streams.
