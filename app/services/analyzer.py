import logging
import uuid
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

from app.models.schemas import ColumnReport, Suggestion, SuggestionAction
from app.services.ml_detector import AnomalyDetector

logger = logging.getLogger(__name__)


def _find_outliers(series: pd.Series) -> int:
    """
    Count outliers in a numeric Series using the IQR method.

    Values outside [Q1 - 1.5*IQR, Q3 + 1.5*IQR] are considered outliers.
    Returns 0 for non-numeric series or series with fewer than 4 non-null values.
    """
    clean = series.dropna()
    if len(clean) < 4:
        return 0

    q1, q3 = clean.quantile(0.25), clean.quantile(0.75)
    iqr = q3 - q1
    lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    return int(((clean < lower) | (clean > upper)).sum())


def _analyze_column(name: str, series: pd.Series, total_rows: int) -> ColumnReport:
    """
    Build a ColumnReport for a single column.

    Computes null stats, unique value count, sample values, and — for numeric
    columns — min, max, mean, and outlier count.
    """
    null_count = int(series.isnull().sum())
    null_percentage = round((null_count / total_rows) * 100, 2) if total_rows > 0 else 0.0
    unique_count = int(series.nunique())

    sample_values = [
        v.item() if isinstance(v, np.generic) else v
        for v in series.dropna().unique()[:5]
    ]

    report = ColumnReport(
        name=name,
        data_type=str(series.dtype),
        null_count=null_count,
        null_percentage=null_percentage,
        unique_values=unique_count,
        sample_values=sample_values,
    )

    if pd.api.types.is_numeric_dtype(series.dtype):
        clean = series.dropna()
        if not clean.empty:
            report.min_value = float(clean.min())
            report.max_value = float(clean.max())
            report.mean_value = float(clean.mean())
        report.outlier_count = _find_outliers(series)

    return report


def _suggest_missing_value_fixes(df: pd.DataFrame, column: str) -> List[Suggestion]:
    """
    Generate imputation suggestions for a column that contains null values.

    Numeric columns get a median-fill option; categorical columns get a mode-fill
    option. Columns with more than 40 % nulls also get a drop-column option.
    """
    null_count = int(df[column].isnull().sum())
    if null_count == 0:
        return []

    null_pct = (null_count / len(df)) * 100
    actions: List[SuggestionAction] = []

    if pd.api.types.is_numeric_dtype(df[column]):
        median_val = df[column].median()
        actions.append(SuggestionAction(
            action_id=f"impute_median_{column}",
            type="IMPUTE",
            description=f"Fill with Median ({median_val:.2f})",
            params={"column": column, "strategy": "median"},
        ))
    elif pd.api.types.is_object_dtype(df[column]):
        mode_val = df[column].mode()[0] if not df[column].mode().empty else "missing"
        actions.append(SuggestionAction(
            action_id=f"impute_mode_{column}",
            type="IMPUTE",
            description=f"Fill with Mode ('{mode_val}')",
            params={"column": column, "strategy": "mode"},
        ))

    if null_pct > 40:
        actions.append(SuggestionAction(
            action_id=f"drop_col_missing_{column}",
            type="DROP_COLUMN",
            description=f"Drop Column ({null_pct:.0f}% empty)",
            params={"column": column},
        ))

    return [Suggestion(
        issue_id=f"missing_{column}_{uuid.uuid4().hex[:6]}",
        column=column,
        issue_type="Missing Values",
        description=f"Column has {null_count} missing values ({null_pct:.1f}%).",
        suggested_actions=actions,
    )]


def _suggest_outlier_fixes(df: pd.DataFrame, column: str) -> Tuple[int, List[Suggestion]]:
    """
    Detect outliers via IQR and return both the count and a cap-to-range suggestion.

    Returns a tuple of (outlier_count, suggestions).
    """
    if not pd.api.types.is_numeric_dtype(df[column]):
        return 0, []

    q1, q3 = df[column].quantile(0.25), df[column].quantile(0.75)
    iqr = q3 - q1
    lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    outlier_count = int(((df[column] < lower) | (df[column] > upper)).sum())

    if outlier_count == 0:
        return 0, []

    suggestion = Suggestion(
        issue_id=f"outlier_{column}_{uuid.uuid4().hex[:6]}",
        column=column,
        issue_type="Outliers",
        description=(
            f"Found {outlier_count} potential outliers outside "
            f"[{lower:.2f}, {upper:.2f}]."
        ),
        suggested_actions=[SuggestionAction(
            action_id=f"cap_outliers_{column}",
            type="CAP_OUTLIERS",
            description="Cap values to range",
            params={"column": column, "lower_bound": lower, "upper_bound": upper},
        )],
    )
    return outlier_count, [suggestion]


def _suggest_whitespace_fixes(df: pd.DataFrame, column: str) -> List[Suggestion]:
    """
    Detect leading/trailing whitespace in a string column.

    Returns a strip-whitespace suggestion when any affected values are found.
    """
    if df[column].dtype != "object":
        return []

    col_str = df[column].astype(str)
    whitespace_count = int((col_str != col_str.str.strip()).sum())
    if whitespace_count == 0:
        return []

    return [Suggestion(
        issue_id=f"ws_{column}_{uuid.uuid4().hex[:6]}",
        column=column,
        issue_type="Inconsistent Formatting",
        description=f"Found {whitespace_count} values with leading or trailing whitespace.",
        suggested_actions=[SuggestionAction(
            action_id=f"strip_whitespace_{column}",
            type="STRIP_WHITESPACE",
            description="Trim whitespace",
            params={"column": column},
        )],
    )]


def _suggest_category_fixes(df: pd.DataFrame, column: str) -> List[Suggestion]:
    """
    Detect inconsistent category labels in a low-cardinality string column.

    For example, 'New York' and 'new york' would be flagged and a standardize
    action targeting the most common form is suggested.
    """
    if df[column].dtype != "object":
        return []
    if not (1 < df[column].nunique() < 50):
        return []

    col_series = df[column].dropna().astype(str)
    normalized = col_series.str.lower().str.strip().str.replace(r"[^a-z0-9]", "", regex=True)

    if normalized.nunique() >= col_series.nunique():
        return []

    for norm_val in normalized.unique():
        original_forms = col_series[normalized == norm_val]
        if original_forms.nunique() <= 1:
            continue

        most_common = original_forms.mode()[0]
        examples = [v for v in original_forms.unique() if v != most_common][:2]
        if not examples:
            continue

        return [Suggestion(
            issue_id=f"cat_{column}_{uuid.uuid4().hex[:6]}",
            column=column,
            issue_type="Inconsistent Categories",
            description=f"Values like '{examples[0]}' could be standardized to '{most_common}'.",
            suggested_actions=[SuggestionAction(
                action_id=f"standardize_cat_{column}",
                type="STANDARDIZE_CATEGORICAL",
                description=f"Standardize to '{most_common}'",
                params={"column": column, "target_value": most_common, "method": "most_common_normalized"},
            )],
        )]

    return []


def _compute_health_score(
    null_percentage: float,
    total_outliers: int,
    total_rows: int,
    anomaly_ratio: float,
    suggestion_count: int,
) -> Tuple[float, str]:
    """
    Calculate a 0–100 health score and a matching label.

    Deductions:
        - 1.5 points per percent of null cells
        - up to 100 points for outlier density
        - up to 100 points for ML anomaly ratio
        - 0.5 points per detected issue
    """
    score = 100.0
    score -= null_percentage * 1.5
    score -= (total_outliers / total_rows * 100) if total_rows > 0 else 0
    score -= anomaly_ratio * 100
    score -= suggestion_count * 0.5
    score = max(0.0, score)

    if score > 90:
        label = "Excellent"
    elif score > 75:
        label = "Good"
    elif score > 50:
        label = "Fair"
    else:
        label = "Poor"

    return round(score, 2), label


def analyze_dataframe(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Run a full data-quality analysis on a DataFrame.

    Steps:
        1. Compute high-level stats (shape, null %, memory).
        2. Train and run the ML anomaly detector.
        3. For each column: detect outliers, missing values, whitespace issues,
           and inconsistent categories.
        4. Produce a health score, recommendations, and per-column reports.

    Returns a plain dict that maps directly onto the ScanReport schema.
    """
    total_rows = len(df)
    total_columns = len(df.columns)
    total_cells = total_rows * total_columns

    memory_mb = round(df.memory_usage(deep=True).sum() / (1024 ** 2), 2)
    null_count = int(df.isnull().sum().sum())
    null_percentage = round((null_count / total_cells) * 100, 2) if total_cells > 0 else 0.0

    detector = AnomalyDetector()
    detector.train(df)
    anomaly_result = detector.predict(df)
    anomaly_ratio = anomaly_result.get("anomaly_ratio", 0.0)

    column_reports: List[ColumnReport] = []
    all_suggestions: List[Suggestion] = []
    total_outliers = 0

    for col_name in df.columns:
        outlier_count, outlier_suggestions = _suggest_outlier_fixes(df, col_name)
        all_suggestions.extend(outlier_suggestions)
        total_outliers += outlier_count

        all_suggestions.extend(_suggest_missing_value_fixes(df, col_name))
        all_suggestions.extend(_suggest_whitespace_fixes(df, col_name))
        all_suggestions.extend(_suggest_category_fixes(df, col_name))

        if df[col_name].nunique() == 1 and total_rows > 1:
            all_suggestions.append(Suggestion(
                issue_id=f"const_{col_name}_{uuid.uuid4().hex[:6]}",
                column=col_name,
                issue_type="Low Variance",
                description=f"Column has only one unique value ('{df[col_name].iloc[0]}'). It may be redundant.",
                suggested_actions=[SuggestionAction(
                    action_id=f"drop_constant_{col_name}",
                    type="DROP_COLUMN",
                    description="Drop Column",
                    params={"column": col_name},
                )],
            ))

        report = _analyze_column(col_name, df[col_name], total_rows)
        column_reports.append(report)

    health_score, overall_health = _compute_health_score(
        null_percentage, total_outliers, total_rows, anomaly_ratio, len(all_suggestions)
    )

    summary = (
        f"The dataset has {total_rows} rows and {total_columns} columns. "
        f"Overall null percentage is {null_percentage:.2f}%. "
        f"Detected {total_outliers} potential outliers. "
        f"ML model flagged {anomaly_ratio * 100:.2f}% of rows as anomalous. "
        f"Found {len(all_suggestions)} potential data quality issues with suggested fixes."
    )

    recommendations: List[str] = []
    if null_percentage > 10:
        recommendations.append("High percentage of missing values detected. Review imputation suggestions.")
    if total_outliers > 0:
        recommendations.append("Outliers detected. Consider capping or removing them.")
    if all_suggestions:
        recommendations.append("Review the detailed suggestions below to improve data quality.")
    if not recommendations:
        recommendations.append("No major issues found. Data looks clean — proceed with analysis.")

    return {
        "total_rows": total_rows,
        "total_columns": total_columns,
        "overall_health": overall_health,
        "health_score": health_score,
        "null_percentage": null_percentage,
        "outlier_count": total_outliers,
        "anomaly_score": anomaly_ratio,
        "memory_usage_mb": memory_mb,
        "columns": column_reports,
        "summary": summary,
        "recommendations": recommendations,
        "suggestions": all_suggestions,
    }
