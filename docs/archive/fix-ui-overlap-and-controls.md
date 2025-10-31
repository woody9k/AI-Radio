# UI Overlap and Consistency Fix Plan (Completed)

**Status:** ✅ Completed and merged to main

**Date Completed:** 2024

## Scope
Stabilize header + nav stacking, restore proper page scrolling, and refactor the 3-column layout so side panels and main content never overlap. Align with existing CSS variables and React structure.

## Changes Implemented

### 1. Global Scrolling and Root Sizing
- ✅ Restored `body { overflow: auto; }` for page-level scrolling
- ✅ Changed `#root` to `min-height: 100vh` instead of fixed `height: 100vh`

### 2. Header and Navigation Stacking
- ✅ Added CSS variables: `--header-h: 64px; --nav-h: 44px;`
- ✅ Made `.app-header` sticky with explicit height
- ✅ Made `.top-nav` sticky beneath header with proper z-index
- ✅ Removed ad-hoc padding from `.app-content` and `.left-panel`

### 3. CSS Grid Layout
- ✅ Converted `.app-content` from flexbox to CSS Grid
- ✅ Grid template: `260px 1fr 280px` (left, main, right)
- ✅ Added `min-width: 0` to `.main-content` to prevent overflow
- ✅ Added `position: relative` to contain absolutely positioned children

### 4. Component Positioning
- ✅ Removed overflow from left column controls
- ✅ Moved frequency numeric input and per-digit stepper to Spectrum header
- ✅ Cleaned up unused code (ESLint zero errors)

### 5. Responsive Behavior
- ✅ At ≤768px: grid collapses to single column

### 6. Mode/Bandwidth Linkage
- ✅ Added Mode-to-bandwidth presets (WFM: 200kHz default, NFM: 12.5kHz, AM: 9kHz, SSB: 2.4kHz)
- ✅ Added Auto option that sets sensible defaults per mode
- ✅ Added Custom bandwidth option with per-mode persistence
- ✅ Added validation/clamping of bandwidth values per mode

## Files Modified
- `frontend/src/index.css`
- `frontend/src/App.css`
- `frontend/src/components/Controls.jsx`
- `frontend/src/components/SpectrumDisplay.jsx`

## Merge Information
- Branch: `fix/ui-overlap-and-controls`
- Merged to: `main`
- Commit: See git history

