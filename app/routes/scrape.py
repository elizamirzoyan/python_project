from fastapi import APIRouter, HTTPException
from datetime import datetime
from typing import List
import time
import logging

from app.models.schemas import ScanReport, Dataset
from app.services.scraper import BUILT_IN_DATASETS, fetch_dataset
from app.services.analyzer import analyze_dataframe

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/api/v1/datasets", response_model=List[Dataset], summary="Browse available datasets")
async def list_datasets():
    """
    See all built-in datasets you can fetch and analyze — no file upload needed.
    Pick one you like, then call GET /api/v1/scrape/{id} to analyze it.
    """
    return [
        Dataset(
            id=k,
            name=v["name"],
            description=v["description"],
            category=v["category"],
            estimated_rows=v["estimated_rows"],
        )
        for k, v in BUILT_IN_DATASETS.items()
    ]


@router.get("/api/v1/scrape/{dataset_id}", response_model=ScanReport, summary="Fetch & analyze a live dataset")
async def scrape_dataset(dataset_id: str):
    """
    Fetch one of the built-in datasets live from the web and run a full DataSnoop analysis on it.

    Available dataset IDs: **crypto**, **countries**, **people**, **posts**, **todos**

    Not sure which to pick? Call GET /api/v1/datasets first to see descriptions.
    """
    if dataset_id not in BUILT_IN_DATASETS:
        available = list(BUILT_IN_DATASETS.keys())
        raise HTTPException(
            status_code=404,
            detail=f"'{dataset_id}' is not a known dataset. Available options: {available}",
        )

    start_time = time.time()

    try:
        df, source_url = await fetch_dataset(dataset_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not fetch the dataset: {e}")

    if df.empty:
        raise HTTPException(status_code=502, detail="The fetched dataset came back empty.")

    analysis = analyze_dataframe(df)

    return ScanReport(
        success=True,
        dataset_name=BUILT_IN_DATASETS[dataset_id]["name"],
        timestamp=datetime.now(),
        processing_time_ms=int((time.time() - start_time) * 1000),
        source_url=source_url,
        rows_fetched=len(df),
        **analysis,
    )
