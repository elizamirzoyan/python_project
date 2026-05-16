"""
Tests for app/services/analyzer.py

Run with:  pytest tests/test_analyzer.py -v
"""
import pytest
import pandas as pd

from app.services.analyzer import analyze_dataframe, _find_outliers, _analyze_column


# ── _find_outliers ────────────────────────────────────────────────────────────

def test_find_outliers_detects_extreme_value():
    # 9 normal values + 1 extreme outlier
    data = [10.0, 11.0, 9.0, 10.5, 10.2, 9.8, 10.1, 9.9, 10.3, 1000.0]
    assert _find_outliers(pd.Series(data)) >= 1


def test_find_outliers_clean_data_returns_zero():
    data = list(range(20))   # evenly spaced, no outliers
    assert _find_outliers(pd.Series(data)) == 0


def test_find_outliers_too_few_values():
    # needs at least 4 values; fewer should return 0 safely
    assert _find_outliers(pd.Series([1.0, 2.0])) == 0


def test_find_outliers_ignores_nulls():
    data = [10.0, None, 10.5, 9.8, 10.2, None, 1000.0, 10.1, 9.9, 10.3]
    # should not raise even with NaN mixed in
    count = _find_outliers(pd.Series(data))
    assert count >= 1


# ── _analyze_column ───────────────────────────────────────────────────────────

def test_analyze_column_numeric():
    s = pd.Series([1.0, 2.0, None, 4.0, 5.0])
    col = _analyze_column("score", s, total_rows=5)
    assert col.name == "score"
    assert col.null_count == 1
    assert col.null_percentage == 20.0
    assert col.min_value == 1.0
    assert col.max_value == 5.0
    assert col.mean_value == pytest.approx(3.0)


def test_analyze_column_text():
    s = pd.Series(["a", "b", None, "a"])
    col = _analyze_column("label", s, total_rows=4)
    assert col.null_count == 1
    assert col.min_value is None   # text columns have no min/max
    assert col.outlier_count is None


def test_analyze_column_all_null():
    s = pd.Series([None, None, None])
    col = _analyze_column("x", s, total_rows=3)
    assert col.null_percentage == 100.0
    assert col.unique_values == 0


# ── analyze_dataframe ─────────────────────────────────────────────────────────

def test_basic_analysis():
    df = pd.DataFrame({"a": [1, 2, 3, 4, 5], "b": ["x", "y", "z", "w", "v"]})
    result = analyze_dataframe(df)
    assert result["total_rows"] == 5
    assert result["total_columns"] == 2
    assert result["null_percentage"] == 0.0
    assert result["overall_health"] in ("Excellent", "Good", "Fair", "Poor")
    assert len(result["columns"]) == 2


def test_null_percentage_calculation():
    # 2 nulls out of 10 cells = 20%
    df = pd.DataFrame({"a": [1.0, None, 3.0], "b": [None, 2.0, 3.0]})
    result = analyze_dataframe(df)
    assert result["null_percentage"] == pytest.approx(33.33, abs=0.1)


def test_outlier_count_propagates():
    normal = [10.0] * 18
    extreme = [10000.0, -10000.0]
    df = pd.DataFrame({"values": normal + extreme})
    result = analyze_dataframe(df)
    assert result["outlier_count"] >= 1


def test_health_excellent_on_clean_data():
    df = pd.DataFrame({"a": list(range(100)), "b": [float(i) for i in range(100)]})
    result = analyze_dataframe(df)
    assert result["health_score"] >= 85
    assert result["overall_health"] == "Excellent"


def test_health_poor_on_messy_data():
    vals = [None if i % 2 == 0 else float(i) for i in range(100)]
    df = pd.DataFrame({"a": vals, "b": vals})
    result = analyze_dataframe(df)
    assert result["health_score"] < 65


def test_recommendations_mention_missing_values():
    # 33% nulls should trigger a recommendation
    vals = [None if i % 3 == 0 else float(i) for i in range(60)]
    df = pd.DataFrame({"x": vals})
    result = analyze_dataframe(df)
    combined = " ".join(result["recommendations"]).lower()
    assert "missing" in combined


def test_recommendations_clean_data():
    df = pd.DataFrame({"a": list(range(50)), "b": list(range(50))})
    result = analyze_dataframe(df)
    combined = " ".join(result["recommendations"]).lower()
    assert "clean" in combined or "no major" in combined


def test_summary_contains_row_count():
    df = pd.DataFrame({"a": [1, 2, 3]})
    result = analyze_dataframe(df)
    assert "3" in result["summary"]


def test_empty_dataframe_does_not_crash():
    df = pd.DataFrame({"a": [], "b": []})
    result = analyze_dataframe(df)
    assert result["total_rows"] == 0
    assert result["null_percentage"] == 0.0
