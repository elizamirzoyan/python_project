import numpy as np
import pandas as pd
from scipy import stats
from typing import List, Dict, Any, Tuple
import logging

from app.models.schemas import ColumnReport

logger = logging.getLogger(__name__)

_DTYPE_LABELS = {
    "int64": "integer", "int32": "integer", "int16": "integer", "int8": "integer",
    "float64": "decimal", "float32": "decimal",
    "object": "text",
    "bool": "yes/no",
    "datetime64[ns]": "date/time",
}


def _find_outliers(series: pd.Series, threshold: float = 3.0) -> int:
    clean = series.dropna()
    if len(clean) < 4:
        return 0
    try:
        z = np.abs(stats.zscore(clean.astype(float)))
        return int((z > threshold).sum())
    except Exception:
        return 0


def _analyze_column(name: str, series: pd.Series, total_rows: int) -> ColumnReport:
    null_count = int(series.isnull().sum())
    null_pct = round(null_count / total_rows * 100, 2) if total_rows > 0 else 0.0
    unique_vals = int(series.nunique())
    sample_values = [v for v in series.dropna().head(3).tolist() if v is not None]
    dtype_label = _DTYPE_LABELS.get(str(series.dtype), str(series.dtype))

    min_val = max_val = mean_val = outlier_count = None
    if pd.api.types.is_numeric_dtype(series):
        clean = series.dropna()
        if len(clean) > 0:
            min_val = round(float(clean.min()), 4)
            max_val = round(float(clean.max()), 4)
            mean_val = round(float(clean.mean()), 4)
            outlier_count = _find_outliers(series)

    return ColumnReport(
        name=name,
        data_type=dtype_label,
        null_count=null_count,
        null_percentage=null_pct,
        unique_values=unique_vals,
        sample_values=sample_values,
        min_value=min_val,
        max_value=max_val,
        mean_value=mean_val,
        outlier_count=outlier_count,
    )


def _health_score(null_pct: float, outlier_ratio: float) -> Tuple[float, str]:
    score = 100.0 - (null_pct * 1.5) - (outlier_ratio * 30)
    score = max(0.0, min(100.0, score))
    if score >= 85:
        label = "Excellent"
    elif score >= 65:
        label = "Good"
    elif score >= 40:
        label = "Fair"
    else:
        label = "Poor"
    return round(score, 1), label


def _recommendations(null_pct: float, outlier_count: int, columns: List[ColumnReport]) -> List[str]:
    recs = []

    if null_pct > 30:
        recs.append(
            f"Your data has {null_pct}% missing values — that's quite a lot. "
            "Consider dropping columns that are more than 50% empty."
        )
    elif null_pct > 10:
        recs.append(
            f"{null_pct}% of your values are missing. "
            "Try filling numeric columns with their average and text columns with 'Unknown'."
        )

    if outlier_count > 0:
        recs.append(
            f"Found {outlier_count} outlier(s) — values that are unusually high or low. "
            "Check whether they're real data points or typos."
        )

    half_empty = [c for c in columns if c.null_percentage > 50]
    if half_empty:
        names = ", ".join(c.name for c in half_empty)
        recs.append(f"These columns are more than half empty: {names}. You may want to drop them.")

    if not recs:
        recs.append("Your data looks clean! No major issues detected.")

    return recs


def analyze_dataframe(df: pd.DataFrame) -> Dict[str, Any]:
    total_rows = len(df)
    columns = [_analyze_column(col, df[col], total_rows) for col in df.columns]

    total_nulls = sum(c.null_count for c in columns)
    total_cells = total_rows * len(df.columns) if df.columns.size > 0 else 1
    null_pct = round(total_nulls / total_cells * 100, 2) if total_cells > 0 else 0.0

    outlier_total = sum(c.outlier_count or 0 for c in columns)
    outlier_ratio = outlier_total / total_rows if total_rows > 0 else 0.0

    health_score, health_label = _health_score(null_pct, outlier_ratio)
    anomaly_score = round(min(1.0, (null_pct / 100 * 0.7) + (outlier_ratio * 0.3)), 4)
    memory_mb = round(df.memory_usage(deep=True).sum() / (1024 * 1024), 2)

    summary = (
        f"DataSnoop scanned {total_rows:,} rows across {len(df.columns)} columns. "
        f"Overall health: {health_label} ({health_score}/100). "
        f"Missing data rate: {null_pct}%."
    )

    return {
        "total_rows": total_rows,
        "total_columns": len(df.columns),
        "null_percentage": null_pct,
        "outlier_count": outlier_total,
        "anomaly_score": anomaly_score,
        "health_score": health_score,
        "overall_health": health_label,
        "memory_usage_mb": memory_mb,
        "columns": columns,
        "summary": summary,
        "recommendations": _recommendations(null_pct, outlier_total, columns),
    }
