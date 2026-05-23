from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any
import pandas as pd
import io
import uuid

from app.services.cleaner import apply_cleaning_actions

router = APIRouter()

# --- In-memory session store ---
_sessions: dict[str, pd.DataFrame] = {}


def _get_session(session_id: str) -> pd.DataFrame:
    df = _sessions.get(session_id)
    if df is None:
        raise HTTPException(
            status_code=404,
            detail="Session not found or expired. Please re-upload the file."
        )
    return df


# --- Models ---

class CleanRequest(BaseModel):
    session_id: str
    actions: List[Dict[str, Any]]


# --- Endpoints ---

@router.post("/api/v1/session", summary="Create a cleaning session from an uploaded DataFrame")
async def create_session(file_data: Dict[str, Any]):
    """
    Accepts JSON-encoded records and stores them as a session.
    Returns a session_id to use in subsequent clean/download calls.
    """
    try:
        df = pd.DataFrame(file_data["records"])
        session_id = str(uuid.uuid4())
        _sessions[session_id] = df
        return {"session_id": session_id, "rows": len(df), "columns": list(df.columns)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create session: {e}")


@router.post("/api/v1/clean", summary="Apply cleaning actions and update session")
async def clean_file(request: CleanRequest):
    """
    Applies the selected cleaning actions to the session DataFrame.
    Updates the session in place and returns a preview of the cleaned data.
    """
    if not request.actions:
        raise HTTPException(status_code=400, detail="No cleaning actions provided.")

    df = _get_session(request.session_id)

    try:
        cleaned_df = apply_cleaning_actions(df, request.actions)
        _sessions[request.session_id] = cleaned_df  # overwrite with cleaned version

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
    Streams the cleaned DataFrame as a CSV file and removes the session.
    """
    df = _get_session(session_id)

    stream = io.StringIO()
    df.to_csv(stream, index=False)
    del _sessions[session_id]  # cleanup after download

    response = StreamingResponse(iter([stream.getvalue()]), media_type="text/csv")
    response.headers["Content-Disposition"] = f"attachment; filename=cleaned_{session_id}.csv"
    return response


@router.delete("/api/v1/session/{session_id}", summary="Discard a session without downloading")
async def discard_session(session_id: str):
    """
    Explicitly cleans up a session if the user cancels without downloading.
    """
    _sessions.pop(session_id, None)
    return {"detail": "Session discarded."}