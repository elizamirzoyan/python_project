from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any
import pandas as pd
import io

from app.services.cleaner import apply_cleaning_actions
from app.services.session_store import get_session, update_session, delete_session

router = APIRouter()


def _require_session(session_id: str) -> pd.DataFrame:
    """Fetch a session or raise a 404 with a clear message."""
    df = get_session(session_id)
    if df is None:
        raise HTTPException(
            status_code=404,
            detail="Session not found or expired. Please re-upload your file.",
        )
    return df


# ── Models ────────────────────────────────────────────────────────────────────

class CleanRequest(BaseModel):
    session_id: str  # previously file_id — returned as file_id from /scan/file
    actions: List[Dict[str, Any]]


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/api/v1/clean", summary="Apply cleaning actions and update session")
async def clean_file(request: CleanRequest):
    """
    Apply a list of cleaning actions to the session DataFrame.
    The session is updated in place so subsequent calls build on previous ones.
    Returns a preview of the first 50 rows after cleaning.
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
            "preview": cleaned_df.head(50).to_dict(orient="records"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cleaning failed: {e}")


@router.get("/api/v1/download/{session_id}", summary="Download the final cleaned CSV")
async def download_file(session_id: str):
    """
    Stream the cleaned DataFrame as a CSV file and remove the session from memory.
    """
    df = _require_session(session_id)

    stream = io.StringIO()
    df.to_csv(stream, index=False)
    delete_session(session_id)

    response = StreamingResponse(iter([stream.getvalue()]), media_type="text/csv")
    response.headers["Content-Disposition"] = f"attachment; filename=cleaned_{session_id}.csv"
    return response


@router.delete("/api/v1/session/{session_id}", summary="Discard a session without downloading")
async def discard_session(session_id: str):
    """
    Explicitly remove a session if the user cancels without downloading.
    Safe to call even if the session has already expired.
    """
    delete_session(session_id)
    return {"detail": "Session discarded."}
