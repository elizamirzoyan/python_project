from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import datetime


class ColumnReport(BaseModel):
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


class ScanReport(BaseModel):
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
    # Populated when data comes from a web scrape
    source_url: Optional[str] = None
    rows_fetched: Optional[int] = None


class Dataset(BaseModel):
    id: str
    name: str
    description: str
    category: str
    estimated_rows: str
