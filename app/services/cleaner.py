import pandas as pd
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


def apply_cleaning_actions(df: pd.DataFrame, actions: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Applies a list of cleaning actions to a DataFrame.

    Args:
        df: The input DataFrame.
        actions: A list of action objects, where each object defines a cleaning step.
                 Example: [{"type": "IMPUTE", "params": {"column": "age", "strategy": "median"}}]

    Returns:
        The cleaned DataFrame.
    """
    cleaned_df = df.copy()

    for action in actions:
        action_type = action.get("type")
        params = action.get("params", {})
        column = params.get("column")

        logger.info(f"Applying action: {action_type} on column '{column}'")

        try:
            if action_type == "IMPUTE":
                if params["strategy"] == "median":
                    fill_value = cleaned_df[column].median()
                    cleaned_df[column] = cleaned_df[column].fillna(fill_value)
                elif params["strategy"] == "mode":
                    fill_value = cleaned_df[column].mode()[0]
                    cleaned_df[column] = cleaned_df[column].fillna(fill_value)
                elif params["strategy"] == "mean":
                    fill_value = cleaned_df[column].mean()
                    cleaned_df[column] = cleaned_df[column].fillna(fill_value)

            elif action_type == "STRIP_WHITESPACE":
                if pd.api.types.is_object_dtype(cleaned_df[column]):
                    cleaned_df[column] = cleaned_df[column].str.strip()

            elif action_type == "CAP_OUTLIERS":
                lower = params.get("lower_bound")
                upper = params.get("upper_bound")
                cleaned_df[column] = cleaned_df[column].clip(lower=lower, upper=upper)
            
            elif action_type == "STANDARDIZE_CATEGORICAL":
                # This is a simplified version. A more robust one would use the `method` param.
                target_value = params.get("target_value")
                normalized_target = str(target_value).lower().strip().replace(r'[^a-z0-9]', '')
                
                def standardize(val):
                    norm_val = str(val).lower().strip().replace(r'[^a-z0-9]', '')
                    return target_value if norm_val == normalized_target else val
                
                cleaned_df[column] = cleaned_df[column].apply(standardize)

            elif action_type == "DROP_COLUMN":
                cleaned_df.drop(columns=[column], inplace=True)

        except Exception as e:
            logger.error(f"Failed to apply action {action} on column {column}: {e}")
            # Continue to next action

    return cleaned_df