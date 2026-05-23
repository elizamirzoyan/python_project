from fastapi import APIRouter, HTTPException, Body
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any
from pathlib import Path
import tempfile
import pandas as pd
import io

from app.services.cleaner import apply_cleaning_actions

router = APIRouter()

TEMP_DIR = Path(tempfile.gettempdir()) / "datasnoop_uploads"
TEMP_DIR.mkdir(parents=True, exist_ok=True)

def get_upload_path(file_id: str) -> Path:
    return TEMP_DIR / f"{file_id}.csv"


class CleanRequest(BaseModel):
    file_id: str
    actions: List[Dict[str, Any]]


@router.post("/api/v1/clean/file", summary="Apply fixes and download cleaned file")
async def clean_file(request: CleanRequest):
    """
    Provide the `file_id` from a scan and a list of `suggested_action` objects
    to apply the fixes. The endpoint returns the cleaned CSV file for download.
    """
    file_path = get_upload_path(request.file_id)

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File ID not found or has expired. Please re-upload the file.")

    if not request.actions:
        raise HTTPException(status_code=400, detail="No cleaning actions provided.")

    try:
        df = pd.read_csv(file_path)
        cleaned_df = apply_cleaning_actions(df, request.actions)

        # Stream the cleaned data back to the user
        stream = io.StringIO()
        cleaned_df.to_csv(stream, index=False)
        response = StreamingResponse(iter([stream.getvalue()]), media_type="text/csv")
        response.headers["Content-Disposition"] = f"attachment; filename=cleaned_{request.file_id}.csv"
        return response

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Original file not found for cleaning.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred during the cleaning process: {e}")