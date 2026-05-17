import numpy as np
import pandas as pd
import pandas as pd
from typing import List, Dict, Any, Tuple
import logging
import uuid

from app.services.ml_detector import ml_model
from app.models.schemas import ColumnReport, Suggestion, SuggestionAction

logger = logging.getLogger(__name__)


def _detect_whitespace_issues(df: pd.DataFrame, column: str) -> List[Suggestion]:
    """Detects leading/trailing whitespace in a string column."""
    suggestions = []
    if df[column].dtype == 'object':
        # Ensure all values are strings before stripping
        col_str = df[column].astype(str)
        stripped_col = col_str.str.strip()
        whitespace_count = (col_str != stripped_col).sum()
        if whitespace_count > 0:
            suggestions.append(Suggestion(
                issue_id=f"ws_{column}_{uuid.uuid4().hex[:6]}",
                column=column,
                issue_type="Inconsistent Formatting",
                description=f"Found {whitespace_count} values with leading or trailing whitespace.",
                suggested_actions=[SuggestionAction(
                    action_id=f"strip_whitespace_{column}",
                    type="STRIP_WHITESPACE",
                    description=f"Trim whitespace",
                    params={"column": column}
                )]
            ))
    return suggestions

def _detect_inconsistent_categories(df: pd.DataFrame, column: str) -> List[Suggestion]:
    """Detects similar-looking categorical values (e.g., 'New York', 'new york')."""
    suggestions = []
    if df[column].dtype == 'object' and 1 < df[column].nunique() < 50: # Heuristic for categorical
        # A copy to avoid SettingWithCopyWarning
        col_series = df[column].dropna().astype(str)
        normalized_values = col_series.str.lower().str.strip().replace(r'[^a-z0-9]', '', regex=True)
        
        if normalized_values.nunique() < col_series.nunique():
            # Find the most common original form for each normalized value
            value_map = {}
            for norm_val in normalized_values.unique():
                original_forms = col_series[normalized_values == norm_val]
                if original_forms.nunique() > 1:
                    most_common_original = original_forms.mode()[0]
                    inconsistent_examples = [v for v in original_forms.unique() if v != most_common_original][:2]
                    if inconsistent_examples:
                        value_map[norm_val] = (most_common_original, inconsistent_examples)

            if value_map:
                # For simplicity, we'll just create one suggestion for the first detected case
                first_key = next(iter(value_map))
                target_value, examples = value_map[first_key]
                suggestions.append(Suggestion(
                    issue_id=f"cat_{column}_{uuid.uuid4().hex[:6]}",
                    column=column,
                    issue_type="Inconsistent Categories",
                    description=f"Values like '{examples[0]}' could be standardized to '{target_value}'.",
                    suggested_actions=[SuggestionAction(
                        action_id=f"standardize_cat_{column}",
                        type="STANDARDIZE_CATEGORICAL",
                        description=f"Standardize to '{target_value}'",
                        params={"column": column, "target_value": target_value, "method": "most_common_normalized"}
                    )]
                ))
    return suggestions

def _detect_outliers(df: pd.DataFrame, column: str) -> Tuple[int, List[Suggestion]]:
    """Detects outliers using the IQR method and suggests capping."""
    suggestions = []
    outlier_count = 0
    if pd.api.types.is_numeric_dtype(df[column]):
        Q1 = df[column].quantile(0.25)
        Q3 = df[column].quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR

        outliers = df[(df[column] < lower_bound) | (df[column] > upper_bound)]
        outlier_count = len(outliers)

        if outlier_count > 0:
            suggestions.append(Suggestion(
                issue_id=f"outlier_{column}_{uuid.uuid4().hex[:6]}",
                column=column,
                issue_type="Outliers",
                description=f"Found {outlier_count} potential outliers outside the range [{lower_bound:.2f}, {upper_bound:.2f}].",
                suggested_actions=[SuggestionAction(
                    action_id=f"cap_outliers_{column}",
                    type="CAP_OUTLIERS",
                    description=f"Cap values to range",
                    params={"column": column, "lower_bound": lower_bound, "upper_bound": upper_bound}
                )]
            ))
    return outlier_count, suggestions

def _detect_missing_values(df: pd.DataFrame, column: str) -> List[Suggestion]:
    """Detects missing values and suggests multiple imputation strategies."""
    suggestions = []
    null_count = df[column].isnull().sum()
    if null_count == 0:
        return []

    null_percentage = (null_count / len(df)) * 100
    actions = []

    # Suggest imputation based on data type
    if pd.api.types.is_numeric_dtype(df[column]):
        median_val = df[column].median()
        actions.append(SuggestionAction(
            action_id=f"impute_median_{column}", type="IMPUTE",
            description=f"Fill with Median ({median_val:.2f})",
            params={"column": column, "strategy": "median"}
        ))
    elif pd.api.types.is_object_dtype(df[column]):
        mode_val = df[column].mode()[0] if not df[column].mode().empty else "missing"
        actions.append(SuggestionAction(
            action_id=f"impute_mode_{column}", type="IMPUTE",
            description=f"Fill with Mode ('{mode_val}')",
            params={"column": column, "strategy": "mode"}
        ))

    # If there are a lot of missing values, also suggest dropping the column
    if null_percentage > 40:
        actions.append(SuggestionAction(
            action_id=f"drop_col_missing_{column}", type="DROP_COLUMN",
            description=f"Drop Column ({null_percentage:.0f}% empty)",
            params={"column": column}
        ))
    
    suggestions.append(Suggestion(
        issue_id=f"missing_{column}_{uuid.uuid4().hex[:6]}",
        column=column,
        issue_type="Missing Values",
        description=f"Column has {null_count} missing values ({null_percentage:.1f}%).",
        suggested_actions=actions
    ))
    return suggestions


def analyze_dataframe(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Performs a comprehensive analysis of a Pandas DataFrame, detecting a wide
    range of data quality issues and generating actionable suggestions.
    """
    total_rows = len(df)
    total_columns = len(df.columns)
    total_cells = total_rows * total_columns
    
    memory_usage_mb = df.memory_usage(deep=True).sum() / (1024 * 1024)
    null_count = int(df.isnull().sum().sum())
    null_percentage = (null_count / total_cells) * 100 if total_cells > 0 else 0

    column_reports: List[ColumnReport] = []
    all_suggestions: List[Suggestion] = []
    total_outliers = 0

    ml_model.train(df)
    anomaly_results = ml_model.predict(df)
    anomaly_score = anomaly_results.get("anomaly_ratio", 0.0)

    for col_name in df.columns:
        col = df[col_name]
        
        outlier_count, outlier_suggestions = _detect_outliers(df, col_name)
        all_suggestions.extend(outlier_suggestions)
        total_outliers += outlier_count

        all_suggestions.extend(_detect_missing_values(df, col_name))
        all_suggestions.extend(_detect_whitespace_issues(df, col_name))
        all_suggestions.extend(_detect_inconsistent_categories(df, col_name))

        unique_count = int(col.nunique())
        if unique_count == 1 and total_rows > 1:
            all_suggestions.append(Suggestion(
                issue_id=f"const_{col_name}_{uuid.uuid4().hex[:6]}",
                column=col_name, issue_type="Low Variance",
                description=f"Column has only one unique value ('{col.iloc[0]}'). It might be redundant.",
                suggested_actions=[SuggestionAction(
                    action_id=f"drop_constant_{col_name}", type="DROP_COLUMN",
                    description=f"Drop Column", params={"column": col_name}
                )]
            ))

        report = ColumnReport(
            name=col_name, data_type=str(col.dtype),
            null_count=int(col.isnull().sum()),
            null_percentage=round(col.isnull().mean() * 100, 2),
            unique_values=unique_count,
            sample_values=[
                v.item() if isinstance(v, np.generic) else v
                for v in col.dropna().unique()[:5]
            ],
            outlier_count=outlier_count,
        )

        if pd.api.types.is_numeric_dtype(col.dtype):
            clean_col = col.dropna()
            if not clean_col.empty:
                report.min_value = float(clean_col.min())
                report.max_value = float(clean_col.max())
                report.mean_value = float(clean_col.mean())

        column_reports.append(report)

    health_score = 100
    health_score -= null_percentage * 1.5
    health_score -= (total_outliers / total_rows) * 100 if total_rows > 0 else 0
    health_score -= anomaly_score * 100
    health_score -= len(all_suggestions) * 0.5
    health_score = max(0, health_score)

    if health_score > 90: overall_health = "Excellent"
    elif health_score > 75: overall_health = "Good"
    elif health_score > 50: overall_health = "Fair"
    else: overall_health = "Poor"

    summary_parts = [
        f"The dataset has {total_rows} rows and {total_columns} columns.",
        f"Overall null percentage is {null_percentage:.2f}%.",
        f"Detected {total_outliers} potential outliers.",
        f"ML model flagged {anomaly_score*100:.2f}% of rows as anomalous.",
        f"Found {len(all_suggestions)} potential data quality issues with suggested fixes."
    ]
    summary = " ".join(summary_parts)

    recommendations = []
    if null_percentage > 10:
        recommendations.append("High percentage of missing values. Review imputation suggestions.")
    if total_outliers > 0:
        recommendations.append("Outliers detected. Consider capping or removing them.")
    if len(all_suggestions) > 0:
        recommendations.append("Review the detailed suggestions to improve data quality.")
    if not recommendations:
        recommendations.append("Data looks relatively clean. Proceed with analysis.")

    return {
        "total_rows": total_rows,
        "total_columns": total_columns,
        "overall_health": overall_health,
        "health_score": round(health_score, 2),
        "null_percentage": round(null_percentage, 2),
        "outlier_count": total_outliers,
        "anomaly_score": anomaly_score,
        "memory_usage_mb": round(memory_usage_mb, 2),
        "columns": column_reports,
        "summary": summary,
        "recommendations": recommendations,
        "suggestions": all_suggestions,
    }
