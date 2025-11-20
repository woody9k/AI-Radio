"""Unit tests for SignalProcessor."""

import numpy as np
import pytest

from backend.signal_processor import SignalProcessor, WaterfallProcessor


@pytest.mark.unit
class TestSignalProcessor:
    """Test SignalProcessor class."""

    def test_init(self, signal_processor):
        """Test SignalProcessor initialization."""
        assert signal_processor.sample_rate == 2.048e6
        assert signal_processor.fft_size == 1024
        assert len(signal_processor.window) == 1024
        assert len(signal_processor.freq_bins) == 1024

    def test_set_sample_rate(self, signal_processor):
        """Test setting sample rate."""
        new_rate = 1.024e6
        signal_processor.set_sample_rate(new_rate)
        assert signal_processor.sample_rate == new_rate
        # Frequency bins should be recalculated
        assert len(signal_processor.freq_bins) == 1024

    def test_set_fft_size(self, signal_processor):
        """Test setting FFT size."""
        new_size = 2048
        signal_processor.set_fft_size(new_size)
        assert signal_processor.fft_size == new_size
        assert len(signal_processor.window) == new_size
        assert len(signal_processor.freq_bins) == new_size

    def test_set_window(self, signal_processor):
        """Test setting window function."""
        signal_processor.set_window("hann")
        assert signal_processor.window is not None
        assert len(signal_processor.window) == 1024

    def test_set_window_invalid(self, signal_processor):
        """Test setting invalid window function."""
        original_window = signal_processor.window.copy()
        signal_processor.set_window("invalid")
        # Should keep original window
        assert np.array_equal(signal_processor.window, original_window)

    def test_compute_fft(self, signal_processor, mock_samples):
        """Test FFT computation."""
        freqs, spectrum = signal_processor.compute_fft(mock_samples)
        
        assert len(freqs) == signal_processor.fft_size
        assert len(spectrum) == signal_processor.fft_size
        assert np.all(np.isfinite(spectrum))
        # Spectrum should be in dB
        assert np.all(spectrum < 0) or np.any(spectrum > -200)

    def test_compute_fft_padding(self, signal_processor):
        """Test FFT with samples smaller than FFT size."""
        small_samples = np.random.randn(512) + 1j * np.random.randn(512)
        freqs, spectrum = signal_processor.compute_fft(small_samples)
        
        assert len(freqs) == signal_processor.fft_size
        assert len(spectrum) == signal_processor.fft_size

    def test_compute_fft_truncation(self, signal_processor):
        """Test FFT with samples larger than FFT size."""
        large_samples = np.random.randn(2048) + 1j * np.random.randn(2048)
        freqs, spectrum = signal_processor.compute_fft(large_samples)
        
        assert len(freqs) == signal_processor.fft_size
        assert len(spectrum) == signal_processor.fft_size

    def test_compute_psd_welch(self, signal_processor, mock_samples):
        """Test PSD computation using Welch's method."""
        freqs, psd = signal_processor.compute_psd(mock_samples, method="welch")
        
        assert len(freqs) > 0
        assert len(psd) > 0
        assert np.all(np.isfinite(psd))

    def test_compute_psd_periodogram(self, signal_processor, mock_samples):
        """Test PSD computation using periodogram."""
        freqs, psd = signal_processor.compute_psd(mock_samples, method="periodogram")
        
        assert len(freqs) > 0
        assert len(psd) > 0
        assert np.all(np.isfinite(psd))

    def test_compute_psd_invalid_method(self, signal_processor, mock_samples):
        """Test PSD with invalid method."""
        with pytest.raises(ValueError, match="Unknown PSD method"):
            signal_processor.compute_psd(mock_samples, method="invalid")

    def test_find_peaks(self, signal_processor, mock_spectrum):
        """Test peak detection."""
        peaks, properties = signal_processor.find_peaks(mock_spectrum)
        
        assert len(peaks) > 0
        assert "peak_heights" in properties
        # Should find the peak we created
        assert 510 <= peaks[0] <= 515

    def test_find_peaks_no_peaks(self, signal_processor):
        """Test peak detection with no peaks."""
        flat_spectrum = np.full(1024, -100.0)
        peaks, properties = signal_processor.find_peaks(flat_spectrum, height=-50)
        
        assert len(peaks) == 0

    def test_detect_signals(self, signal_processor, mock_spectrum):
        """Test signal detection."""
        center_freq = 100e6
        signals = signal_processor.detect_signals(mock_spectrum, center_freq)
        
        assert len(signals) > 0
        signal = signals[0]
        assert "frequency" in signal
        assert "power" in signal
        assert "bandwidth" in signal
        assert "snr" in signal
        assert signal["frequency"] > 0

    def test_detect_signals_threshold(self, signal_processor, mock_spectrum):
        """Test signal detection with high threshold."""
        center_freq = 100e6
        signals = signal_processor.detect_signals(mock_spectrum, center_freq, threshold=-30)
        
        # With high threshold, should find fewer or no signals
        assert isinstance(signals, list)

    def test_estimate_bandwidth(self, signal_processor, mock_spectrum):
        """Test bandwidth estimation."""
        peak_idx = 512
        bandwidth = signal_processor._estimate_bandwidth(mock_spectrum, peak_idx)
        
        assert bandwidth > 0
        assert np.isfinite(bandwidth)

    def test_estimate_snr(self, signal_processor, mock_spectrum):
        """Test SNR estimation."""
        peak_idx = 512
        snr = signal_processor._estimate_snr(mock_spectrum, peak_idx)
        
        assert np.isfinite(snr)
        # SNR should be positive for a signal above noise
        assert snr > 0

    def test_decimate(self, signal_processor, mock_samples):
        """Test decimation."""
        decimation_factor = 4
        decimated = signal_processor.decimate(mock_samples, decimation_factor)
        
        expected_length = len(mock_samples) // decimation_factor
        assert len(decimated) == expected_length

    def test_decimate_no_decimation(self, signal_processor, mock_samples):
        """Test decimation with factor <= 1."""
        decimated = signal_processor.decimate(mock_samples, 1)
        assert len(decimated) == len(mock_samples)
        
        decimated = signal_processor.decimate(mock_samples, 0)
        assert len(decimated) == len(mock_samples)

    def test_extract_features(self, signal_processor, mock_samples):
        """Test feature extraction."""
        features = signal_processor.extract_features(mock_samples)
        
        assert "mean" in features
        assert "std" in features
        assert "rms" in features
        assert "peak" in features
        assert "spectral_centroid" in features
        assert "spectral_bandwidth" in features
        assert "total_power" in features
        
        # All features should be finite
        for value in features.values():
            assert np.isfinite(value)

    def test_get_frequency_range(self, signal_processor):
        """Test frequency range calculation."""
        center_freq = 100e6
        start_freq, end_freq = signal_processor.get_frequency_range(center_freq)
        
        expected_start = center_freq - signal_processor.sample_rate / 2
        expected_end = center_freq + signal_processor.sample_rate / 2
        
        assert abs(start_freq - expected_start) < 1.0
        assert abs(end_freq - expected_end) < 1.0

    def test_get_frequency_resolution(self, signal_processor):
        """Test frequency resolution calculation."""
        resolution = signal_processor.get_frequency_resolution()
        
        expected = signal_processor.sample_rate / signal_processor.fft_size
        assert abs(resolution - expected) < 1.0


@pytest.mark.unit
class TestWaterfallProcessor:
    """Test WaterfallProcessor class."""

    def test_init(self, waterfall_processor):
        """Test WaterfallProcessor initialization."""
        assert waterfall_processor.width == 1024
        assert waterfall_processor.height == 100
        assert waterfall_processor.current_row == 0

    def test_add_spectrum(self, waterfall_processor, mock_spectrum):
        """Test adding spectrum to waterfall."""
        waterfall_processor.add_spectrum(mock_spectrum)
        
        assert waterfall_processor.current_row == 1
        # Check that data was added
        waterfall_data = waterfall_processor.get_waterfall()
        assert waterfall_data.shape == (100, 1024)

    def test_add_spectrum_wraparound(self, waterfall_processor, mock_spectrum):
        """Test waterfall wraparound."""
        # Add more spectra than height
        for _ in range(150):
            waterfall_processor.add_spectrum(mock_spectrum)
        
        # Should wrap around
        assert waterfall_processor.current_row == 50

    def test_get_waterfall(self, waterfall_processor, mock_spectrum):
        """Test getting waterfall data."""
        waterfall_processor.add_spectrum(mock_spectrum)
        waterfall_data = waterfall_processor.get_waterfall()
        
        assert waterfall_data.shape == (100, 1024)
        assert np.all(waterfall_data >= 0)
        assert np.all(waterfall_data <= 255)

    def test_clear(self, waterfall_processor, mock_spectrum):
        """Test clearing waterfall."""
        waterfall_processor.add_spectrum(mock_spectrum)
        waterfall_processor.clear()
        
        assert waterfall_processor.current_row == 0
        waterfall_data = waterfall_processor.get_waterfall()
        assert np.all(waterfall_data == 0)

