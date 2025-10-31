# Release Notes

## [Unreleased]
### Added
- OpenAI integration (AI commands, settings)
- FM/NOAA scanners
- Chat and Settings UI
- Scripts: stop.sh, test_ai.sh; improved setup/start/test
- **Frequency controls in Spectrum header**: Per-digit stepper (GHz/MHz/kHz/Hz) and numeric input
- **Mode/Bandwidth linkage**: Auto presets, mode-specific presets, and custom bandwidth with per-mode persistence
- **CSS Grid layout**: Responsive 3-column grid replacing fixed flexbox layout

### Changed
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
