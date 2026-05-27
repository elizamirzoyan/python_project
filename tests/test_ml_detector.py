"""
Unit tests for app/services/ml_detector.py

Run with:  pytest tests/test_ml_detector.py -v
"""

import numpy as np
import pandas as pd
import pytest

from app.services.ml_detector import AnomalyDetector


def _make_clean_df(n: int = 60) -> pd.DataFrame:
    """Build a small DataFrame with two well-behaved numeric columns."""
    rng = np.random.default_rng(0)
    return pd.DataFrame({"a": rng.normal(0, 1, n), "b": rng.normal(5, 0.5, n)})


# ── Training ───────────────────────────────────────────────────────────────────

def test_train_succeeds_on_valid_data():
    detector = AnomalyDetector()
    result = detector.train(_make_clean_df(60))
    assert result["success"] is True
    assert detector.is_trained is True


@pytest.mark.parametrize("row_count, should_succeed", [
    (60, True),
    (2, False),
    (9, False),
    (10, True),
])
def test_train_row_count_threshold(row_count, should_succeed):
    detector = AnomalyDetector()
    df = pd.DataFrame({"a": list(range(row_count)), "b": list(range(row_count))})
    result = detector.train(df)
    assert result["success"] is should_succeed


def test_train_fails_no_numeric_columns():
    detector = AnomalyDetector()
    df = pd.DataFrame({"name": ["Alice", "Bob"] * 10})
    result = detector.train(df)
    assert result["success"] is False


def test_train_handles_nulls_gracefully():
    rng = np.random.default_rng(1)
    df = pd.DataFrame({"a": rng.normal(0, 1, 50), "b": rng.normal(5, 1, 50)})
    df.loc[[0, 5, 10], "a"] = np.nan
    detector = AnomalyDetector()
    result = detector.train(df)
    assert result["success"] is True


# ── Prediction ─────────────────────────────────────────────────────────────────

def test_predict_before_training_returns_not_trained():
    detector = AnomalyDetector()
    result = detector.predict(_make_clean_df())
    assert result["is_trained"] is False
    assert result["status"] == "NOT_TRAINED"


def test_predict_returns_valid_ratio():
    detector = AnomalyDetector()
    df = _make_clean_df(60)
    detector.train(df)
    result = detector.predict(df)
    assert result["is_trained"] is True
    assert 0.0 <= result["anomaly_ratio"] <= 1.0


@pytest.mark.parametrize("expected_status", ["CLEAN", "MODERATE_ANOMALIES", "HIGH_ANOMALIES"])
def test_predict_status_labels_are_valid(expected_status):
    detector = AnomalyDetector()
    df = _make_clean_df(60)
    detector.train(df)
    result = detector.predict(df)
    assert result["status"] in ("CLEAN", "MODERATE_ANOMALIES", "HIGH_ANOMALIES")


def test_predict_no_matching_features():
    detector = AnomalyDetector()
    detector.train(_make_clean_df(60))
    df_other = pd.DataFrame({"x": [1.0, 2.0], "y": [3.0, 4.0]})
    result = detector.predict(df_other)
    assert result["status"] == "NO_MATCHING_FEATURES"


def test_anomaly_count_and_ratio_are_consistent():
    detector = AnomalyDetector()
    df = _make_clean_df(60)
    detector.train(df)
    result = detector.predict(df)
    expected_normal = result["total_rows"] - result["anomaly_count"]
    assert expected_normal == int(round((1 - result["anomaly_ratio"]) * result["total_rows"]))
