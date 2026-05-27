"""
Input validation helpers for uploaded CSV files.

All functions return a (is_valid, error_message) tuple so callers can decide
how to surface the error without coupling validation to FastAPI directly.
"""

import io
from pathlib import Path
from typing import Optional, Tuple

import pandas as pd

from app.config import settings

SUPPORTED_EXTENSIONS = {".csv"}


def validate_extension(filename: str) -> Tuple[bool, Optional[str]]:
    """
    Check that the uploaded file has a supported extension.

    Args:
        filename: The original filename provided by the client.

    Returns:
        (True, None) on success; (False, error_message) otherwise.
    """
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        return False, f"'{suffix}' files are not supported. Please upload a .csv file."
    return True, None


def validate_size(content: bytes) -> Tuple[bool, Optional[str]]:
    """
    Ensure the raw file bytes do not exceed the configured size limit.

    Args:
        content: The raw bytes read from the upload.

    Returns:
        (True, None) on success; (False, error_message) otherwise.
    """
    size_mb = len(content) / (1024 * 1024)
    if size_mb > settings.MAX_FILE_SIZE_MB:
        return False, f"File is {size_mb:.1f} MB — the limit is {settings.MAX_FILE_SIZE_MB} MB."
    return True, None


def validate_csv_bytes(content: bytes) -> Tuple[bool, Optional[str]]:
    """
    Attempt to parse the first few rows of a CSV from raw bytes.

    This avoids the need to write a temporary file to disk. Checks that the CSV
    is readable, non-empty, and within the column limit.

    Args:
        content: Raw CSV bytes.

    Returns:
        (True, None) on success; (False, error_message) otherwise.
    """
    try:
        df = pd.read_csv(io.BytesIO(content), nrows=5)
    except Exception as exc:
        return False, f"Could not parse the CSV: {exc}"

    if df.empty or len(df.columns) == 0:
        return False, "The file appears to be empty or has no columns."

    if len(df.columns) > settings.MAX_COLUMNS:
        return False, (
            f"Too many columns ({len(df.columns):,}). "
            f"Maximum is {settings.MAX_COLUMNS:,}."
        )

    return True, None
