from fastapi import APIRouter, UploadFile, File, HTTPException
from datetime import datetime
from pathlib import Path
from typing import List
import tempfile
import os
import time
import gc
import pandas as pd
import logging

from app.models.schemas import ScanReport, Dataset
from app.services.analyzer import analyze_dataframe
from app.services.validator import validate_extension, validate_size, validate_csv

router = APIRouter()
logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).parent.parent.parent / "data"


# ── Demo ──────────────────────────────────────────────────────────────────────

@router.get("/api/v1/demo", response_model=ScanReport, summary="Try DataSnoop on sample data")
async def demo():
    """
    No file needed — run DataSnoop on the built-in sample dataset to see what the
    output looks like. Perfect for a first look.
    """
    sample = _DATA_DIR / "sample.csv"
    if not sample.exists():
        raise HTTPException(status_code=404, detail="sample.csv not found in data/")

    start = time.time()
    df = pd.read_csv(sample)
    analysis = analyze_dataframe(df)

    return ScanReport(
        success=True,
        dataset_name="sample.csv (built-in demo)",
        timestamp=datetime.now(),
        processing_time_ms=int((time.time() - start) * 1000),
        **analysis,
    )


# ── Local datasets ────────────────────────────────────────────────────────────

@router.get("/api/v1/local-datasets", response_model=List[Dataset], summary="List local CSV files")
async def list_local_datasets():
    """
    See all CSV files available in the data/ folder.
    Run scripts/generate_test_data.py first to populate it with benchmark datasets.
    """
    files = []
    for f in sorted(_DATA_DIR.glob("*.csv")):
        size_kb = round(f.stat().st_size / 1024, 1)
        try:
            peek = pd.read_csv(f, nrows=1)
            cols = len(peek.columns)
            row_count = sum(1 for _ in open(f)) - 1  # fast row count
        except Exception:
            cols, row_count = 0, 0

        files.append(Dataset(
            id=f.stem,
            name=f.name,
            description=f"{cols} columns · ~{row_count} rows · {size_kb} KB on disk",
            category="Local File",
            estimated_rows=str(row_count),
        ))
    return files


@router.get(
    "/api/v1/local-datasets/{name}",
    response_model=ScanReport,
    summary="Analyze a local CSV file",
)
async def analyze_local_dataset(name: str):
    """
    Analyze any CSV file in the data/ folder by name (no .csv extension needed).

    Example: /api/v1/local-datasets/employees
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
    analysis = analyze_dataframe(df)

    return ScanReport(
        success=True,
        dataset_name=f"{name}.csv",
        timestamp=datetime.now(),
        processing_time_ms=int((time.time() - start) * 1000),
        **analysis,
    )


# ── File upload ───────────────────────────────────────────────────────────────

@router.post("/api/v1/scan/file", response_model=ScanReport, summary="Upload & analyze your CSV")
async def scan_file(file: UploadFile = File(...)):
    """
    Upload a CSV file and DataSnoop will analyze it — checking for missing values,
    outliers, and overall data quality. You'll get a per-column breakdown and
    plain-English recommendations.
    """
    # Validate extension
    ok, err = validate_extension(file.filename or "")
    if not ok:
        raise HTTPException(status_code=400, detail=err)

    content = await file.read()

    # Validate size
    ok, err = validate_size(content)
    if not ok:
        raise HTTPException(status_code=413, detail=err)

    start = time.time()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # Validate CSV structure
        ok, err = validate_csv(tmp_path)
        if not ok:
            raise HTTPException(status_code=400, detail=err)

        chunks = []
        for chunk in pd.read_csv(tmp_path, chunksize=5000):
            chunks.append(chunk)
            gc.collect()

        df = pd.concat(chunks, ignore_index=True)
        analysis = analyze_dataframe(df)

        return ScanReport(
            success=True,
            dataset_name=file.filename or "upload.csv",
            timestamp=datetime.now(),
            processing_time_ms=int((time.time() - start) * 1000),
            **analysis,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Something went wrong reading your file: {e}")
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
