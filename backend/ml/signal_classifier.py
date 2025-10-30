"""
Signal Classification Module

Provides real-time signal classification based on frequency, features, and spectrum analysis.
Focuses on user-friendly service categories with technical details as metadata.
"""

import logging
from dataclasses import dataclass
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class ClassificationResult:
    """Result of signal classification."""

    category: str
    confidence: float
    modulation: str
    description: str
    technical_details: dict[str, Any]


class SignalClassifier:
    """Classifies signals into service categories with technical metadata."""

    def __init__(self):
        self.signal_categories = {
            "aviation": {
                "freq_range": (118e6, 137e6),
                "modulation": "AM",
                "bandwidth": "narrow",
                "description": "Aviation Communication",
                "typical_bw": 8000,  # Hz
                "typical_snr": 15,
            },
            "fm_radio": {
                "freq_range": (88e6, 108e6),
                "modulation": "FM",
                "bandwidth": "wide",
                "description": "FM Broadcast Radio",
                "typical_bw": 200000,  # Hz
                "typical_snr": 20,
            },
            "cb_radio": {
                "freq_range": (26.965e6, 27.405e6),
                "modulation": "AM/SSB",
                "bandwidth": "narrow",
                "description": "CB Radio",
                "typical_bw": 4000,  # Hz
                "typical_snr": 10,
            },
            "ham_2m": {
                "freq_range": (144e6, 148e6),
                "modulation": "FM/SSB",
                "bandwidth": "narrow",
                "description": "2m Ham Radio",
                "typical_bw": 12000,  # Hz
                "typical_snr": 15,
            },
            "ham_70cm": {
                "freq_range": (420e6, 450e6),
                "modulation": "FM",
                "bandwidth": "narrow",
                "description": "70cm Ham Radio",
                "typical_bw": 12000,  # Hz
                "typical_snr": 15,
            },
            "walkie_talkie": {
                "freq_ranges": [(462.5625e6, 462.7250e6), (467.5625e6, 467.7250e6)],
                "modulation": "FM",
                "bandwidth": "narrow",
                "description": "FRS/GMRS Walkie-Talkie",
                "typical_bw": 12500,  # Hz
                "typical_snr": 12,
            },
            "weather": {
                "freq_range": (162.4e6, 162.55e6),
                "modulation": "FM",
                "bandwidth": "narrow",
                "description": "NOAA Weather Radio",
                "typical_bw": 5000,  # Hz
                "typical_snr": 18,
            },
            "marine": {
                "freq_range": (156e6, 162e6),
                "modulation": "FM",
                "bandwidth": "narrow",
                "description": "Marine VHF Radio",
                "typical_bw": 16000,  # Hz
                "typical_snr": 15,
            },
            "unknown": {
                "freq_range": (0, 1e12),  # Catch-all
                "modulation": "Unknown",
                "bandwidth": "unknown",
                "description": "Unknown Signal",
                "typical_bw": 10000,  # Hz
                "typical_snr": 10,
            },
        }

        # Classification history for learning
        self.classification_history = []
        self.max_history = 1000

    def classify_signal(
        self,
        frequency: float,
        features: dict[str, float],
        spectrum: np.ndarray,
        signal_info: dict[str, Any] | None = None,
    ) -> ClassificationResult:
        """
        Classify a signal based on frequency, features, and spectrum.

        Args:
            frequency: Signal frequency in Hz
            features: Extracted signal features
            spectrum: Power spectrum array
            signal_info: Additional signal information (bandwidth, SNR, etc.)

        Returns:
            ClassificationResult with category, confidence, and metadata
        """
        # Start with frequency-based classification
        freq_based_category = self._classify_by_frequency(frequency)

        # Enhance with feature-based analysis
        feature_confidence = self._analyze_features(features, freq_based_category)

        # Use signal characteristics if available
        signal_confidence = 1.0
        if signal_info:
            signal_confidence = self._analyze_signal_characteristics(
                signal_info, freq_based_category
            )

        # Combine confidences
        total_confidence = (feature_confidence + signal_confidence) / 2.0

        # Get category info
        category_info = self.signal_categories[freq_based_category]

        # Create technical details
        technical_details = {
            "frequency_hz": frequency,
            "frequency_mhz": frequency / 1e6,
            "bandwidth_hz": signal_info.get("bandwidth", 0) if signal_info else 0,
            "snr_db": signal_info.get("snr", 0) if signal_info else 0,
            "power_db": signal_info.get("power", 0) if signal_info else 0,
            "spectral_centroid": features.get("spectral_centroid", 0),
            "spectral_bandwidth": features.get("spectral_bandwidth", 0),
            "modulation_type": category_info["modulation"],
            "bandwidth_type": category_info["bandwidth"],
        }

        # Store classification for learning
        self._store_classification(frequency, freq_based_category, total_confidence, features)

        return ClassificationResult(
            category=freq_based_category,
            confidence=total_confidence,
            modulation=category_info["modulation"],
            description=category_info["description"],
            technical_details=technical_details,
        )

    def _classify_by_frequency(self, frequency: float) -> str:
        """Classify signal based on frequency ranges."""
        for category, info in self.signal_categories.items():
            if category == "unknown":
                continue

            # Handle single frequency range
            if "freq_range" in info:
                freq_min, freq_max = info["freq_range"]
                if freq_min <= frequency <= freq_max:
                    return category

            # Handle multiple frequency ranges (like walkie-talkies)
            elif "freq_ranges" in info:
                for freq_range in info["freq_ranges"]:
                    freq_min, freq_max = freq_range
                    if freq_min <= frequency <= freq_max:
                        return category

        return "unknown"

    def _analyze_features(self, features: dict[str, float], category: str) -> float:
        """Analyze signal features to enhance classification confidence."""
        if category == "unknown":
            return 0.5

        category_info = self.signal_categories[category]
        confidence = 0.7  # Base confidence for frequency match

        # Analyze spectral characteristics
        spectral_centroid = features.get("spectral_centroid", 0)
        spectral_bandwidth = features.get("spectral_bandwidth", 0)

        # Bandwidth analysis
        if category_info["bandwidth"] == "wide":
            if spectral_bandwidth > 50000:  # Wide bandwidth
                confidence += 0.2
        elif category_info["bandwidth"] == "narrow":
            if spectral_bandwidth < 20000:  # Narrow bandwidth
                confidence += 0.2

        # Power analysis
        total_power = features.get("total_power", 0)
        peak_power = features.get("peak_power", 0)
        power_ratio = features.get("power_ratio", 0)

        # Strong signals get higher confidence
        if peak_power > 20:  # dB
            confidence += 0.1

        # Clamp confidence
        return min(1.0, max(0.1, confidence))

    def _analyze_signal_characteristics(self, signal_info: dict[str, Any], category: str) -> float:
        """Analyze signal characteristics like bandwidth and SNR."""
        if category == "unknown":
            return 0.5

        category_info = self.signal_categories[category]
        confidence = 0.8  # Base confidence

        # Bandwidth analysis
        bandwidth = signal_info.get("bandwidth", 0)
        typical_bw = category_info.get("typical_bw", 10000)

        if bandwidth > 0:
            # Check if bandwidth is reasonable for this category
            bw_ratio = bandwidth / typical_bw
            if 0.5 <= bw_ratio <= 2.0:  # Within reasonable range
                confidence += 0.1
            elif 0.2 <= bw_ratio <= 5.0:  # Still reasonable
                confidence += 0.05

        # SNR analysis
        snr = signal_info.get("snr", 0)
        typical_snr = category_info.get("typical_snr", 10)

        if snr > 0:
            # Good SNR increases confidence
            if snr >= typical_snr:
                confidence += 0.1
            elif snr >= typical_snr * 0.7:
                confidence += 0.05

        return min(1.0, max(0.1, confidence))

    def _store_classification(
        self, frequency: float, category: str, confidence: float, features: dict[str, float]
    ):
        """Store classification for future learning."""
        classification = {
            "frequency": frequency,
            "category": category,
            "confidence": confidence,
            "features": features,
            "timestamp": np.datetime64("now"),
        }

        self.classification_history.append(classification)

        # Keep only recent history
        if len(self.classification_history) > self.max_history:
            self.classification_history = self.classification_history[-self.max_history :]

    def get_category_info(self, category: str, include_technical: bool = False) -> dict[str, Any]:
        """Get information about a signal category."""
        if category not in self.signal_categories:
            category = "unknown"

        info = self.signal_categories[category].copy()

        if include_technical:
            # Add technical details
            info["technical"] = {
                "typical_bandwidth_hz": info.get("typical_bw", 0),
                "typical_snr_db": info.get("typical_snr", 0),
                "frequency_range_mhz": (
                    info["freq_range"][0] / 1e6 if "freq_range" in info else 0,
                    info["freq_range"][1] / 1e6 if "freq_range" in info else 0,
                ),
            }

        return info

    def get_classification_stats(self) -> dict[str, Any]:
        """Get statistics about recent classifications."""
        if not self.classification_history:
            return {"total_classifications": 0}

        # Count by category
        category_counts: dict[str, int] = {}
        total_confidence = 0

        for classification in self.classification_history:
            category = classification["category"]
            category_counts[category] = category_counts.get(category, 0) + 1
            total_confidence += classification["confidence"]

        avg_confidence = total_confidence / len(self.classification_history)

        return {
            "total_classifications": len(self.classification_history),
            "category_counts": category_counts,
            "average_confidence": avg_confidence,
            "most_common_category": (
                max(category_counts, key=lambda k: category_counts[k]) if category_counts else None
            ),
        }

    def get_available_categories(self) -> list[str]:
        """Get list of available signal categories."""
        return list(self.signal_categories.keys())


# Global classifier instance
signal_classifier = SignalClassifier()
