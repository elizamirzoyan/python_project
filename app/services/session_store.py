"""
In-memory session store for DataSnoop cleaning sessions.

Keeps a parsed DataFrame alive between the initial scan and any subsequent
clean/download calls so that the server never needs to re-read or persist files.
Sessions are keyed by a UUID string generated at scan time.
"""

from typing import Optional

import pandas as pd

_store: dict[str, pd.DataFrame] = {}


def save_session(session_id: str, df: pd.DataFrame) -> None:
    """Persist a DataFrame under the given session ID."""
    _store[session_id] = df.copy()


def get_session(session_id: str) -> Optional[pd.DataFrame]:
    """Return the DataFrame for session_id, or None if not found."""
    return _store.get(session_id)


def update_session(session_id: str, df: pd.DataFrame) -> None:
    """Replace the DataFrame stored under session_id."""
    _store[session_id] = df.copy()


def delete_session(session_id: str) -> None:
    """Remove a session; no-op if it does not exist."""
    _store.pop(session_id, None)


def active_session_count() -> int:
    """Return the number of sessions currently held in memory."""
    return len(_store)
