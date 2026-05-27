"""
Clean and download endpoints.

These endpoints operate on DataFrames that were stored in the session store
during a previous scan call. This means fixes work identically whether the
data came from an uploaded file, a local dataset, or a live web scrape.
"""

import io
import logging
import math
from typing import Any, Dict, List

import pandas as pd
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.services.cleaner import apply_cleaning_actions
from app.services.session_store import delete_session, get_session, update_session

router = APIRouter()
logger = logging.getLogger(__name__)


class CleanRequest(BaseModel):
    """Request body for the clean endpoint."""

    session_id: str
    actions: List[Dict[str, Any]]


def _sanitize_for_json(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Convert the first 50 rows of a DataFrame to a JSON-safe list of dicts.

    Replaces float NaN and Inf values with None so FastAPI can serialise
    the response without errors.
    """
    raw = df.head(50).to_dict(orient="records")
    return [
        {
            key: None if isinstance(val, float) and (math.isnan(val) or math.isinf(val)) else val
            for key, val in row.items()
        }
        for row in raw
    ]


def _require_session(session_id: str) -> pd.DataFrame:
    """
    Look up a session and raise a 404 if it is not found.

    Args:
        session_id: The UUID returned as file_id from a scan endpoint.

    Returns:
        The DataFrame stored for this session.

    Raises:
        HTTPException 404 if the session does not exist.
    """
    df = get_session(session_id)
    if df is None:
        raise HTTPException(
            status_code=404,
            detail="Session not found or expired. Please re-upload or re-scan your file.",
        )
    return df


@router.post("/api/v1/clean", summary="Apply cleaning actions and update session")
async def clean_file(request: CleanRequest) -> Dict[str, Any]:
    """
    Apply one or more cleaning actions to the session DataFrame.

    The session is updated in place so multiple sequential calls build on
    each other. Returns a preview of the first 50 rows after cleaning.

    The ``session_id`` must match the ``file_id`` returned by any scan endpoint,
    including scrape results.
    """
    if not request.actions:
        raise HTTPException(status_code=400, detail="No cleaning actions provided.")

    df = _require_session(request.session_id)

    try:
        cleaned_df = apply_cleaning_actions(df, request.actions)
        update_session(request.session_id, cleaned_df)

        return {
            "session_id": request.session_id,
            "rows": len(cleaned_df),
            "columns": list(cleaned_df.columns),
            "preview": _sanitize_for_json(cleaned_df),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Cleaning failed: {exc}")


@router.get(
    "/api/v1/download/{session_id}",
    summary="Download the cleaned CSV",
)
async def download_file(session_id: str) -> StreamingResponse:
    """
    Stream the cleaned DataFrame as a CSV file and remove the session from memory.

    Call this once all desired cleaning actions have been applied.
    """
    df = _require_session(session_id)

    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    delete_session(session_id)

    response = StreamingResponse(iter([buffer.getvalue()]), media_type="text/csv")
    response.headers["Content-Disposition"] = f"attachment; filename=cleaned_{session_id}.csv"
    return response


@router.delete(
    "/api/v1/session/{session_id}",
    summary="Discard a session without downloading",
)
async def discard_session(session_id: str) -> Dict[str, str]:
    """
    Explicitly remove a session if the user cancels without downloading.

    Safe to call even if the session has already expired.
    """
    delete_session(session_id)
    return {"detail": "Session discarded."}
