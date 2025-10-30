"""
RTL-SDR Interface Layer

Provides a high-level interface for RTL-SDR devices with error handling,
device detection, and thread-safe sample streaming.
"""

import logging
import threading
import time
from collections.abc import Callable
from queue import Empty, Queue
from typing import Any

import numpy as np

try:
    from rtlsdr import RtlSdr
except ImportError:
    RtlSdr = None
    logging.warning("pyrtlsdr not installed. SDR functionality will be limited.")

logger = logging.getLogger(__name__)


class SDRDevice:
    """High-level RTL-SDR device interface with error handling and streaming."""

    def __init__(self, device_index: int = 0):
        self.device_index = device_index
        self.sdr: RtlSdr | None = None
        self.is_connected: bool = False
        self.is_streaming: bool = False

        # Streaming configuration
        self.sample_queue: Queue[np.ndarray] = Queue(maxsize=10)
        self.streaming_thread: threading.Thread | None = None
        self.stop_stream_event = threading.Event()

        # Device parameters
        self.frequency: float = 100e6  # 100 MHz default
        self.sample_rate: float = 2.048e6  # 2.048 MS/s default
        self.gain: float | str = "auto"
        self.bandwidth: float | None = None  # Auto bandwidth
        self.mode: str = "WFM"  # Demodulation mode: WFM, NFM, AM, SSB
        self.agc_enabled: bool = False  # Automatic Gain Control
        self.bias_t: bool = False  # Bias-T power (for active antennas)
        self.device_capabilities: dict[str, Any] = {}  # Device-specific capabilities

        # Callbacks
        self.data_callback: Callable[[np.ndarray], None] | None = None

    def connect(self) -> bool:
        """Connect to the RTL-SDR device."""
        if RtlSdr is None:
            logger.error("pyrtlsdr library not available")
            return False

        try:
            self.sdr = RtlSdr(device_index=self.device_index)
            self.sdr.set_sample_rate(self.sample_rate)
            self.sdr.set_center_freq(self.frequency)
            self.sdr.set_gain(self.gain)

            if self.bandwidth:
                self.sdr.set_bandwidth(self.bandwidth)

            # Check device capabilities
            self._check_device_capabilities()

            self.is_connected = True
            logger.info(f"Connected to RTL-SDR device {self.device_index}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to RTL-SDR device {self.device_index}: {e}")
            self.is_connected = False
            return False

    def disconnect(self):
        """Disconnect from the RTL-SDR device."""
        self.stop_stream()

        if self.streaming_thread and self.streaming_thread.is_alive():
            self.streaming_thread.join(timeout=2.0)

        if self.sdr:
            try:
                self.sdr.close()
            except Exception as e:
                logger.warning(f"Error closing SDR device: {e}")
            finally:
                self.sdr = None

        self.is_connected = False
        self.is_streaming = False
        logger.info("Disconnected from RTL-SDR device")

    def set_frequency(self, frequency: float) -> bool:
        """Set the center frequency in Hz."""
        if not self.is_connected or not self.sdr:
            logger.warning("Device not connected")
            return False

        try:
            self.sdr.set_center_freq(frequency)
            self.frequency = frequency
            logger.debug(f"Frequency set to {frequency/1e6:.3f} MHz")
            return True
        except Exception as e:
            logger.error(f"Failed to set frequency: {e}")
            return False

    def set_gain(self, gain) -> bool:
        """Set the gain. Can be 'auto', a number, or a string like 'auto'."""
        if not self.is_connected or not self.sdr:
            logger.warning("Device not connected")
            return False

        try:
            self.sdr.set_gain(gain)
            self.gain = gain
            logger.debug(f"Gain set to {gain}")
            return True
        except Exception as e:
            logger.error(f"Failed to set gain: {e}")
            return False

    def set_sample_rate(self, sample_rate: float) -> bool:
        """Set the sample rate in Hz."""
        if not self.is_connected or not self.sdr:
            logger.warning("Device not connected")
            return False

        try:
            self.sdr.set_sample_rate(sample_rate)
            self.sample_rate = sample_rate
            logger.debug(f"Sample rate set to {sample_rate/1e6:.3f} MS/s")
            return True
        except Exception as e:
            logger.error(f"Failed to set sample rate: {e}")
            return False

    def set_bandwidth(self, bandwidth: float) -> bool:
        """Set the bandwidth in Hz."""
        if not self.is_connected or not self.sdr:
            logger.warning("Device not connected")
            return False

        try:
            self.sdr.set_bandwidth(bandwidth)
            self.bandwidth = bandwidth
            logger.debug(f"Bandwidth set to {bandwidth/1e6:.3f} MHz")
            return True
        except Exception as e:
            logger.error(f"Failed to set bandwidth: {e}")
            return False

    def set_mode(self, mode: str) -> bool:
        """Set the demodulation mode (WFM, NFM, AM, SSB)."""
        valid_modes = ["WFM", "NFM", "AM", "SSB"]
        mode = mode.upper()
        if mode not in valid_modes:
            logger.warning(f"Invalid mode: {mode}, must be one of {valid_modes}")
            return False

        self.mode = mode
        logger.debug(f"Mode set to {mode}")
        return True

    def set_agc(self, enabled: bool) -> bool:
        """Enable or disable Automatic Gain Control."""
        self.agc_enabled = enabled
        if enabled and isinstance(self.gain, (int, float)):
            # When AGC is enabled, we typically use auto gain
            # Store the manual gain value for when AGC is disabled
            if not hasattr(self, "_manual_gain"):
                self._manual_gain = self.gain
            self.set_gain("auto")
        elif not enabled and hasattr(self, "_manual_gain"):
            # Restore manual gain when disabling AGC
            self.set_gain(self._manual_gain)

        logger.debug(f"AGC {'enabled' if enabled else 'disabled'}")
        return True

    def set_bias_t(self, enabled: bool) -> bool:
        """Enable or disable bias-T power (for active antennas). Only works on RTL-SDR Blog V4."""
        if not self.is_connected or not self.sdr:
            logger.warning("Device not connected")
            return False

        # Check if device supports bias-T
        if not self.device_capabilities.get("bias_t", False):
            logger.warning("Device does not support bias-T")
            return False

        try:
            # RTL-SDR Blog V4 has bias-T support via set_bias_tee
            if hasattr(self.sdr, "set_bias_tee"):
                self.sdr.set_bias_tee(enabled)
                self.bias_t = enabled
                logger.debug(f"Bias-T {'enabled' if enabled else 'disabled'}")
                return True
            else:
                logger.warning("Device API does not support bias-T control")
                return False
        except Exception as e:
            logger.error(f"Failed to set bias-T: {e}")
            return False

    def _check_device_capabilities(self):
        """Check device-specific capabilities (e.g., RTL-SDR Blog V4 features)."""
        if not self.sdr:
            return

        self.device_capabilities = {"bias_t": False, "device_type": "unknown"}

        try:
            # Check for RTL-SDR Blog V4 (has bias-T support)
            # We can detect this by checking if set_bias_tee method exists
            if hasattr(self.sdr, "set_bias_tee"):
                self.device_capabilities["bias_t"] = True
                self.device_capabilities["device_type"] = "rtl_blog_v4"
                logger.info("RTL-SDR Blog V4 detected - bias-T supported")
            else:
                # Try to get device info to identify
                device_info = self.get_device_info()
                if "rtlsdrblog" in str(device_info).lower() or "blog" in str(device_info).lower():
                    self.device_capabilities["device_type"] = "rtl_blog"
        except Exception as e:
            logger.debug(f"Could not determine device capabilities: {e}")

    def read_samples(self, num_samples: int) -> np.ndarray | None:
        """Read a single batch of samples."""
        if not self.is_connected or not self.sdr:
            logger.warning("Device not connected")
            return None

        try:
            samples = self.sdr.read_samples(num_samples)
            return samples
        except Exception as e:
            logger.error(f"Failed to read samples: {e}")
            return None

    def start_streaming(self, num_samples: int = 1024, callback: Callable | None = None):
        """Start continuous sample streaming in a separate thread."""
        if not self.is_connected or not self.sdr:
            logger.warning("Device not connected")
            return False

        if self.is_streaming:
            logger.warning("Already streaming")
            return False

        self.data_callback = callback
        self.stop_stream_event.clear()
        self.streaming_thread = threading.Thread(
            target=self._streaming_worker, args=(num_samples,), daemon=True
        )
        self.streaming_thread.start()
        self.is_streaming = True
        logger.info("Started streaming")
        return True

    def stop_stream(self):
        """Stop the streaming thread."""
        if not self.is_streaming:
            return

        self.stop_stream_event.set()
        if self.streaming_thread and self.streaming_thread.is_alive():
            self.streaming_thread.join(timeout=2.0)

        self.is_streaming = False
        logger.info("Stopped streaming")

    def _streaming_worker(self, num_samples: int):
        """Worker thread for continuous streaming."""
        while not self.stop_stream_event.is_set():
            try:
                samples = self.read_samples(num_samples)
                if samples is not None:
                    # Add to queue for processing
                    try:
                        self.sample_queue.put_nowait(samples)
                    except Exception:
                        # Queue full, skip this sample
                        pass

                    # Call callback if provided
                    if self.data_callback:
                        try:
                            self.data_callback(samples)
                        except Exception as e:
                            logger.error(f"Error in data callback: {e}")

            except Exception as e:
                logger.error(f"Error in streaming worker: {e}")
                break

            # Small delay to prevent overwhelming the system
            time.sleep(0.001)

    def get_queue_samples(self, timeout: float = 0.1) -> np.ndarray | None:
        """Get samples from the streaming queue."""
        try:
            return self.sample_queue.get(timeout=timeout)
        except Empty:
            return None

    def get_device_info(self) -> dict[str, Any]:
        """Get information about the connected device."""
        if not self.is_connected or not self.sdr:
            return {"connected": False}

        try:
            info = {
                "connected": True,
                "device_index": self.device_index,
                "frequency": self.frequency,
                "sample_rate": self.sample_rate,
                "gain": self.gain,
                "bandwidth": self.bandwidth,
                "mode": self.mode,
                "agc_enabled": self.agc_enabled,
                "bias_t": self.bias_t,
                "is_streaming": self.is_streaming,
                "queue_size": self.sample_queue.qsize(),
                "capabilities": self.device_capabilities,
            }
            return info
        except Exception as e:
            logger.error(f"Error getting device info: {e}")
            return {"connected": False, "error": str(e)}


class SDRManager:
    """Manager class for handling multiple RTL-SDR devices."""

    def __init__(self):
        self.devices: dict[int, SDRDevice] = {}
        self.available_devices: list[int] = []

    def scan_devices(self) -> list[int]:
        """Scan for available RTL-SDR devices."""
        if RtlSdr is None:
            logger.warning("pyrtlsdr library not available")
            return []

        available = []
        for i in range(10):  # Check first 10 device indices
            try:
                sdr = RtlSdr(device_index=i)
                sdr.close()
                available.append(i)
            except Exception:
                continue

        self.available_devices = available
        logger.info(f"Found {len(available)} RTL-SDR devices: {available}")
        return available

    def get_device(self, device_index: int = 0) -> SDRDevice | None:
        """Get or create a device instance."""
        if device_index not in self.devices:
            self.devices[device_index] = SDRDevice(device_index)

        return self.devices[device_index]

    def connect_device(self, device_index: int = 0) -> bool:
        """Connect to a specific device."""
        device = self.get_device(device_index)
        if device:
            return device.connect()
        return False

    def disconnect_device(self, device_index: int = 0):
        """Disconnect a specific device."""
        if device_index in self.devices:
            self.devices[device_index].disconnect()

    def disconnect_all(self):
        """Disconnect all devices."""
        for device in self.devices.values():
            device.disconnect()
        self.devices.clear()

    def get_all_device_info(self) -> dict[int, dict[str, Any]]:
        """Get information about all devices."""
        return {idx: device.get_device_info() for idx, device in self.devices.items()}


# Global SDR manager instance
sdr_manager = SDRManager()
