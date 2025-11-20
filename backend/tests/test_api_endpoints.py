"""Integration tests for Flask API endpoints."""

import json
from unittest.mock import MagicMock, patch

import pytest

from backend.app import app


@pytest.fixture
def client():
    """Create a test client for the Flask app."""
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def mock_device():
    """Create a mock SDR device."""
    device = MagicMock()
    device.is_connected = True
    device.frequency = 100e6
    device.sample_rate = 2.048e6
    device.gain = "auto"
    device.get_device_info.return_value = {
        "connected": True,
        "frequency": 100e6,
        "sample_rate": 2.048e6,
        "gain": "auto",
    }
    return device


@pytest.mark.integration
class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/api/health")
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert "device_connected" in data
        assert "streaming" in data
        assert "timestamp" in data


@pytest.mark.integration
class TestDevicesEndpoint:
    """Test device management endpoints."""

    @patch("backend.app.sdr_manager")
    def test_get_devices(self, mock_manager, client):
        """Test getting list of devices."""
        mock_manager.scan_devices.return_value = [0, 1]
        mock_manager.get_all_device_info.return_value = {
            0: {"connected": False},
            1: {"connected": True},
        }
        
        response = client.get("/api/devices")
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert "devices" in data
        assert "device_info" in data

    @patch("backend.app.sdr_manager")
    @patch("backend.app.current_device", new_callable=lambda: None)
    def test_connect_device(self, mock_device, mock_manager, client, mock_device_instance):
        """Test connecting to a device."""
        mock_manager.connect_device.return_value = True
        mock_manager.get_device.return_value = mock_device_instance
        
        response = client.post("/api/devices/0/connect")
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True

    @patch("backend.app.current_device")
    def test_disconnect_device(self, mock_device, client):
        """Test disconnecting a device."""
        mock_device.disconnect = MagicMock()
        
        response = client.post("/api/devices/0/disconnect")
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True


@pytest.mark.integration
class TestSettingsEndpoint:
    """Test settings endpoints."""

    @patch("backend.app.current_device", new_callable=lambda: None)
    def test_get_settings_no_device(self, mock_device, client):
        """Test getting settings when no device is connected."""
        response = client.get("/api/settings")
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["success"] is False

    @patch("backend.app.current_device")
    def test_get_settings(self, mock_device, client, mock_device):
        """Test getting device settings."""
        mock_device.is_connected = True
        mock_device.get_device_info.return_value = {
            "frequency": 100e6,
            "sample_rate": 2.048e6,
            "gain": "auto",
        }
        
        response = client.get("/api/settings")
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert "settings" in data

    @patch("backend.app.current_device")
    def test_update_settings(self, mock_device, client, mock_device):
        """Test updating device settings."""
        mock_device.is_connected = True
        mock_device.set_frequency.return_value = True
        mock_device.set_sample_rate.return_value = True
        mock_device.set_gain.return_value = True
        mock_device.get_device_info.return_value = {
            "frequency": 104.1e6,
            "sample_rate": 2.048e6,
            "gain": "auto",
        }
        
        response = client.post(
            "/api/settings",
            json={"frequency": 104.1e6, "sample_rate": 2.048e6},
            content_type="application/json",
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True


@pytest.mark.integration
class TestStreamingEndpoint:
    """Test streaming endpoints."""

    @patch("backend.app.current_device", new_callable=lambda: None)
    def test_start_streaming_no_device(self, mock_device, client):
        """Test starting stream when no device is connected."""
        response = client.post("/api/stream/start")
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["success"] is False

    @patch("backend.app.current_device")
    @patch("backend.app.streaming_active", False)
    @patch("backend.app.streaming_thread", None)
    def test_start_streaming(self, mock_thread, mock_active, mock_device, client, mock_device):
        """Test starting streaming."""
        mock_device.is_connected = True
        
        response = client.post("/api/stream/start")
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True

    @patch("backend.app.streaming_active", True)
    def test_stop_streaming(self, client):
        """Test stopping streaming."""
        response = client.post("/api/stream/stop")
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True


@pytest.mark.integration
class TestSpectrumEndpoint:
    """Test spectrum endpoints."""

    @patch("backend.app.current_device", new_callable=lambda: None)
    def test_get_spectrum_no_device(self, mock_device, client):
        """Test getting spectrum when no device is connected."""
        response = client.get("/api/spectrum")
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["success"] is False

    @patch("backend.app.current_device")
    @patch("backend.app.signal_processor")
    def test_get_spectrum(self, mock_processor, mock_device, client, mock_device):
        """Test getting spectrum data."""
        import numpy as np
        
        mock_device.is_connected = True
        mock_device.read_samples.return_value = np.random.randn(1024) + 1j * np.random.randn(1024)
        mock_device.frequency = 100e6
        mock_device.sample_rate = 2.048e6
        
        mock_processor.fft_size = 1024
        mock_processor.compute_fft.return_value = (
            np.linspace(-1e6, 1e6, 1024),
            np.random.randn(1024) * 10 - 80,
        )
        mock_processor.detect_signals.return_value = []
        mock_processor.extract_features.return_value = {}
        mock_processor.get_frequency_resolution.return_value = 2000.0
        
        response = client.get("/api/spectrum")
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert "frequencies" in data
        assert "spectrum" in data


@pytest.mark.integration
class TestPresetsEndpoint:
    """Test presets endpoints."""

    @patch("backend.app.preset_manager")
    def test_get_presets(self, mock_manager, client):
        """Test getting presets."""
        from backend.presets import Preset
        
        mock_presets = [
            Preset(
                name="FM Radio",
                description="FM Broadcast",
                frequency=104.1e6,
                sample_rate=2.048e6,
                gain="auto",
            )
        ]
        mock_manager.get_presets_by_category.return_value = mock_presets
        mock_manager.get_categories.return_value = ["Broadcast"]
        
        response = client.get("/api/presets")
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert "presets" in data
        assert "categories" in data

    @patch("backend.app.current_device")
    @patch("backend.app.preset_manager")
    def test_apply_preset(self, mock_manager, mock_device, client, mock_device):
        """Test applying a preset."""
        from backend.presets import Preset
        
        mock_device.is_connected = True
        mock_device.set_frequency.return_value = True
        mock_device.set_sample_rate.return_value = True
        mock_device.set_gain.return_value = True
        
        preset = Preset(
            name="FM Radio",
            description="FM Broadcast",
            frequency=104.1e6,
            sample_rate=2.048e6,
            gain="auto",
        )
        mock_manager.get_preset.return_value = preset
        
        response = client.post("/api/presets/FM Radio/apply")
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert "preset" in data


@pytest.mark.integration
class TestAISettingsEndpoint:
    """Test AI settings endpoints."""

    @patch("backend.app.get_settings")
    def test_get_ai_settings(self, mock_get_settings, client):
        """Test getting AI settings."""
        mock_get_settings.return_value = {
            "openai_api_key": "test-key",
            "openai_model": "gpt-4o-mini",
        }
        
        response = client.get("/api/settings/ai")
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert "settings" in data
        # API key should be masked
        assert data["settings"]["openai_api_key"] == "****"

    @patch("backend.app.update_settings")
    def test_update_ai_settings(self, mock_update_settings, client):
        """Test updating AI settings."""
        mock_update_settings.return_value = {
            "openai_api_key": "new-key",
            "openai_model": "gpt-4o-mini",
        }
        
        response = client.post(
            "/api/settings/ai",
            json={"openai_api_key": "new-key", "openai_model": "gpt-4o-mini"},
            content_type="application/json",
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True

