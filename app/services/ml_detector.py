import logging
from typing import Dict, Any

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

logger = logging.getLogger(__name__)

MIN_ROWS_REQUIRED = 10


class AnomalyDetector:
    """
    Wraps scikit-learn's IsolationForest to flag anomalous rows in a DataFrame.

    Usage:
        detector = AnomalyDetector()
        detector.train(df)
        result = detector.predict(df)
    """

    def __init__(self, contamination: float = 0.1, random_state: int = 42) -> None:
        self._model = IsolationForest(
            contamination=contamination,
            random_state=random_state,
            n_jobs=-1,
        )
        self.is_trained: bool = False
        self._feature_columns: list[str] = []

    def train(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Fit the model on the numeric columns of df.

        Returns a dict with keys:
            success (bool)  — whether training succeeded
            error   (str)   — human-readable reason when success is False
            columns (list)  — names of the columns used for training
        """
        numeric_cols = df.select_dtypes(include=np.number).columns.tolist()

        if not numeric_cols:
            self.is_trained = False
            return {"success": False, "error": "No numeric columns found.", "columns": []}

        if len(df) < MIN_ROWS_REQUIRED:
            self.is_trained = False
            return {
                "success": False,
                "error": f"Need at least {MIN_ROWS_REQUIRED} rows to train; got {len(df)}.",
                "columns": [],
            }

        train_data = df[numeric_cols].fillna(df[numeric_cols].median())
        self._model.fit(train_data)
        self._feature_columns = numeric_cols
        self.is_trained = True

        logger.info("AnomalyDetector trained on columns: %s", numeric_cols)
        return {"success": True, "error": None, "columns": numeric_cols}

    def predict(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Score rows in df and return anomaly statistics.

        Returns a dict with keys:
            is_trained      (bool)
            status          (str)   — one of NOT_TRAINED, NO_MATCHING_FEATURES,
                                      CLEAN, MODERATE_ANOMALIES, HIGH_ANOMALIES
            anomaly_count   (int)
            anomaly_ratio   (float) — fraction of rows flagged as anomalous
            total_rows      (int)
        """
        if not self.is_trained:
            return {
                "is_trained": False,
                "status": "NOT_TRAINED",
                "anomaly_count": 0,
                "anomaly_ratio": 0.0,
                "total_rows": len(df),
            }

        available_cols = [c for c in self._feature_columns if c in df.columns]
        if not available_cols:
            return {
                "is_trained": True,
                "status": "NO_MATCHING_FEATURES",
                "anomaly_count": 0,
                "anomaly_ratio": 0.0,
                "total_rows": len(df),
            }

        predict_data = df[available_cols].fillna(df[available_cols].median())
        predictions = self._model.predict(predict_data)
        anomaly_count = int((predictions == -1).sum())
        anomaly_ratio = anomaly_count / len(df) if len(df) > 0 else 0.0

        if anomaly_ratio > 0.2:
            status = "HIGH_ANOMALIES"
        elif anomaly_ratio > 0.05:
            status = "MODERATE_ANOMALIES"
        else:
            status = "CLEAN"

        return {
            "is_trained": True,
            "status": status,
            "anomaly_count": anomaly_count,
            "anomaly_ratio": anomaly_ratio,
            "total_rows": len(df),
        }
