"""Data preprocessing for ML model training."""

import logging
from typing import Any

import numpy as np
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


class DataPreprocessor:
    """Preprocess signal data for ML training."""

    def __init__(self):
        self.scaler = StandardScaler()
        self.feature_names = [
            "mean_power",
            "std_power",
            "max_power",
            "min_power",
            "spectral_centroid",
            "spectral_bandwidth",
            "spectral_rolloff",
            "zero_crossing_rate",
            "rms_energy",
            "spectral_flatness",
        ]

    def extract_features(self, samples: np.ndarray, spectrum: np.ndarray) -> dict[str, float]:
        """
        Extract features from signal samples and spectrum.

        Args:
            samples: IQ samples
            spectrum: Power spectrum in dB

        Returns:
            Dictionary of extracted features
        """
        features = {}

        # Time domain features
        features["mean_power"] = float(np.mean(np.abs(samples)))
        features["std_power"] = float(np.std(np.abs(samples)))
        features["max_power"] = float(np.max(np.abs(samples)))
        features["min_power"] = float(np.min(np.abs(samples)))
        features["rms_energy"] = float(np.sqrt(np.mean(np.abs(samples) ** 2)))

        # Spectral features
        power_spectrum = np.abs(spectrum)
        features["spectral_centroid"] = float(
            np.sum(np.arange(len(power_spectrum)) * power_spectrum)
            / np.sum(power_spectrum)
            if np.sum(power_spectrum) > 0
            else 0
        )
        features["spectral_bandwidth"] = float(
            np.sqrt(
                np.sum(
                    ((np.arange(len(power_spectrum)) - features["spectral_centroid"]) ** 2)
                    * power_spectrum
                )
                / np.sum(power_spectrum)
            )
            if np.sum(power_spectrum) > 0
            else 0
        )

        # Spectral rolloff (frequency below which 85% of energy is contained)
        cumsum = np.cumsum(power_spectrum)
        total_energy = cumsum[-1]
        if total_energy > 0:
            rolloff_idx = np.where(cumsum >= 0.85 * total_energy)[0]
            features["spectral_rolloff"] = float(rolloff_idx[0] if len(rolloff_idx) > 0 else 0)
        else:
            features["spectral_rolloff"] = 0.0

        # Zero crossing rate
        zero_crossings = np.sum(np.diff(np.sign(np.real(samples))) != 0)
        features["zero_crossing_rate"] = float(zero_crossings / len(samples))

        # Spectral flatness
        if np.all(power_spectrum > 0):
            geometric_mean = np.exp(np.mean(np.log(power_spectrum)))
            arithmetic_mean = np.mean(power_spectrum)
            features["spectral_flatness"] = float(
                geometric_mean / arithmetic_mean if arithmetic_mean > 0 else 0
            )
        else:
            features["spectral_flatness"] = 0.0

        return features

    def features_to_array(self, features: dict[str, float]) -> np.ndarray:
        """
        Convert features dictionary to numpy array.

        Args:
            features: Features dictionary

        Returns:
            Feature array
        """
        return np.array([features.get(name, 0.0) for name in self.feature_names])

    def fit_scaler(self, feature_arrays: list[np.ndarray]):
        """
        Fit the scaler on training data.

        Args:
            feature_arrays: List of feature arrays
        """
        if len(feature_arrays) == 0:
            return
        X = np.vstack(feature_arrays)
        self.scaler.fit(X)
        logger.info("Fitted scaler on training data")

    def transform_features(self, feature_array: np.ndarray) -> np.ndarray:
        """
        Transform features using fitted scaler.

        Args:
            feature_array: Feature array

        Returns:
            Scaled feature array
        """
        if not hasattr(self.scaler, "mean_"):
            return feature_array
        return self.scaler.transform(feature_array.reshape(1, -1))[0]

