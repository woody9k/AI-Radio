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

            self.is_connected = True
            logger.info(f"Connected to RTL-SDR device {self.device_index}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to RTL-SDR device {self.device_index}: {e}")
            self.is_connected = False
            return False

    def disconnect(self):
        """Disconnect from the RTL-SDR device."""
        self.stop_streaming.set()

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
                    except:
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
            return {
                "connected": True,
                "device_index": self.device_index,
                "frequency": self.frequency,
                "sample_rate": self.sample_rate,
                "gain": self.gain,
                "bandwidth": self.bandwidth,
                "is_streaming": self.is_streaming,
                "queue_size": self.sample_queue.qsize(),
            }
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
            except:
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
