"""
Scrape endpoints — fetch a live dataset from the web and run a quality analysis on it.

Scraped datasets are stored in the session store just like uploaded files, so
the same clean and download endpoints work for them too.
"""

import logging
import time
import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, HTTPException

from app.models.schemas import Dataset, ScanReport
from app.services.analyzer import analyze_dataframe
from app.services.scraper import BUILT_IN_DATASETS, fetch_dataset
from app.services.session_store import save_session

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get(
    "/api/v1/datasets",
    response_model=List[Dataset],
    summary="Browse available live datasets",
)
async def list_datasets() -> List[Dataset]:
    """
    Return the catalogue of built-in datasets that can be fetched and analysed
    without uploading a file.

    Pick an ID from this list and pass it to GET /api/v1/scrape/{id}.
    """
    return [
        Dataset(
            id=dataset_id,
            name=meta["name"],
            description=meta["description"],
            category=meta["category"],
            estimated_rows=meta["estimated_rows"],
        )
        for dataset_id, meta in BUILT_IN_DATASETS.items()
    ]


@router.get(
    "/api/v1/scrape/{dataset_id}",
    response_model=ScanReport,
    summary="Fetch and analyze a live dataset",
)
async def scrape_dataset(dataset_id: str) -> ScanReport:
    """
    Fetch one of the built-in datasets live from the web and run a full
    DataSnoop analysis on it.

    The resulting DataFrame is stored in the session store, so the ``file_id``
    in the response can be passed directly to the clean and download endpoints.

    Available IDs: crypto, countries, people, posts, todos, products, spacex,
    nutrition, quotes. Call GET /api/v1/datasets to see descriptions.
    """
    if dataset_id not in BUILT_IN_DATASETS:
        raise HTTPException(
            status_code=404,
            detail=(
                f"'{dataset_id}' is not a known dataset. "
                f"Available: {list(BUILT_IN_DATASETS.keys())}"
            ),
        )

    start = time.time()

    try:
        df, source_url = await fetch_dataset(dataset_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Could not fetch the dataset: {exc}")

    if df.empty:
        raise HTTPException(status_code=502, detail="The fetched dataset came back empty.")

    session_id = str(uuid.uuid4())
    save_session(session_id, df)
    analysis = analyze_dataframe(df)

    return ScanReport(
        success=True,
        dataset_name=BUILT_IN_DATASETS[dataset_id]["name"],
        file_id=session_id,
        timestamp=datetime.now(),
        processing_time_ms=int((time.time() - start) * 1000),
        source_url=source_url,
        rows_fetched=len(df),
        **analysis,
    )
