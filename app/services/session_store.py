"""
app/services/session_store.py

In-memory session store for DataSnoop cleaning sessions.
Keeps the parsed DataFrame alive between the scan and clean steps
so nothing needs to be written to or read from disk on Render.
"""

import pandas as pd
from typing import Optional

# { session_id: df }
_sessions: dict[str, pd.DataFrame] = {}


def save_session(session_id: str, df: pd.DataFrame) -> None:
    _sessions[session_id] = df.copy()


def get_session(session_id: str) -> Optional[pd.DataFrame]:
    return _sessions.get(session_id)


def update_session(session_id: str, df: pd.DataFrame) -> None:
    _sessions[session_id] = df.copy()


def delete_session(session_id: str) -> None:
    _sessions.pop(session_id, None)
