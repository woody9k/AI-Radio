"""Pytest fixtures for AI-Radio tests."""

import numpy as np
import pytest

from backend.signal_processor import SignalProcessor, WaterfallProcessor


@pytest.fixture
def signal_processor():
    """Create a SignalProcessor instance for testing."""
    return SignalProcessor(sample_rate=2.048e6, fft_size=1024)


@pytest.fixture
def waterfall_processor():
    """Create a WaterfallProcessor instance for testing."""
    return WaterfallProcessor(width=1024, height=100)


@pytest.fixture
def mock_samples():
    """Generate mock IQ samples for testing."""
    # Generate a simple sine wave at 1 MHz offset
    sample_rate = 2.048e6
    fft_size = 1024
    duration = fft_size / sample_rate
    t = np.linspace(0, duration, fft_size, endpoint=False)
    
    # Create complex IQ samples with a signal at 1 MHz
    signal_freq = 1e6
    i_samples = np.cos(2 * np.pi * signal_freq * t)
    q_samples = np.sin(2 * np.pi * signal_freq * t)
    samples = i_samples + 1j * q_samples
    
    # Add some noise
    noise = (np.random.randn(fft_size) + 1j * np.random.randn(fft_size)) * 0.1
    samples = samples + noise
    
    return samples


@pytest.fixture
def mock_spectrum():
    """Generate a mock power spectrum for testing."""
    fft_size = 1024
    # Create a spectrum with a peak at bin 512 (center)
    spectrum = np.full(fft_size, -100.0)  # Noise floor
    spectrum[510:515] = -50.0  # Signal peak
    return spectrum


@pytest.fixture
def mock_rtlsdr():
    """Create a mock RTL-SDR device for testing."""
    from unittest.mock import MagicMock
    
    mock_sdr = MagicMock()
    mock_sdr.device_index = 0
    mock_sdr.center_freq = 100e6
    mock_sdr.sample_rate = 2.048e6
    mock_sdr.gain = "auto"
    mock_sdr.bandwidth = None
    
    # Mock read_samples to return test data
    def mock_read_samples(num_samples):
        t = np.linspace(0, num_samples / 2.048e6, num_samples, endpoint=False)
        signal = np.cos(2 * np.pi * 1e6 * t) + 1j * np.sin(2 * np.pi * 1e6 * t)
        noise = (np.random.randn(num_samples) + 1j * np.random.randn(num_samples)) * 0.1
        return signal + noise
    
    mock_sdr.read_samples = MagicMock(side_effect=mock_read_samples)
    mock_sdr.set_center_freq = MagicMock(return_value=None)
    mock_sdr.set_sample_rate = MagicMock(return_value=None)
    mock_sdr.set_gain = MagicMock(return_value=None)
    mock_sdr.set_bandwidth = MagicMock(return_value=None)
    mock_sdr.close = MagicMock(return_value=None)
    
    return mock_sdr


@pytest.fixture
def mock_sdr_device(mock_rtlsdr, monkeypatch):
    """Create a mock SDRDevice for testing."""
    from unittest.mock import patch
    from backend.sdr_interface import SDRDevice
    
    with patch("backend.sdr_interface.RtlSdr", return_value=mock_rtlsdr):
        device = SDRDevice(device_index=0)
        device.sdr = mock_rtlsdr
        device.is_connected = True
        return device

