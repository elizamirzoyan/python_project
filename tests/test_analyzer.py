"""
Unit tests for app/services/analyzer.py

Run with:  pytest tests/test_analyzer.py -v
"""

import pytest
import pandas as pd

from app.services.analyzer import (
    analyze_dataframe,
    _find_outliers,
    _analyze_column,
)


# ── _find_outliers ─────────────────────────────────────────────────────────────

def test_find_outliers_detects_extreme_value():
    data = [10.0, 11.0, 9.0, 10.5, 10.2, 9.8, 10.1, 9.9, 10.3, 1000.0]
    assert _find_outliers(pd.Series(data)) >= 1


def test_find_outliers_clean_data_returns_zero():
    assert _find_outliers(pd.Series(list(range(20)))) == 0


def test_find_outliers_too_few_values():
    assert _find_outliers(pd.Series([1.0, 2.0])) == 0


def test_find_outliers_ignores_nulls():
    data = [10.0, None, 10.5, 9.8, 10.2, None, 1000.0, 10.1, 9.9, 10.3]
    assert _find_outliers(pd.Series(data)) >= 1


# ── _analyze_column — parametrized ────────────────────────────────────────────

@pytest.mark.parametrize("values, expected_null_count, expected_null_pct", [
    ([1.0, 2.0, None, 4.0, 5.0], 1, 20.0),
    ([None, None, None, None], 4, 100.0),
    ([1.0, 2.0, 3.0], 0, 0.0),
])
def test_analyze_column_null_stats(values, expected_null_count, expected_null_pct):
    series = pd.Series(values)
    report = _analyze_column("col", series, total_rows=len(values))
    assert report.null_count == expected_null_count
    assert report.null_percentage == pytest.approx(expected_null_pct, abs=0.01)


def test_analyze_column_numeric_stats():
    series = pd.Series([1.0, 2.0, None, 4.0, 5.0])
    report = _analyze_column("score", series, total_rows=5)
    assert report.name == "score"
    assert report.min_value == 1.0
    assert report.max_value == 5.0
    assert report.mean_value == pytest.approx(3.0)


def test_analyze_column_text_has_no_numeric_stats():
    series = pd.Series(["a", "b", None, "a"])
    report = _analyze_column("label", series, total_rows=4)
    assert report.null_count == 1
    assert report.min_value is None
    assert report.outlier_count is None


# ── analyze_dataframe — parametrized health score edge cases ──────────────────

@pytest.mark.parametrize("null_frac, expected_health_below", [
    (0.0, 101),   # clean data — no upper bound check, just must pass
    (0.5, 75),    # 50% nulls — health must be below 75
    (0.9, 40),    # 90% nulls — health must be very low
])
def test_health_score_degrades_with_nulls(null_frac, expected_health_below):
    n = 100
    vals = [None if i < int(n * null_frac) else float(i) for i in range(n)]
    df = pd.DataFrame({"a": vals, "b": vals})
    result = analyze_dataframe(df)
    assert result["health_score"] < expected_health_below


def test_basic_analysis_shape():
    df = pd.DataFrame({"a": [1, 2, 3, 4, 5], "b": ["x", "y", "z", "w", "v"]})
    result = analyze_dataframe(df)
    assert result["total_rows"] == 5
    assert result["total_columns"] == 2
    assert result["null_percentage"] == 0.0
    assert result["overall_health"] in ("Excellent", "Good", "Fair", "Poor")
    assert len(result["columns"]) == 2


def test_null_percentage_calculation():
    df = pd.DataFrame({"a": [1.0, None, 3.0], "b": [None, 2.0, 3.0]})
    result = analyze_dataframe(df)
    assert result["null_percentage"] == pytest.approx(33.33, abs=0.1)


def test_outlier_count_propagates():
    normal = [10.0] * 18
    extreme = [10000.0, -10000.0]
    df = pd.DataFrame({"values": normal + extreme})
    result = analyze_dataframe(df)
    assert result["outlier_count"] >= 1


def test_health_good_or_better_on_clean_data():
    import numpy as np
    rng = np.random.default_rng(42)
    df = pd.DataFrame({
        "a": rng.normal(50, 5, 200).tolist(),
        "b": rng.normal(20, 2, 200).tolist(),
    })
    result = analyze_dataframe(df)
    assert result["health_score"] >= 75
    assert result["overall_health"] in ("Excellent", "Good")


def test_recommendations_mention_missing_values():
    vals = [None if i % 3 == 0 else float(i) for i in range(60)]
    df = pd.DataFrame({"x": vals})
    result = analyze_dataframe(df)
    combined = " ".join(result["recommendations"]).lower()
    assert "missing" in combined


def test_recommendations_clean_data():
    df = pd.DataFrame({"a": list(range(50)), "b": list(range(50))})
    result = analyze_dataframe(df)
    combined = " ".join(result["recommendations"]).lower()
    assert "no major" in combined or "clean" in combined


def test_summary_contains_row_count():
    df = pd.DataFrame({"a": [1, 2, 3]})
    result = analyze_dataframe(df)
    assert "3" in result["summary"]


def test_empty_dataframe_does_not_crash():
    df = pd.DataFrame({"a": [], "b": []})
    result = analyze_dataframe(df)
    assert result["total_rows"] == 0
    assert result["null_percentage"] == 0.0
