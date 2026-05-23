from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from datetime import datetime
from pathlib import Path
from typing import List
import tempfile
import os
import time
import uuid
import gc
import pandas as pd
import logging
import io

from app.models.schemas import ScanReport, Dataset
from app.services.analyzer import analyze_dataframe
from app.services.validator import validate_extension, validate_size, validate_csv
from app.services.session_store import save_session

router = APIRouter()
logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).parent.parent.parent / "data"
# Still used for validate_csv which needs a file path
_TEMP_DIR = Path(tempfile.gettempdir()) / "datasnoop_uploads"
_TEMP_DIR.mkdir(exist_ok=True)


def cleanup_file(path: str):
    """Utility to remove a temp file in the background."""
    try:
        os.unlink(path)
    except FileNotFoundError:
        pass


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
    session_id = str(uuid.uuid4())
    save_session(session_id, df)
    analysis = analyze_dataframe(df)

    return ScanReport(
        success=True,
        dataset_name="sample.csv (built-in demo)",
        file_id=session_id,
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
            row_count = sum(1 for _ in open(f)) - 1
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
    session_id = str(uuid.uuid4())
    save_session(session_id, df)
    analysis = analyze_dataframe(df)

    return ScanReport(
        success=True,
        dataset_name=f"{name}.csv",
        file_id=session_id,
        timestamp=datetime.now(),
        processing_time_ms=int((time.time() - start) * 1000),
        **analysis,
    )


# ── File upload ───────────────────────────────────────────────────────────────

@router.post("/api/v1/scan/file", response_model=ScanReport, summary="Upload & analyze your CSV")
async def scan_file(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """
    Upload a CSV file and DataSnoop will analyze it — checking for missing values,
    outliers, and overall data quality. You'll get a per-column breakdown and
    plain-English recommendations.
    """
    ok, err = validate_extension(file.filename or "")
    if not ok:
        raise HTTPException(status_code=400, detail=err)

    content = await file.read()

    ok, err = validate_size(content)
    if not ok:
        raise HTTPException(status_code=413, detail=err)

    start = time.time()

    # Write temp file only so validate_csv (which needs a path) can run.
    # The DataFrame is stored in memory — the temp file is deleted right after.
    tmp_path = str(_TEMP_DIR / f"{uuid.uuid4()}.csv")
    Path(tmp_path).write_bytes(content)

    try:
        ok, err = validate_csv(tmp_path)
        if not ok:
            raise HTTPException(status_code=400, detail=err)

        # Read in chunks to handle large files without blowing memory at once
        chunks = []
        for chunk in pd.read_csv(tmp_path, chunksize=5000):
            chunks.append(chunk)
            gc.collect()

        df = pd.concat(chunks, ignore_index=True)

        # Store in session — this is now the source of truth for cleaning
        session_id = str(uuid.uuid4())
        save_session(session_id, df)

        analysis = analyze_dataframe(df)

        return ScanReport(
            success=True,
            dataset_name=file.filename or "upload.csv",
            file_id=session_id,  # frontend uses this as session_id in /clean and /download
            timestamp=datetime.now(),
            processing_time_ms=int((time.time() - start) * 1000),
            **analysis,
        )

    except HTTPException:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise
    except Exception as e:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise HTTPException(status_code=500, detail=f"Something went wrong reading your file: {e}")
    finally:
        # Temp file is only needed for validation — delete it immediately
        background_tasks.add_task(cleanup_file, tmp_path)
