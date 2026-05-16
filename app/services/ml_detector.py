import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from typing import Dict, Any, Optional
import logging

from app.config import settings

logger = logging.getLogger(__name__)


class AnomalyDetector:
    def __init__(self) -> None:
        self.model: Optional[IsolationForest] = None
        self.scaler: Optional[StandardScaler] = None
        self.is_trained = False
        self.feature_columns: list = []

    def train(self, df: pd.DataFrame) -> Dict[str, Any]:
        numeric_df = df.select_dtypes(include=[np.number])
        if numeric_df.empty:
            return {"success": False, "error": "No numeric columns found"}
        if len(numeric_df) < 10:
            return {"success": False, "error": "Need at least 10 rows to train"}

        self.feature_columns = list(numeric_df.columns)
        numeric_df = numeric_df.fillna(numeric_df.mean())

        self.scaler = StandardScaler()
        X = self.scaler.fit_transform(numeric_df)

        self.model = IsolationForest(
            contamination=settings.ANOMALY_CONTAMINATION,
            random_state=settings.RANDOM_SEED,
            n_estimators=100,
        )
        self.model.fit(X)
        self.is_trained = True

        return {
            "success": True,
            "n_samples": len(numeric_df),
            "n_features": len(self.feature_columns),
        }

    def predict(self, df: pd.DataFrame) -> Dict[str, Any]:
        if not self.is_trained or self.model is None:
            return {"is_trained": False, "anomaly_ratio": 0.0, "status": "NOT_TRAINED"}

        available = [c for c in self.feature_columns if c in df.columns]
        if not available:
            return {"is_trained": True, "anomaly_ratio": 0.0, "status": "NO_MATCHING_FEATURES"}

        X = df[available].fillna(df[available].mean())
        X_scaled = self.scaler.transform(X)
        preds = self.model.predict(X_scaled)

        anomaly_count = int((preds == -1).sum())
        anomaly_ratio = round(anomaly_count / len(preds), 4)

        if anomaly_ratio > 0.2:
            status = "HIGH_ANOMALIES"
        elif anomaly_ratio > 0.05:
            status = "MODERATE_ANOMALIES"
        else:
            status = "CLEAN"

        return {
            "is_trained": True,
            "anomaly_ratio": anomaly_ratio,
            "anomaly_count": anomaly_count,
            "total_rows": len(preds),
            "status": status,
        }


ml_model = AnomalyDetector()
