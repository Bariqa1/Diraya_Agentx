"""Reliable loading and inference wrapper for the risk-model pipeline."""
from pathlib import Path

import joblib


class RiskPredictor:
    def __init__(self, model_path="ml/models/risk_model.joblib"):
        path = Path(model_path)
        if not path.exists():
            raise FileNotFoundError(f"Risk model not found: {path}. Run python -m ml.train_risk_model")
        bundle = joblib.load(path)
        self.pipeline = bundle["pipeline"]
        self.features = bundle["features"]
        self.labels = bundle["labels"]
        self.training_mode = bundle.get("training_mode", "standard")
        self.lookback_hours = bundle.get("lookback_hours", 24 * 14)
        self.target = bundle.get("target")

    def predict(self, features: dict) -> str:
        missing = [name for name in self.features if name not in features]
        if missing:
            raise ValueError(f"Missing risk features: {', '.join(missing)}")
        return str(self.pipeline.predict([features])[0])
