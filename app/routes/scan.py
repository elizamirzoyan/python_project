"""
Scan endpoints — upload a CSV or analyse a local file and get back a full
data-quality report with per-column stats, issue suggestions, and a health score.
"""

import gc
import io
import logging
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import List

import pandas as pd
from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile

from app.models.schemas import Dataset, ScanReport
from app.services.analyzer import analyze_dataframe
from app.services.session_store import save_session
from app.services.validator import validate_csv_bytes, validate_extension, validate_size

router = APIRouter()
logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).parent.parent.parent / "data"


def _build_scan_report(
    df: pd.DataFrame,
    dataset_name: str,
    start_time: float,
    source_url: str | None = None,
) -> ScanReport:
    """
    Run analysis on df and wrap the result in a ScanReport.

    Also saves the DataFrame to the session store so clean/download
    endpoints can access it later.
    """
    session_id = str(uuid.uuid4())
    save_session(session_id, df)
    analysis = analyze_dataframe(df)

    return ScanReport(
        success=True,
        dataset_name=dataset_name,
        file_id=session_id,
        timestamp=datetime.now(),
        processing_time_ms=int((time.time() - start_time) * 1000),
        source_url=source_url,
        rows_fetched=len(df) if source_url else None,
        **analysis,
    )


@router.get(
    "/api/v1/demo",
    response_model=ScanReport,
    summary="Try DataSnoop on sample data",
)
async def demo() -> ScanReport:
    """
    Run a full analysis on the built-in sample dataset.

    No file upload needed — great for a quick first look at what DataSnoop produces.
    """
    sample_path = _DATA_DIR / "sample.csv"
    if not sample_path.exists():
        raise HTTPException(status_code=404, detail="sample.csv not found in data/.")

    start = time.time()
    df = pd.read_csv(sample_path)
    return _build_scan_report(df, "sample.csv (built-in demo)", start)


@router.get(
    "/api/v1/local-datasets",
    response_model=List[Dataset],
    summary="List local CSV files",
)
async def list_local_datasets() -> List[Dataset]:
    """
    Return metadata for every CSV file in the data/ directory.

    Run ``scripts/generate_test_data.py`` first to populate the folder with
    benchmark datasets if it is empty.
    """
    datasets = []
    for csv_file in sorted(_DATA_DIR.glob("*.csv")):
        size_kb = round(csv_file.stat().st_size / 1024, 1)
        try:
            peek = pd.read_csv(csv_file, nrows=1)
            col_count = len(peek.columns)
            row_count = sum(1 for _ in open(csv_file)) - 1
        except Exception:
            col_count, row_count = 0, 0

        datasets.append(Dataset(
            id=csv_file.stem,
            name=csv_file.name,
            description=f"{col_count} columns · ~{row_count} rows · {size_kb} KB on disk",
            category="Local File",
            estimated_rows=str(row_count),
        ))
    return datasets


@router.get(
    "/api/v1/local-datasets/{name}",
    response_model=ScanReport,
    summary="Analyze a local CSV file",
)
async def analyze_local_dataset(name: str) -> ScanReport:
    """
    Analyze any CSV in the data/ directory by name (without the .csv extension).

    Example: GET /api/v1/local-datasets/employees
    """
    csv_path = _DATA_DIR / f"{name}.csv"
    if not csv_path.exists():
        available = [f.stem for f in sorted(_DATA_DIR.glob("*.csv"))]
        raise HTTPException(
            status_code=404,
            detail=f"'{name}.csv' not found. Available files: {available}",
        )

    start = time.time()
    df = pd.read_csv(csv_path)
    return _build_scan_report(df, f"{name}.csv", start)


@router.post(
    "/api/v1/scan/file",
    response_model=ScanReport,
    summary="Upload and analyze a CSV",
)
async def scan_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
) -> ScanReport:
    """
    Upload a CSV file and receive a full data-quality report.

    The file is read in chunks to handle large uploads without exhausting RAM.
    A session ID returned in ``file_id`` can be passed to the clean and download
    endpoints to apply fixes and retrieve the result.
    """
    ok, err = validate_extension(file.filename or "")
    if not ok:
        raise HTTPException(status_code=400, detail=err)

    content = await file.read()

    ok, err = validate_size(content)
    if not ok:
        raise HTTPException(status_code=413, detail=err)

    ok, err = validate_csv_bytes(content)
    if not ok:
        raise HTTPException(status_code=400, detail=err)

    start = time.time()

    chunks = []
    for chunk in pd.read_csv(io.BytesIO(content), chunksize=5_000):
        chunks.append(chunk)
        gc.collect()

    df = pd.concat(chunks, ignore_index=True)
    return _build_scan_report(df, file.filename or "upload.csv", start)
