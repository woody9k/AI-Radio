"""
Data Collection and Feature Extraction

Handles background data collection during normal operation, feature extraction
from signal data, and dataset management for machine learning training.
"""

import json
import logging
import os
import threading
import time
from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

import numpy as np
from scipy.fft import dct

logger = logging.getLogger(__name__)


@dataclass
class SignalSample:
    """Represents a single signal sample with metadata."""

    timestamp: str
    frequency: float
    sample_rate: float
    gain: str
    samples: np.ndarray
    spectrum: np.ndarray
    features: dict[str, float]
    signals_detected: list[dict[str, Any]]
    label: str | None = None
    confidence: float | None = None
    category: str | None = None  # 'aviation', 'fm_radio', etc.
    modulation: str | None = None  # 'AM', 'FM', 'SSB'


@dataclass
class TrainingDataset:
    """Represents a training dataset for ML models."""

    name: str
    description: str
    created_at: str
    samples: list[SignalSample]
    categories: list[str]
    total_samples: int


class FeatureExtractor:
    """Extracts features from signal data for ML training."""

    def __init__(self):
        self.feature_names = [
            "mean_power",
            "std_power",
            "max_power",
            "min_power",
            "spectral_centroid",
            "spectral_bandwidth",
            "spectral_rolloff",
            "zero_crossing_rate",
            "mfcc_1",
            "mfcc_2",
            "mfcc_3",
            "spectral_contrast",
            "tonnetz_1",
            "tonnetz_2",
            "chroma_1",
            "chroma_2",
            "chroma_3",
            "chroma_4",
            "rms_energy",
            "spectral_flatness",
            "spectral_rolloff",
        ]

    def extract_features(
        self, samples: np.ndarray, spectrum: np.ndarray, sample_rate: float
    ) -> dict[str, float]:
        """Extract comprehensive features from signal data."""
        features = {}

        # Time domain features
        features.update(self._extract_time_domain_features(samples))

        # Frequency domain features
        features.update(self._extract_frequency_domain_features(spectrum, sample_rate))

        # Spectral features
        features.update(self._extract_spectral_features(spectrum))

        # Statistical features
        features.update(self._extract_statistical_features(samples, spectrum))

        return features

    def _extract_time_domain_features(self, samples: np.ndarray) -> dict[str, float]:
        """Extract time domain features."""
        features = {}

        # Basic statistics
        features["mean_power"] = float(np.mean(np.abs(samples) ** 2))
        features["std_power"] = float(np.std(np.abs(samples) ** 2))
        features["max_power"] = float(np.max(np.abs(samples) ** 2))
        features["min_power"] = float(np.min(np.abs(samples) ** 2))

        # RMS energy
        features["rms_energy"] = float(np.sqrt(np.mean(np.abs(samples) ** 2)))

        # Zero crossing rate
        zero_crossings = np.sum(np.diff(np.sign(samples)) != 0)
        features["zero_crossing_rate"] = float(zero_crossings / len(samples))

        return features

    def _extract_frequency_domain_features(
        self, spectrum: np.ndarray, sample_rate: float
    ) -> dict[str, float]:
        """Extract frequency domain features."""
        features = {}

        # Convert to power spectrum
        power_spectrum = np.abs(spectrum) ** 2
        freqs = np.linspace(0, sample_rate / 2, len(power_spectrum))

        # Spectral centroid
        features["spectral_centroid"] = float(
            np.sum(freqs * power_spectrum) / np.sum(power_spectrum)
        )

        # Spectral bandwidth
        centroid = features["spectral_centroid"]
        features["spectral_bandwidth"] = float(
            np.sqrt(np.sum(((freqs - centroid) ** 2) * power_spectrum) / np.sum(power_spectrum))
        )

        # Spectral rolloff (95% of energy)
        cumsum = np.cumsum(power_spectrum)
        rolloff_idx = np.where(cumsum >= 0.95 * cumsum[-1])[0]
        if len(rolloff_idx) > 0:
            features["spectral_rolloff"] = float(freqs[rolloff_idx[0]])
        else:
            features["spectral_rolloff"] = float(freqs[-1])

        # Spectral flatness
        geometric_mean = np.exp(np.mean(np.log(power_spectrum + 1e-12)))
        arithmetic_mean = np.mean(power_spectrum)
        features["spectral_flatness"] = float(geometric_mean / (arithmetic_mean + 1e-12))

        return features

    def _extract_spectral_features(self, spectrum: np.ndarray) -> dict[str, float]:
        """Extract spectral features."""
        features = {}

        # MFCC-like features (simplified)
        power_spectrum = np.abs(spectrum) ** 2

        # Mel-frequency cepstral coefficients (simplified)
        mel_filters = self._create_mel_filters(len(power_spectrum), 13)
        mel_spectrum = np.dot(mel_filters, power_spectrum)
        log_mel_spectrum = np.log(mel_spectrum + 1e-12)

        # DCT to get MFCCs
        mfccs = dct(log_mel_spectrum, norm="ortho")
        features["mfcc_1"] = float(mfccs[1] if len(mfccs) > 1 else 0)
        features["mfcc_2"] = float(mfccs[2] if len(mfccs) > 2 else 0)
        features["mfcc_3"] = float(mfccs[3] if len(mfccs) > 3 else 0)

        # Chroma features (simplified)
        chroma = self._extract_chroma_features(power_spectrum)
        features["chroma_1"] = float(chroma[0] if len(chroma) > 0 else 0)
        features["chroma_2"] = float(chroma[1] if len(chroma) > 1 else 0)
        features["chroma_3"] = float(chroma[2] if len(chroma) > 2 else 0)
        features["chroma_4"] = float(chroma[3] if len(chroma) > 3 else 0)

        # Tonnetz features (simplified)
        tonnetz = self._extract_tonnetz_features(chroma)
        features["tonnetz_1"] = float(tonnetz[0] if len(tonnetz) > 0 else 0)
        features["tonnetz_2"] = float(tonnetz[1] if len(tonnetz) > 1 else 0)

        # Spectral contrast
        features["spectral_contrast"] = float(self._extract_spectral_contrast(power_spectrum))

        return features

    def _extract_statistical_features(
        self, samples: np.ndarray, spectrum: np.ndarray
    ) -> dict[str, float]:
        """Extract statistical features."""
        features = {}

        # Kurtosis and skewness (use magnitude to avoid complex warnings)
        magnitude = np.abs(samples)
        features["kurtosis"] = float(self._kurtosis(magnitude))
        features["skewness"] = float(self._skewness(magnitude))

        # Peak-to-average ratio
        features["peak_to_avg_ratio"] = float(np.max(magnitude) / (np.mean(magnitude) + 1e-12))

        # Crest factor
        features["crest_factor"] = float(
            np.max(magnitude) / (np.sqrt(np.mean(magnitude**2)) + 1e-12)
        )

        return features

    def _create_mel_filters(self, n_fft: int, n_mels: int) -> np.ndarray:
        """Create mel filter bank."""
        # Simplified mel filter bank
        filters = np.zeros((n_mels, n_fft))
        mel_points = np.linspace(0, n_fft // 2, n_mels + 2)

        for i in range(1, n_mels + 1):
            left = int(mel_points[i - 1])
            center = int(mel_points[i])
            right = int(mel_points[i + 1])

            # Rising edge
            filters[i - 1, left:center] = np.linspace(0, 1, center - left)
            # Falling edge
            filters[i - 1, center:right] = np.linspace(1, 0, right - center)

        return filters

    def _extract_chroma_features(self, power_spectrum: np.ndarray) -> np.ndarray:
        """Extract chroma features."""
        # Simplified chroma extraction
        n_chroma = 12
        chroma = np.zeros(n_chroma)

        # Group frequency bins into chroma bins
        for i in range(len(power_spectrum)):
            chroma_bin = i % n_chroma
            chroma[chroma_bin] += power_spectrum[i]

        # Normalize
        chroma = chroma / (np.sum(chroma) + 1e-12)

        return chroma

    def _extract_tonnetz_features(self, chroma: np.ndarray) -> np.ndarray:
        """Extract tonnetz features."""
        # Simplified tonnetz extraction
        tonnetz = np.zeros(6)

        if len(chroma) >= 12:
            # Major thirds
            tonnetz[0] = chroma[0] - chroma[4]  # C - E
            tonnetz[1] = chroma[7] - chroma[11]  # G - B

            # Minor thirds
            tonnetz[2] = chroma[0] - chroma[3]  # C - Eb
            tonnetz[3] = chroma[7] - chroma[10]  # G - Bb

            # Perfect fifths
            tonnetz[4] = chroma[0] - chroma[7]  # C - G
            tonnetz[5] = chroma[2] - chroma[9]  # D - A

        return tonnetz

    def _extract_spectral_contrast(self, power_spectrum: np.ndarray) -> float:
        """Extract spectral contrast."""
        # Divide spectrum into sub-bands and compute contrast
        n_bands = 6
        band_size = len(power_spectrum) // n_bands

        contrasts = []
        for i in range(n_bands):
            start = i * band_size
            end = start + band_size
            band = power_spectrum[start:end]

            if len(band) > 0:
                peak = np.max(band)
                valley = np.min(band)
                contrast = peak / (valley + 1e-12)
                contrasts.append(contrast)

        return np.mean(contrasts) if contrasts else 0

    def _kurtosis(self, x: np.ndarray) -> float:
        """Calculate kurtosis."""
        mean = np.mean(x)
        std = np.std(x)
        if std == 0:
            return 0
        return np.mean(((x - mean) / std) ** 4) - 3

    def _skewness(self, x: np.ndarray) -> float:
        """Calculate skewness."""
        mean = np.mean(x)
        std = np.std(x)
        if std == 0:
            return 0
        return np.mean(((x - mean) / std) ** 3)


class DataCollector:
    """Collects and manages signal data for ML training."""

    def __init__(self, data_dir: str = "data", max_samples: int = 10000):
        self.data_dir = data_dir
        self.max_samples = max_samples
        self.samples_buffer: deque[SignalSample] = deque(maxlen=max_samples)
        self.feature_extractor = FeatureExtractor()
        self.collecting = False
        self.collection_thread = None
        self.lock = threading.Lock()

        # Create data directory
        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(os.path.join(data_dir, "samples"), exist_ok=True)
        os.makedirs(os.path.join(data_dir, "datasets"), exist_ok=True)

        # Load existing samples
        self._load_existing_samples()

    def start_collection(self):
        """Start background data collection."""
        if not self.collecting:
            self.collecting = True
            self.collection_thread = threading.Thread(target=self._collection_worker, daemon=True)
            self.collection_thread.start()
            logger.info("Started data collection")

    def stop_collection(self):
        """Stop background data collection."""
        self.collecting = False
        if self.collection_thread:
            self.collection_thread.join(timeout=2.0)
        logger.info("Stopped data collection")

    def add_sample(
        self,
        samples: np.ndarray,
        spectrum: np.ndarray,
        frequency: float,
        sample_rate: float,
        gain: str,
        signals_detected: list[dict[str, Any]] | None = None,
    ):
        """Add a new signal sample to the collection."""
        if not self.collecting:
            return

        try:
            # Extract features
            features = self.feature_extractor.extract_features(samples, spectrum, sample_rate)

            # Create sample object
            sample = SignalSample(
                timestamp=datetime.now().isoformat(),
                frequency=frequency,
                sample_rate=sample_rate,
                gain=gain,
                samples=samples.copy(),
                spectrum=spectrum.copy(),
                features=features,
                signals_detected=signals_detected or [],
            )

            # Add to buffer
            with self.lock:
                self.samples_buffer.append(sample)

            # Periodically save to disk
            if len(self.samples_buffer) % 100 == 0:
                self._save_samples()

        except Exception as e:
            logger.error(f"Error adding sample: {e}")

    def _collection_worker(self):
        """Background worker for data collection."""
        while self.collecting:
            time.sleep(1.0)  # Check every second

    def _load_existing_samples(self):
        """Load existing samples from disk."""
        samples_file = os.path.join(self.data_dir, "samples", "samples.json")
        if os.path.exists(samples_file):
            try:
                with open(samples_file) as f:
                    data = json.load(f)

                for sample_data in data.get("samples", []):
                    sample = SignalSample(
                        timestamp=sample_data["timestamp"],
                        frequency=sample_data["frequency"],
                        sample_rate=sample_data["sample_rate"],
                        gain=sample_data["gain"],
                        samples=np.array(sample_data["samples"]),
                        spectrum=np.array(sample_data["spectrum"]),
                        features=sample_data["features"],
                        signals_detected=sample_data.get("signals_detected", []),
                        label=sample_data.get("label"),
                        confidence=sample_data.get("confidence"),
                    )
                    self.samples_buffer.append(sample)

                logger.info(f"Loaded {len(self.samples_buffer)} existing samples")

            except Exception as e:
                logger.error(f"Error loading existing samples: {e}")

    def _save_samples(self):
        """Save samples to disk."""
        samples_file = os.path.join(self.data_dir, "samples", "samples.json")
        try:
            with self.lock:
                samples_data = []
                for sample in self.samples_buffer:
                    sample_dict = asdict(sample)
                    # Convert numpy arrays to lists for JSON serialization
                    # Handle complex IQ samples by storing magnitude only for efficiency
                    sample_dict["samples_magnitude"] = np.abs(sample.samples).tolist()
                    sample_dict["spectrum"] = sample.spectrum.tolist()

                    # Remove the original samples field to avoid serialization issues
                    if "samples" in sample_dict:
                        del sample_dict["samples"]
                    samples_data.append(sample_dict)

            data = {
                "samples": samples_data,
                "total_samples": len(samples_data),
                "last_updated": datetime.now().isoformat(),
            }

            with open(samples_file, "w") as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.error(f"Error saving samples: {e}")

    def get_samples(
        self, limit: int | None = None, category: str | None = None
    ) -> list[SignalSample]:
        """Get samples from the collection."""
        with self.lock:
            samples = list(self.samples_buffer)

        if category:
            samples = [s for s in samples if s.label == category]

        if limit:
            samples = samples[-limit:]

        return samples

    def create_dataset(
        self, name: str, description: str, categories: list[str] | None = None
    ) -> TrainingDataset:
        """Create a training dataset from collected samples."""
        samples = self.get_samples()

        if categories:
            samples = [s for s in samples if s.label in categories]

        dataset = TrainingDataset(
            name=name,
            description=description,
            created_at=datetime.now().isoformat(),
            samples=samples,
            categories=categories or [],
            total_samples=len(samples),
        )

        # Save dataset
        dataset_file = os.path.join(self.data_dir, "datasets", f"{name}.json")
        try:
            dataset_dict = asdict(dataset)
            # Convert numpy arrays to lists
            for sample in dataset_dict["samples"]:
                sample["samples"] = sample["samples"].tolist()
                sample["spectrum"] = sample["spectrum"].tolist()

            with open(dataset_file, "w") as f:
                json.dump(dataset_dict, f, indent=2)

            logger.info(f"Created dataset '{name}' with {len(samples)} samples")

        except Exception as e:
            logger.error(f"Error saving dataset: {e}")

        return dataset

    def get_datasets(self) -> list[TrainingDataset]:
        """Get all available datasets."""
        datasets: list[TrainingDataset] = []
        datasets_dir = os.path.join(self.data_dir, "datasets")

        if os.path.exists(datasets_dir):
            for filename in os.listdir(datasets_dir):
                if filename.endswith(".json"):
                    try:
                        with open(os.path.join(datasets_dir, filename)) as f:
                            data = json.load(f)

                        # Convert lists back to numpy arrays
                        for sample in data["samples"]:
                            sample["samples"] = np.array(sample["samples"])
                            sample["spectrum"] = np.array(sample["spectrum"])

                        dataset = TrainingDataset(**data)
                        datasets.append(dataset)

                    except Exception as e:
                        logger.error(f"Error loading dataset {filename}: {e}")

        return datasets

    def get_statistics(self) -> dict[str, Any]:
        """Get collection statistics."""
        with self.lock:
            total_samples = len(self.samples_buffer)

            if total_samples == 0:
                return {"total_samples": 0}

            # Count by category
            categories: dict[str, int] = {}
            for sample in self.samples_buffer:
                category = sample.label or "unlabeled"
                categories[category] = categories.get(category, 0) + 1

            # Time range
            timestamps = [datetime.fromisoformat(s.timestamp) for s in self.samples_buffer]
            time_range = {"start": min(timestamps).isoformat(), "end": max(timestamps).isoformat()}

            return {
                "total_samples": total_samples,
                "categories": categories,
                "time_range": time_range,
                "collecting": self.collecting,
            }


# Global data collector instance
data_collector = DataCollector()
