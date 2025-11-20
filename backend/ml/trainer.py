"""ML model training pipeline."""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split

from backend.ml.data_handler import data_collector
from backend.ml.preprocessing import DataPreprocessor

logger = logging.getLogger(__name__)


class ModelTrainer:
    """Train ML models for signal classification."""

    def __init__(self, models_dir: str = "ml-models"):
        """
        Initialize model trainer.

        Args:
            models_dir: Directory to save trained models
        """
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.preprocessor = DataPreprocessor()
        self._model = None

    def prepare_training_data(self) -> tuple[np.ndarray, np.ndarray]:
        """
        Prepare training data from collected samples.

        Returns:
            Tuple of (X, y) where X is features and y is labels
        """
        datasets = data_collector.get_datasets()
        if not datasets:
            raise ValueError("No training datasets available")

        X_list = []
        y_list = []

        for dataset in datasets:
            for sample in dataset.samples:
                if sample.label and sample.category:
                    # Extract features
                    features = self.preprocessor.extract_features(
                        sample.samples, sample.spectrum
                    )
                    feature_array = self.preprocessor.features_to_array(features)
                    X_list.append(feature_array)
                    y_list.append(sample.category)

        if len(X_list) == 0:
            raise ValueError("No labeled samples found in datasets")

        X = np.vstack(X_list)
        y = np.array(y_list)

        logger.info(f"Prepared training data: {len(X)} samples, {len(np.unique(y))} classes")
        return X, y

    def train_model(
        self, test_size: float = 0.2, random_state: int = 42, n_estimators: int = 100
    ) -> dict[str, Any]:
        """
        Train a classification model.

        Args:
            test_size: Fraction of data to use for testing
            random_state: Random seed
            n_estimators: Number of trees for Random Forest

        Returns:
            Training metrics
        """
        try:
            # Prepare data
            X, y = self.prepare_training_data()

            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=test_size, random_state=random_state, stratify=y
            )

            # Fit scaler
            self.preprocessor.fit_scaler(X_train.tolist())

            # Transform features
            X_train_scaled = np.vstack(
                [self.preprocessor.transform_features(x) for x in X_train]
            )
            X_test_scaled = np.vstack(
                [self.preprocessor.transform_features(x) for x in X_test]
            )

            # Train model
            logger.info("Training Random Forest classifier...")
            self._model = RandomForestClassifier(
                n_estimators=n_estimators, random_state=random_state, n_jobs=-1
            )
            self._model.fit(X_train_scaled, y_train)

            # Evaluate
            y_pred = self._model.predict(X_test_scaled)
            accuracy = accuracy_score(y_test, y_pred)
            report = classification_report(y_test, y_pred, output_dict=True)
            cm = confusion_matrix(y_test, y_pred)

            metrics = {
                "accuracy": float(accuracy),
                "classification_report": report,
                "confusion_matrix": cm.tolist(),
                "n_samples": len(X),
                "n_train": len(X_train),
                "n_test": len(X_test),
                "n_classes": len(np.unique(y)),
                "classes": list(np.unique(y)),
            }

            logger.info(f"Model trained with accuracy: {accuracy:.3f}")
            return metrics

        except Exception as e:
            logger.error(f"Error training model: {e}")
            raise

    def save_model(self, model_name: str = None) -> str:
        """
        Save trained model.

        Args:
            model_name: Optional model name (defaults to timestamp)

        Returns:
            Path to saved model
        """
        if self._model is None:
            raise ValueError("No model to save. Train a model first.")

        if model_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            model_name = f"signal_classifier_{timestamp}"

        model_path = self.models_dir / f"{model_name}.pkl"
        metadata_path = self.models_dir / f"{model_name}_metadata.json"

            # Save model (using joblib for sklearn models)
        try:
            import joblib

            joblib.dump(self._model, model_path)
            logger.info(f"Saved model to {model_path}")

            # Save metadata
            metadata = {
                "model_name": model_name,
                "model_type": "RandomForestClassifier",
                "feature_names": self.preprocessor.feature_names,
                "created_at": datetime.now().isoformat(),
            }
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)

            return str(model_path)

        except ImportError:
            logger.warning("joblib not available, cannot save model")
            raise ImportError("joblib is required to save models. Install with: pip install joblib")

    def load_model(self, model_path: str):
        """
        Load a trained model.

        Args:
            model_path: Path to saved model
        """
        try:
            import joblib

            self._model = joblib.load(model_path)
            logger.info(f"Loaded model from {model_path}")

            # Load metadata if available
            metadata_path = Path(model_path).with_suffix(".json").with_name(
                Path(model_path).stem + "_metadata.json"
            )
            if metadata_path.exists():
                with open(metadata_path, "r") as f:
                    metadata = json.load(f)
                    logger.info(f"Model metadata: {metadata}")

        except ImportError:
            logger.warning("joblib not available, cannot load model")
            raise ImportError("joblib is required to load models. Install with: pip install joblib")

    def predict(self, features: dict[str, float]) -> tuple[str, float]:
        """
        Predict signal category from features.

        Args:
            features: Feature dictionary

        Returns:
            Tuple of (category, confidence)
        """
        if self._model is None:
            raise ValueError("No model loaded. Load or train a model first.")

        # Extract and transform features
        feature_array = self.preprocessor.features_to_array(features)
        feature_scaled = self.preprocessor.transform_features(feature_array)

        # Predict
        prediction = self._model.predict(feature_scaled.reshape(1, -1))[0]
        probabilities = self._model.predict_proba(feature_scaled.reshape(1, -1))[0]
        confidence = float(np.max(probabilities))

        return prediction, confidence


# Global trainer instance
model_trainer = ModelTrainer()

