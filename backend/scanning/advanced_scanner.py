"""Advanced multi-band scanner with progress tracking."""

import logging
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class ScanBand:
    """Frequency band to scan."""

    start_freq: float
    end_freq: float
    step_size: float
    dwell_ms: int = 200
    threshold_db: float = -70


@dataclass
class ScanResult:
    """Result of a scan."""

    frequency: float
    power: float
    bandwidth: float
    snr: float
    timestamp: str
    category: str | None = None
    confidence: float | None = None


class AdvancedScanner:
    """Advanced scanner with multi-band support and progress tracking."""

    def __init__(self):
        self.is_scanning = False
        self.scan_thread: threading.Thread | None = None
        self.stop_scan_event = threading.Event()
        self.progress_callback: Callable[[dict[str, Any]], None] | None = None
        self.results: list[ScanResult] = []

    def scan_bands(
        self,
        bands: list[ScanBand],
        read_spectrum_fn: Callable[[float], tuple[Any, Any] | None],
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> list[ScanResult]:
        """
        Scan multiple frequency bands.

        Args:
            bands: List of frequency bands to scan
            read_spectrum_fn: Function to read spectrum at a frequency
            progress_callback: Optional callback for progress updates

        Returns:
            List of scan results
        """
        self.results = []
        self.progress_callback = progress_callback
        self.stop_scan_event.clear()

        total_steps = sum(
            int((band.end_freq - band.start_freq) / band.step_size) for band in bands
        )
        current_step = 0

        for band_idx, band in enumerate(bands):
            if self.stop_scan_event.is_set():
                break

            logger.info(
                f"Scanning band {band_idx + 1}/{len(bands)}: "
                f"{band.start_freq/1e6:.3f} - {band.end_freq/1e6:.3f} MHz"
            )

            freq = band.start_freq
            while freq <= band.end_freq and not self.stop_scan_event.is_set():
                # Read spectrum
                result = read_spectrum_fn(freq)
                if result:
                    freqs, spectrum = result
                    if spectrum is not None and len(spectrum) > 0:
                        max_power = float(np.max(spectrum))
                        if max_power >= band.threshold_db:
                            # Signal detected
                            max_idx = int(np.argmax(spectrum))
                            signal_freq = freqs[max_idx] + freq

                            scan_result = ScanResult(
                                frequency=signal_freq,
                                power=max_power,
                                bandwidth=0.0,  # Could estimate from spectrum
                                snr=max_power - np.mean(spectrum),
                                timestamp=datetime.now().isoformat(),
                            )
                            self.results.append(scan_result)

                # Update progress
                current_step += 1
                if self.progress_callback:
                    progress = {
                        "current_band": band_idx + 1,
                        "total_bands": len(bands),
                        "current_freq": freq,
                        "band_start": band.start_freq,
                        "band_end": band.end_freq,
                        "progress": current_step / total_steps,
                        "signals_found": len(self.results),
                    }
                    self.progress_callback(progress)

                # Dwell time
                time.sleep(band.dwell_ms / 1000.0)
                freq += band.step_size

        return self.results

    def start_scan(
        self,
        bands: list[dict[str, Any]],
        read_spectrum_fn: Callable[[float], tuple[Any, Any] | None],
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
    ):
        """
        Start scanning in a separate thread.

        Args:
            bands: List of band dictionaries
            read_spectrum_fn: Function to read spectrum
            progress_callback: Optional progress callback
        """
        if self.is_scanning:
            return {"success": False, "error": "Already scanning"}

        # Convert band dicts to ScanBand objects
        scan_bands = [
            ScanBand(
                start_freq=float(b["start_freq"]),
                end_freq=float(b["end_freq"]),
                step_size=float(b.get("step_size", 100e3)),
                dwell_ms=int(b.get("dwell_ms", 200)),
                threshold_db=float(b.get("threshold_db", -70)),
            )
            for b in bands
        ]

        self.is_scanning = True
        self.stop_scan_event.clear()

        def scan_worker():
            try:
                self.scan_bands(scan_bands, read_spectrum_fn, progress_callback)
            finally:
                self.is_scanning = False

        self.scan_thread = threading.Thread(target=scan_worker, daemon=True)
        self.scan_thread.start()

        return {"success": True, "message": "Scan started"}

    def stop_scan(self):
        """Stop the current scan."""
        if not self.is_scanning:
            return {"success": False, "error": "Not scanning"}

        self.stop_scan_event.set()
        if self.scan_thread and self.scan_thread.is_alive():
            self.scan_thread.join(timeout=5.0)

        self.is_scanning = False
        return {"success": True, "results": [r.__dict__ for r in self.results]}

    def get_progress(self) -> dict[str, Any]:
        """Get current scan progress."""
        return {
            "is_scanning": self.is_scanning,
            "results_count": len(self.results),
        }


# Global scanner instance
advanced_scanner = AdvancedScanner()

