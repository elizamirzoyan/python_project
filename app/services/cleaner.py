import logging
from typing import Any, Dict, List

import pandas as pd

logger = logging.getLogger(__name__)


def apply_cleaning_actions(df: pd.DataFrame, actions: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Apply a sequence of cleaning actions to a DataFrame and return the result.

    Each action is a dict with at minimum a ``type`` key and a ``params`` sub-dict
    that must contain a ``column`` key. Unrecognised action types are skipped with
    a warning rather than raising, so a bad action never blocks the rest of the
    pipeline.

    Supported action types:
        IMPUTE                  — fill nulls (strategy: median | mode | mean)
        STRIP_WHITESPACE        — strip leading/trailing whitespace from strings
        CAP_OUTLIERS            — clip values to [lower_bound, upper_bound]
        STANDARDIZE_CATEGORICAL — normalise inconsistent category labels
        DROP_COLUMN             — remove the column entirely

    Args:
        df:      The source DataFrame (not mutated).
        actions: List of action dicts, typically sourced from the suggestions API.

    Returns:
        A new DataFrame with all valid actions applied.
    """
    cleaned = df.copy()

    for action in actions:
        action_type = action.get("type")
        params = action.get("params", {})
        column = params.get("column")

        logger.info("Applying action '%s' on column '%s'", action_type, column)

        try:
            if action_type == "IMPUTE":
                strategy = params.get("strategy", "median")
                if strategy == "median":
                    fill_value = cleaned[column].median()
                elif strategy == "mode":
                    fill_value = cleaned[column].mode()[0]
                elif strategy == "mean":
                    fill_value = cleaned[column].mean()
                else:
                    logger.warning("Unknown imputation strategy '%s'; skipping.", strategy)
                    continue
                cleaned[column] = cleaned[column].fillna(fill_value)

            elif action_type == "STRIP_WHITESPACE":
                if pd.api.types.is_object_dtype(cleaned[column]):
                    cleaned[column] = cleaned[column].str.strip()

            elif action_type == "CAP_OUTLIERS":
                lower = params.get("lower_bound")
                upper = params.get("upper_bound")
                cleaned[column] = cleaned[column].clip(lower=lower, upper=upper)

            elif action_type == "STANDARDIZE_CATEGORICAL":
                target_value = params.get("target_value", "")
                normalized_target = (
                    str(target_value).lower().strip()
                )

                def _standardize(val: Any) -> Any:
                    if pd.isna(val):
                        return val
                    return target_value if str(val).lower().strip() == normalized_target else val

                cleaned[column] = cleaned[column].apply(_standardize)

            elif action_type == "DROP_COLUMN":
                cleaned.drop(columns=[column], inplace=True)

            else:
                logger.warning("Unrecognised action type '%s'; skipping.", action_type)

        except Exception as exc:
            logger.error("Failed to apply action %s on column '%s': %s", action_type, column, exc)

    return cleaned
