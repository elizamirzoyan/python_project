import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class MLAnomalyDetector:
    """
    A wrapper for using IsolationForest to detect anomalies in a DataFrame.
    """
    def __init__(self, contamination='auto', random_state=42):
        self.model = IsolationForest(contamination=contamination, random_state=random_state, n_jobs=-1)
        self.is_trained = False
        self.numeric_columns = []

    def train(self, df: pd.DataFrame):
        """Trains the Isolation Forest model on the numeric columns of the DataFrame."""
        self.numeric_columns = df.select_dtypes(include=np.number).columns.tolist()
        if not self.numeric_columns:
            logger.info("No numeric columns found for ML anomaly detection.")
            self.is_trained = False
            return

        # Simple imputation for training
        train_data = df[self.numeric_columns].fillna(df[self.numeric_columns].median())
        
        if train_data.empty:
            self.is_trained = False
            return

        self.model.fit(train_data)
        self.is_trained = True
        logger.info(f"Trained ML anomaly detector on columns: {self.numeric_columns}")

    def predict(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Predicts anomalies and returns the anomaly ratio and count."""
        if not self.is_trained or not self.numeric_columns:
            return {"anomaly_count": 0, "anomaly_ratio": 0.0}

        predict_data = df[self.numeric_columns].fillna(df[self.numeric_columns].median())
        predictions = self.model.predict(predict_data)
        anomaly_count = int((predictions == -1).sum())
        anomaly_ratio = anomaly_count / len(df) if len(df) > 0 else 0.0
        return {"anomaly_count": anomaly_count, "anomaly_ratio": anomaly_ratio}

ml_model = MLAnomalyDetector()