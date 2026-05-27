from pydantic import BaseModel
from typing import List, Optional, Any, Dict
from datetime import datetime


class SuggestionAction(BaseModel):
    """A single, executable fix that can be applied to a column."""

    action_id: str
    type: str
    description: str
    params: Dict[str, Any]


class ColumnReport(BaseModel):
    """Quality metrics for one column in the dataset."""

    name: str
    data_type: str
    null_count: int
    null_percentage: float
    unique_values: int
    sample_values: List[Any]
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    mean_value: Optional[float] = None
    outlier_count: Optional[int] = None


class Suggestion(BaseModel):
    """A detected data quality issue together with one or more suggested fixes."""

    issue_id: str
    column: str
    issue_type: str
    description: str
    suggested_actions: List[SuggestionAction]


class ScanReport(BaseModel):
    """The full analysis report returned by every scan endpoint."""

    success: bool
    dataset_name: str
    timestamp: datetime
    total_rows: int
    total_columns: int
    overall_health: str
    health_score: float
    null_percentage: float
    outlier_count: int
    anomaly_score: float
    processing_time_ms: int
    memory_usage_mb: float
    columns: List[ColumnReport]
    summary: str
    recommendations: List[str]
    suggestions: List[Suggestion] = []
    source_url: Optional[str] = None
    rows_fetched: Optional[int] = None
    file_id: Optional[str] = None


class Dataset(BaseModel):
    """Metadata for a built-in or local dataset."""

    id: str
    name: str
    description: str
    category: str
    estimated_rows: str
