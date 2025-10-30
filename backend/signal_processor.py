"""
Signal Processing Core

Provides FFT computation, power spectral density calculation, peak detection,
and other signal processing functions for real-time spectrum analysis.
"""

import logging
from typing import Any

import numpy as np
from scipy import signal
from scipy.fft import fft, fftfreq, fftshift
from scipy.signal import find_peaks, welch

logger = logging.getLogger(__name__)


class SignalProcessor:
    """Core signal processing class for spectrum analysis and feature extraction."""

    def __init__(self, sample_rate: float = 2.048e6, fft_size: int = 1024):
        self.sample_rate = sample_rate
        self.fft_size = fft_size

        # Window functions
        self.windows = {
            "hamming": signal.windows.hamming,
            "hann": signal.windows.hann,
            "blackman": signal.windows.blackman,
            "bartlett": signal.windows.bartlett,
            "rectangular": signal.windows.boxcar,
        }

        # Pre-compute window for efficiency
        self.window = self.windows["hamming"](fft_size)
        self.window_norm = np.sum(self.window**2) / fft_size

        # Frequency bins
        self.freq_bins = fftfreq(fft_size, 1 / sample_rate)
        self.freq_bins = fftshift(self.freq_bins)

        # Overlap for Welch's method
        self.overlap = fft_size // 2

    def set_sample_rate(self, sample_rate: float):
        """Update sample rate and recalculate frequency bins."""
        self.sample_rate = sample_rate
        self.freq_bins = fftfreq(self.fft_size, 1 / sample_rate)
        self.freq_bins = fftshift(self.freq_bins)

    def set_fft_size(self, fft_size: int):
        """Update FFT size and recalculate window and frequency bins."""
        self.fft_size = fft_size
        self.window = self.windows["hamming"](fft_size)
        self.window_norm = np.sum(self.window**2) / fft_size
        self.freq_bins = fftfreq(fft_size, 1 / self.sample_rate)
        self.freq_bins = fftshift(self.freq_bins)
        self.overlap = fft_size // 2

    def set_window(self, window_type: str):
        """Set the window function for FFT."""
        if window_type in self.windows:
            self.window = self.windows[window_type](self.fft_size)
            self.window_norm = np.sum(self.window**2) / self.fft_size
        else:
            logger.warning(f"Unknown window type: {window_type}")

    def compute_fft(self, samples: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """
        Compute FFT of input samples.

        Args:
            samples: Complex or real samples

        Returns:
            Tuple of (frequencies, power_spectrum)
        """
        if len(samples) != self.fft_size:
            # Zero-pad or truncate to match FFT size
            if len(samples) < self.fft_size:
                padded = np.zeros(self.fft_size, dtype=samples.dtype)
                padded[: len(samples)] = samples
                samples = padded
            else:
                samples = samples[: self.fft_size]

        # Apply window
        windowed_samples = samples * self.window

        # Compute FFT
        fft_result = fft(windowed_samples)
        fft_result = fftshift(fft_result)

        # Convert to power spectrum (dB)
        power_spectrum = 20 * np.log10(np.abs(fft_result) + 1e-12)

        return self.freq_bins, power_spectrum

    def compute_psd(
        self, samples: np.ndarray, method: str = "welch"
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Compute Power Spectral Density using Welch's method or periodogram.

        Args:
            samples: Input samples
            method: 'welch' or 'periodogram'

        Returns:
            Tuple of (frequencies, psd)
        """
        if method == "welch":
            freqs, psd = welch(
                samples,
                fs=self.sample_rate,
                window="hamming",
                nperseg=self.fft_size,
                noverlap=self.overlap,
                return_onesided=False,
            )
            # Convert to dB
            psd_db = 10 * np.log10(psd + 1e-12)
            return freqs, psd_db

        elif method == "periodogram":
            freqs, psd = signal.periodogram(
                samples, fs=self.sample_rate, window="hamming", return_onesided=False
            )
            psd_db = 10 * np.log10(psd + 1e-12)
            return freqs, psd_db

        else:
            raise ValueError(f"Unknown PSD method: {method}")

    def find_peaks(
        self, spectrum: np.ndarray, height: float = -80, distance: int = 10, prominence: float = 3
    ) -> tuple[np.ndarray, dict[str, Any]]:
        """
        Find peaks in the power spectrum.

        Args:
            spectrum: Power spectrum in dB
            height: Minimum peak height in dB
            distance: Minimum distance between peaks in bins
            prominence: Minimum peak prominence in dB

        Returns:
            Tuple of (peak_indices, peak_properties)
        """
        peaks, properties = find_peaks(
            spectrum, height=height, distance=distance, prominence=prominence
        )

        return peaks, properties

    def detect_signals(
        self, spectrum: np.ndarray, center_freq: float = 0, threshold: float = -70
    ) -> list[dict[str, Any]]:
        """
        Detect signals in the spectrum.

        Args:
            spectrum: Power spectrum in dB
            center_freq: Center frequency in Hz
            threshold: Detection threshold in dB

        Returns:
            List of detected signals with properties
        """
        peaks, properties = self.find_peaks(spectrum, height=threshold)

        signals = []
        for i, peak_idx in enumerate(peaks):
            # Calculate frequency
            freq = center_freq + self.freq_bins[peak_idx]

            # Get signal properties
            signal_info = {
                "frequency": float(freq),
                "power": float(spectrum[peak_idx]),
                "bin_index": int(peak_idx),
                "bandwidth": float(self._estimate_bandwidth(spectrum, peak_idx)),
                "snr": float(self._estimate_snr(spectrum, peak_idx)),
            }

            signals.append(signal_info)

        return signals

    def _estimate_bandwidth(
        self, spectrum: np.ndarray, peak_idx: int, threshold_db: float = 3
    ) -> float:
        """Estimate signal bandwidth at -3dB points."""
        peak_power = spectrum[peak_idx]
        threshold = peak_power - threshold_db

        # Find -3dB points
        left_idx = peak_idx
        right_idx = peak_idx

        # Search left
        while left_idx > 0 and spectrum[left_idx] > threshold:
            left_idx -= 1

        # Search right
        while right_idx < len(spectrum) - 1 and spectrum[right_idx] > threshold:
            right_idx += 1

        # Convert to frequency bandwidth
        bandwidth_bins = right_idx - left_idx
        bandwidth_hz = bandwidth_bins * (self.sample_rate / self.fft_size)

        return bandwidth_hz

    def _estimate_snr(self, spectrum: np.ndarray, peak_idx: int, noise_window: int = 50) -> float:
        """Estimate signal-to-noise ratio."""
        peak_power = spectrum[peak_idx]

        # Estimate noise floor from surrounding bins
        start_idx = max(0, peak_idx - noise_window)
        end_idx = min(len(spectrum), peak_idx + noise_window)

        # Exclude the peak itself
        noise_samples = np.concatenate(
            [spectrum[start_idx : peak_idx - 5], spectrum[peak_idx + 5 : end_idx]]
        )

        if len(noise_samples) == 0:
            return 0

        noise_floor = np.mean(noise_samples)
        snr = peak_power - noise_floor

        return snr

    def decimate(self, samples: np.ndarray, decimation_factor: int) -> np.ndarray:
        """
        Decimate samples by the given factor.

        Args:
            samples: Input samples
            decimation_factor: Decimation factor

        Returns:
            Decimated samples
        """
        if decimation_factor <= 1:
            return samples

        # Apply anti-aliasing filter before decimation
        nyquist = self.sample_rate / 2
        cutoff = nyquist / decimation_factor

        # Design low-pass filter
        b, a = signal.butter(8, cutoff / nyquist, btype="low")

        # Apply filter
        filtered = signal.filtfilt(b, a, samples)

        # Decimate
        decimated = filtered[::decimation_factor]

        return decimated

    def extract_features(self, samples: np.ndarray) -> dict[str, float]:
        """
        Extract statistical features from signal samples.

        Args:
            samples: Input samples

        Returns:
            Dictionary of extracted features
        """
        features = {}

        # Time domain features
        features["mean"] = float(np.mean(np.abs(samples)))
        features["std"] = float(np.std(samples))
        features["rms"] = float(np.sqrt(np.mean(np.abs(samples) ** 2)))
        features["peak"] = float(np.max(np.abs(samples)))
        features["crest_factor"] = float(
            features["peak"] / features["rms"] if features["rms"] > 0 else 0
        )

        # Spectral features
        freqs, spectrum = self.compute_fft(samples)
        features["spectral_centroid"] = float(
            np.sum(freqs * np.abs(spectrum)) / np.sum(np.abs(spectrum))
        )
        features["spectral_bandwidth"] = float(
            np.sqrt(
                np.sum(((freqs - features["spectral_centroid"]) ** 2) * np.abs(spectrum))
                / np.sum(np.abs(spectrum))
            )
        )

        # Power features
        total_power = float(np.sum(np.abs(spectrum) ** 2))
        features["total_power"] = total_power
        features["peak_power"] = float(np.max(np.abs(spectrum) ** 2))
        features["power_ratio"] = float(
            features["peak_power"] / total_power if total_power > 0 else 0
        )

        return features

    def get_frequency_range(self, center_freq: float) -> tuple[float, float]:
        """Get the frequency range covered by the current FFT."""
        start_freq = center_freq - self.sample_rate / 2
        end_freq = center_freq + self.sample_rate / 2

        return start_freq, end_freq

    def get_frequency_resolution(self) -> float:
        """Get the frequency resolution of the current FFT."""
        return self.sample_rate / self.fft_size


class WaterfallProcessor:
    """Process waterfall data for real-time spectrum display."""

    def __init__(self, width: int = 1024, height: int = 100):
        self.width = width
        self.height = height
        self.waterfall_data = np.zeros((height, width), dtype=np.float32)
        self.current_row = 0

    def add_spectrum(self, spectrum: np.ndarray):
        """Add a new spectrum line to the waterfall."""
        # Normalize spectrum to 0-255 range
        normalized = np.clip((spectrum + 100) / 100 * 255, 0, 255)

        # Resize if necessary
        if len(normalized) != self.width:
            normalized = np.interp(
                np.linspace(0, len(normalized) - 1, self.width),
                np.arange(len(normalized)),
                normalized,
            )

        # Add to waterfall
        self.waterfall_data[self.current_row] = normalized
        self.current_row = (self.current_row + 1) % self.height

    def get_waterfall(self) -> np.ndarray:
        """Get the current waterfall data."""
        # Roll data so newest is at the bottom
        rolled_data = np.roll(self.waterfall_data, -self.current_row, axis=0)
        return rolled_data

    def clear(self):
        """Clear the waterfall data."""
        self.waterfall_data.fill(0)
        self.current_row = 0
