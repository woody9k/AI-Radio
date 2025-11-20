# Release Notes

## [Unreleased]
### Added
- **Testing Infrastructure**: Comprehensive test suite with pytest, unit tests for SignalProcessor and SDRDevice, integration tests for API endpoints
- **Error Handling**: Retry decorators with exponential backoff, circuit breakers for fault tolerance
- **Signal Recording**: IQ sample recording with metadata storage, playback, and export capabilities
- **Signal Database**: SQLite database for persistent signal storage with search and filtering
- **ML Training Pipeline**: Trainable classification models with preprocessing and evaluation
- **Advanced Scanning**: Multi-band scanning with progress tracking, cancellation, and scheduled scans
- **Mobile Support**: Touch gestures (pinch zoom, pan, tap) and responsive design improvements
- **WebSocket Resilience**: Improved reconnection handling with exponential backoff
- OpenAI integration (AI commands, settings)
- FM/NOAA scanners
- Chat and Settings UI
- Scripts: stop.sh, test_ai.sh; improved setup/start/test
- **Frequency controls in Spectrum header**: Per-digit stepper (GHz/MHz/kHz/Hz) and numeric input
- **Mode/Bandwidth linkage**: Auto presets, mode-specific presets, and custom bandwidth with per-mode persistence
- **CSS Grid layout**: Responsive 3-column grid replacing fixed flexbox layout

### Changed
- **SDR Interface**: Enhanced with retry logic for all device operations (connect, set_frequency, read_samples, etc.)
- **Signal Classifier**: Integrated ML models with automatic fallback to rule-based classification
- **WebSocket Manager**: Replaced direct socket.io usage with WebSocketManager class for better connection handling
- Bind frontend to 0.0.0.0; PYTHONPATH for backend
- **Layout**: Converted to CSS Grid with sticky header/nav for better stability
- **Frequency controls**: Moved from left panel to Spectrum display header
- **Bandwidth control**: Changed from free-form input to dropdown with Auto/Preset/Custom options
- **Responsive behavior**: Grid collapses to single column at ≤768px

### Fixed
- JSX fragment error in App.jsx
- **UI overlaps**: Header/nav stacking, column overlap, content rendering under banner
- **Left panel overflow**: Radio controls now fit properly within column width

## [0.1.0] - Initial foundation
- Backend/Frontend skeleton, SDR control, spectrum UI
