"""Unit tests for SDRDevice and SDRManager."""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from backend.sdr_interface import SDRDevice, SDRManager


@pytest.mark.unit
class TestSDRDevice:
    """Test SDRDevice class."""

    def test_init(self):
        """Test SDRDevice initialization."""
        device = SDRDevice(device_index=0)
        
        assert device.device_index == 0
        assert device.sdr is None
        assert device.is_connected is False
        assert device.frequency == 100e6
        assert device.sample_rate == 2.048e6
        assert device.gain == "auto"

    def test_connect_success(self, mock_rtlsdr):
        """Test successful device connection."""
        with patch("backend.sdr_interface.RtlSdr", return_value=mock_rtlsdr):
            device = SDRDevice(device_index=0)
            result = device.connect()
            
            assert result is True
            assert device.is_connected is True
            assert device.sdr is not None
            mock_rtlsdr.set_sample_rate.assert_called_once()
            mock_rtlsdr.set_center_freq.assert_called_once()

    def test_connect_failure(self):
        """Test device connection failure."""
        with patch("backend.sdr_interface.RtlSdr", side_effect=Exception("Device not found")):
            device = SDRDevice(device_index=0)
            result = device.connect()
            
            assert result is False
            assert device.is_connected is False

    def test_connect_no_library(self, monkeypatch):
        """Test connection when pyrtlsdr is not available."""
        monkeypatch.setattr("backend.sdr_interface.RtlSdr", None)
        device = SDRDevice(device_index=0)
        result = device.connect()
        
        assert result is False
        assert device.is_connected is False

    def test_disconnect(self, mock_sdr_device):
        """Test device disconnection."""
        mock_sdr_device.disconnect()
        
        assert mock_sdr_device.is_connected is False
        assert mock_sdr_device.sdr is None

    def test_set_frequency(self, mock_sdr_device):
        """Test setting frequency."""
        new_freq = 104.1e6
        result = mock_sdr_device.set_frequency(new_freq)
        
        assert result is True
        assert mock_sdr_device.frequency == new_freq
        mock_sdr_device.sdr.set_center_freq.assert_called_with(new_freq)

    def test_set_frequency_not_connected(self):
        """Test setting frequency when not connected."""
        device = SDRDevice(device_index=0)
        result = device.set_frequency(104.1e6)
        
        assert result is False

    def test_set_gain(self, mock_sdr_device):
        """Test setting gain."""
        new_gain = 20.0
        result = mock_sdr_device.set_gain(new_gain)
        
        assert result is True
        assert mock_sdr_device.gain == new_gain
        mock_sdr_device.sdr.set_gain.assert_called_with(new_gain)

    def test_set_gain_auto(self, mock_sdr_device):
        """Test setting gain to auto."""
        result = mock_sdr_device.set_gain("auto")
        
        assert result is True
        assert mock_sdr_device.gain == "auto"

    def test_set_sample_rate(self, mock_sdr_device):
        """Test setting sample rate."""
        new_rate = 1.024e6
        result = mock_sdr_device.set_sample_rate(new_rate)
        
        assert result is True
        assert mock_sdr_device.sample_rate == new_rate
        mock_sdr_device.sdr.set_sample_rate.assert_called_with(new_rate)

    def test_set_bandwidth(self, mock_sdr_device):
        """Test setting bandwidth."""
        new_bw = 200e3
        result = mock_sdr_device.set_bandwidth(new_bw)
        
        assert result is True
        assert mock_sdr_device.bandwidth == new_bw
        mock_sdr_device.sdr.set_bandwidth.assert_called_with(new_bw)

    def test_set_mode(self, mock_sdr_device):
        """Test setting demodulation mode."""
        result = mock_sdr_device.set_mode("NFM")
        
        assert result is True
        assert mock_sdr_device.mode == "NFM"

    def test_set_mode_invalid(self, mock_sdr_device):
        """Test setting invalid mode."""
        original_mode = mock_sdr_device.mode
        result = mock_sdr_device.set_mode("INVALID")
        
        assert result is False
        assert mock_sdr_device.mode == original_mode

    def test_set_agc(self, mock_sdr_device):
        """Test setting AGC."""
        result = mock_sdr_device.set_agc(True)
        
        assert result is True
        assert mock_sdr_device.agc_enabled is True

    def test_read_samples(self, mock_sdr_device):
        """Test reading samples."""
        num_samples = 1024
        samples = mock_sdr_device.read_samples(num_samples)
        
        assert samples is not None
        assert len(samples) == num_samples
        assert isinstance(samples, np.ndarray)

    def test_read_samples_not_connected(self):
        """Test reading samples when not connected."""
        device = SDRDevice(device_index=0)
        samples = device.read_samples(1024)
        
        assert samples is None

    def test_get_device_info(self, mock_sdr_device):
        """Test getting device info."""
        info = mock_sdr_device.get_device_info()
        
        assert info["connected"] is True
        assert info["device_index"] == 0
        assert info["frequency"] == mock_sdr_device.frequency
        assert info["sample_rate"] == mock_sdr_device.sample_rate
        assert "capabilities" in info

    def test_get_device_info_not_connected(self):
        """Test getting device info when not connected."""
        device = SDRDevice(device_index=0)
        info = device.get_device_info()
        
        assert info["connected"] is False


@pytest.mark.unit
class TestSDRManager:
    """Test SDRManager class."""

    def test_init(self):
        """Test SDRManager initialization."""
        manager = SDRManager()
        
        assert len(manager.devices) == 0
        assert len(manager.available_devices) == 0

    def test_scan_devices(self):
        """Test device scanning."""
        with patch("backend.sdr_interface.RtlSdr") as mock_rtlsdr_class:
            mock_sdr = MagicMock()
            mock_rtlsdr_class.side_effect = [mock_sdr, Exception("No device")]
            
            manager = SDRManager()
            devices = manager.scan_devices()
            
            assert len(devices) == 1
            assert devices[0] == 0

    def test_scan_devices_no_library(self, monkeypatch):
        """Test scanning when pyrtlsdr is not available."""
        monkeypatch.setattr("backend.sdr_interface.RtlSdr", None)
        manager = SDRManager()
        devices = manager.scan_devices()
        
        assert devices == []

    def test_get_device(self):
        """Test getting a device instance."""
        manager = SDRManager()
        device = manager.get_device(0)
        
        assert device is not None
        assert isinstance(device, SDRDevice)
        assert device.device_index == 0

    def test_get_device_cached(self):
        """Test that device instances are cached."""
        manager = SDRManager()
        device1 = manager.get_device(0)
        device2 = manager.get_device(0)
        
        assert device1 is device2

    def test_connect_device(self, mock_rtlsdr):
        """Test connecting a device."""
        with patch("backend.sdr_interface.RtlSdr", return_value=mock_rtlsdr):
            manager = SDRManager()
            result = manager.connect_device(0)
            
            assert result is True
            assert 0 in manager.devices
            assert manager.devices[0].is_connected is True

    def test_disconnect_device(self, mock_sdr_device):
        """Test disconnecting a device."""
        manager = SDRManager()
        manager.devices[0] = mock_sdr_device
        
        manager.disconnect_device(0)
        
        assert mock_sdr_device.is_connected is False

    def test_disconnect_all(self, mock_sdr_device):
        """Test disconnecting all devices."""
        manager = SDRManager()
        manager.devices[0] = mock_sdr_device
        manager.devices[1] = SDRDevice(device_index=1)
        
        manager.disconnect_all()
        
        assert len(manager.devices) == 0

    def test_get_all_device_info(self, mock_sdr_device):
        """Test getting info for all devices."""
        manager = SDRManager()
        manager.devices[0] = mock_sdr_device
        
        info = manager.get_all_device_info()
        
        assert 0 in info
        assert info[0]["connected"] is True

