import pandas as pd
from pathlib import Path
from typing import Tuple, Optional

MAX_FILE_SIZE_MB = 500
MAX_COLUMNS = 1000
SUPPORTED_EXTENSIONS = {".csv"}


def validate_extension(filename: str) -> Tuple[bool, Optional[str]]:
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        return False, f"'{suffix}' files are not supported. Please upload a .csv file."
    return True, None


def validate_size(content: bytes) -> Tuple[bool, Optional[str]]:
    size_mb = len(content) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        return False, f"File is {size_mb:.1f} MB — the limit is {MAX_FILE_SIZE_MB} MB."
    return True, None


def validate_csv(path: str) -> Tuple[bool, Optional[str]]:
    try:
        df = pd.read_csv(path, nrows=5)
    except Exception as e:
        return False, f"Could not read the CSV: {e}"

    if df.empty or len(df.columns) == 0:
        return False, "The file appears to be empty or has no columns."

    if len(df.columns) > MAX_COLUMNS:
        return False, f"Too many columns ({len(df.columns):,}). Maximum is {MAX_COLUMNS:,}."

    return True, None
