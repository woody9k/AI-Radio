"""IQ sample recording and playback manager."""

import json
import logging
import os
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class RecordingMetadata:
    """Metadata for a recording."""

    filename: str
    frequency: float
    sample_rate: float
    gain: str
    mode: str
    start_time: str
    duration: float
    num_samples: int
    file_size: int
    description: str | None = None


class RecordingManager:
    """Manages IQ sample recording and playback."""

    def __init__(self, recordings_dir: str = "data/recordings"):
        """
        Initialize recording manager.

        Args:
            recordings_dir: Directory to store recordings
        """
        self.recordings_dir = Path(recordings_dir)
        self.recordings_dir.mkdir(parents=True, exist_ok=True)

        self.is_recording = False
        self.recording_thread: threading.Thread | None = None
        self.stop_recording_event = threading.Event()
        self.recording_file = None
        self.recording_metadata: RecordingMetadata | None = None
        self.samples_written = 0
        self.start_time: float | None = None

    def start_recording(
        self,
        frequency: float,
        sample_rate: float,
        gain: str,
        mode: str,
        description: str | None = None,
    ) -> dict[str, Any]:
        """
        Start recording IQ samples.

        Args:
            frequency: Center frequency in Hz
            sample_rate: Sample rate in Hz
            gain: Gain setting
            mode: Demodulation mode
            description: Optional description

        Returns:
            Recording metadata
        """
        if self.is_recording:
            return {"success": False, "error": "Already recording"}

        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"recording_{timestamp}.iq"
        filepath = self.recordings_dir / filename

        try:
            self.recording_file = open(filepath, "wb")
            self.start_time = time.time()
            self.samples_written = 0

            self.recording_metadata = RecordingMetadata(
                filename=filename,
                frequency=frequency,
                sample_rate=sample_rate,
                gain=gain,
                mode=mode,
                start_time=datetime.now().isoformat(),
                duration=0.0,
                num_samples=0,
                file_size=0,
                description=description,
            )

            self.is_recording = True
            self.stop_recording_event.clear()

            logger.info(f"Started recording to {filename}")
            return {"success": True, "filename": filename, "metadata": asdict(self.recording_metadata)}

        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            if self.recording_file:
                self.recording_file.close()
                self.recording_file = None
            return {"success": False, "error": str(e)}

    def write_samples(self, samples: np.ndarray):
        """
        Write samples to the recording file.

        Args:
            samples: IQ samples to write
        """
        if not self.is_recording or not self.recording_file:
            return

        try:
            # Write samples as binary (complex64)
            samples.astype(np.complex64).tofile(self.recording_file)
            self.samples_written += len(samples)
        except Exception as e:
            logger.error(f"Error writing samples: {e}")

    def stop_recording(self) -> dict[str, Any]:
        """
        Stop recording and save metadata.

        Returns:
            Final recording metadata
        """
        if not self.is_recording:
            return {"success": False, "error": "Not recording"}

        self.is_recording = False
        self.stop_recording_event.set()

        if self.recording_file:
            try:
                self.recording_file.close()
                filepath = self.recordings_dir / self.recording_metadata.filename
                file_size = filepath.stat().st_size

                # Update metadata
                duration = time.time() - self.start_time if self.start_time else 0.0
                self.recording_metadata.duration = duration
                self.recording_metadata.num_samples = self.samples_written
                self.recording_metadata.file_size = file_size

                # Save metadata JSON
                metadata_file = self.recordings_dir / f"{self.recording_metadata.filename}.json"
                with open(metadata_file, "w") as f:
                    json.dump(asdict(self.recording_metadata), f, indent=2)

                logger.info(f"Stopped recording: {self.recording_metadata.filename}")
                result = {"success": True, "metadata": asdict(self.recording_metadata)}
                self.recording_file = None
                self.recording_metadata = None
                return result

            except Exception as e:
                logger.error(f"Error stopping recording: {e}")
                return {"success": False, "error": str(e)}

        return {"success": False, "error": "No recording file"}

    def list_recordings(self) -> list[dict[str, Any]]:
        """
        List all available recordings.

        Returns:
            List of recording metadata
        """
        recordings = []

        for json_file in self.recordings_dir.glob("*.json"):
            try:
                with open(json_file, "r") as f:
                    metadata = json.load(f)
                    recordings.append(metadata)
            except Exception as e:
                logger.warning(f"Error reading metadata {json_file}: {e}")

        # Sort by start time (newest first)
        recordings.sort(key=lambda x: x.get("start_time", ""), reverse=True)
        return recordings

    def get_recording(self, filename: str) -> dict[str, Any] | None:
        """
        Get metadata for a specific recording.

        Args:
            filename: Recording filename

        Returns:
            Recording metadata or None
        """
        metadata_file = self.recordings_dir / f"{filename}.json"
        if not metadata_file.exists():
            return None

        try:
            with open(metadata_file, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading metadata: {e}")
            return None

    def delete_recording(self, filename: str) -> dict[str, Any]:
        """
        Delete a recording and its metadata.

        Args:
            filename: Recording filename

        Returns:
            Success status
        """
        try:
            iq_file = self.recordings_dir / filename
            json_file = self.recordings_dir / f"{filename}.json"

            if iq_file.exists():
                iq_file.unlink()
            if json_file.exists():
                json_file.unlink()

            logger.info(f"Deleted recording: {filename}")
            return {"success": True}

        except Exception as e:
            logger.error(f"Error deleting recording: {e}")
            return {"success": False, "error": str(e)}

    def read_recording(
        self, filename: str, start_sample: int = 0, num_samples: int | None = None
    ) -> tuple[np.ndarray, dict[str, Any]] | None:
        """
        Read samples from a recording file.

        Args:
            filename: Recording filename
            start_sample: Starting sample index
            num_samples: Number of samples to read (None = all remaining)

        Returns:
            Tuple of (samples, metadata) or None
        """
        filepath = self.recordings_dir / filename
        if not filepath.exists():
            logger.error(f"Recording file not found: {filename}")
            return None

        metadata = self.get_recording(filename)
        if not metadata:
            logger.error(f"Metadata not found for: {filename}")
            return None

        try:
            # Read samples as complex64
            samples = np.fromfile(filepath, dtype=np.complex64)

            # Apply range if specified
            if start_sample > 0:
                samples = samples[start_sample:]
            if num_samples is not None:
                samples = samples[:num_samples]

            return samples, metadata

        except Exception as e:
            logger.error(f"Error reading recording: {e}")
            return None

    def get_recording_status(self) -> dict[str, Any]:
        """
        Get current recording status.

        Returns:
            Recording status
        """
        if not self.is_recording:
            return {"is_recording": False}

        duration = time.time() - self.start_time if self.start_time else 0.0
        return {
            "is_recording": True,
            "filename": self.recording_metadata.filename if self.recording_metadata else None,
            "duration": duration,
            "samples_written": self.samples_written,
            "frequency": self.recording_metadata.frequency if self.recording_metadata else None,
        }


# Global recording manager instance
recording_manager = RecordingManager()

