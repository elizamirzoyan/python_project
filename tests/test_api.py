"""
API integration tests for all DataSnoop endpoints.

Uses FastAPI's TestClient for in-process HTTP calls, and unittest.mock to
isolate external dependencies (file I/O, session store lookups).

Run with:  pytest tests/test_api.py -v
"""

import io
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _csv_upload(content: bytes, filename: str = "test.csv") -> dict:
    """Build a multipart files dict for TestClient.post."""
    return {"file": (filename, io.BytesIO(content), "text/csv")}


# ── Health ─────────────────────────────────────────────────────────────────────

def test_health_returns_200():
    assert client.get("/health").status_code == 200


def test_health_payload_fields():
    data = client.get("/health").json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "app" in data


# ── Landing page ───────────────────────────────────────────────────────────────

def test_root_returns_html():
    response = client.get("/")
    assert response.status_code == 200
    assert "DataSnoop" in response.text


# ── Demo ───────────────────────────────────────────────────────────────────────

def test_demo_returns_200():
    assert client.get("/api/v1/demo").status_code == 200


def test_demo_payload_shape():
    data = client.get("/api/v1/demo").json()
    assert data["success"] is True
    assert data["total_rows"] > 0
    assert data["total_columns"] > 0
    assert isinstance(data["columns"], list)
    assert len(data["columns"]) == data["total_columns"]
    assert isinstance(data["recommendations"], list)
    assert isinstance(data["summary"], str)


def test_demo_health_score_in_range():
    data = client.get("/api/v1/demo").json()
    assert 0.0 <= data["health_score"] <= 100.0
    assert data["overall_health"] in ("Excellent", "Good", "Fair", "Poor")


# ── Dataset catalogue ──────────────────────────────────────────────────────────

def test_datasets_returns_list():
    response = client.get("/api/v1/datasets")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_datasets_have_required_fields():
    items = client.get("/api/v1/datasets").json()
    assert len(items) > 0
    for item in items:
        assert "id" in item
        assert "name" in item
        assert "description" in item


# ── Local datasets ─────────────────────────────────────────────────────────────

def test_local_datasets_returns_list():
    assert isinstance(client.get("/api/v1/local-datasets").json(), list)


def test_local_datasets_includes_sample():
    ids = [item["id"] for item in client.get("/api/v1/local-datasets").json()]
    assert "sample" in ids


def test_local_dataset_analyze_sample():
    data = client.get("/api/v1/local-datasets/sample").json()
    assert data["success"] is True
    assert data["total_rows"] > 0


def test_local_dataset_not_found_returns_404():
    assert client.get("/api/v1/local-datasets/does_not_exist").status_code == 404


# ── File upload ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("csv_bytes, expected_rows, expected_cols", [
    (b"name,age,score\nAlice,25,90.5\nBob,30,85.0\nCarol,28,92.0\n", 3, 3),
    (b"x,y\n1,2\n3,4\n", 2, 2),
    (b"a,b,c,d\n1,2,3,4\n5,6,7,8\n9,10,11,12\n", 3, 4),
])
def test_upload_valid_csv_parametrized(csv_bytes, expected_rows, expected_cols):
    data = client.post("/api/v1/scan/file", files=_csv_upload(csv_bytes)).json()
    assert data["success"] is True
    assert data["total_rows"] == expected_rows
    assert data["total_columns"] == expected_cols


def test_upload_wrong_extension_returns_400():
    assert client.post("/api/v1/scan/file", files=_csv_upload(b"a,b\n1,2", "data.txt")).status_code == 400


def test_upload_detects_nulls():
    csv = b"a,b,c\n1,,3\n,2,\n1,2,3\n"
    data = client.post("/api/v1/scan/file", files=_csv_upload(csv)).json()
    assert data["null_percentage"] > 0


def test_upload_column_breakdown():
    csv = b"x,y\n1.0,a\n2.0,b\n3.0,c\n"
    data = client.post("/api/v1/scan/file", files=_csv_upload(csv)).json()
    col_names = [c["name"] for c in data["columns"]]
    assert "x" in col_names
    assert "y" in col_names


def test_upload_detects_outlier():
    rows = "\n".join(f"{v},ok" for v in ([10.0] * 18 + [99999.0, -99999.0]))
    csv = f"value,label\n{rows}\n".encode()
    data = client.post("/api/v1/scan/file", files=_csv_upload(csv)).json()
    assert data["outlier_count"] >= 1


def test_upload_empty_csv_returns_error():
    status = client.post("/api/v1/scan/file", files=_csv_upload(b"", "empty.csv")).status_code
    assert status in (400, 500)


# ── Clean endpoint — mocked session store ─────────────────────────────────────

def test_clean_applies_imputation_via_mock():
    """
    Verify the clean endpoint calls apply_cleaning_actions and updates the session,
    without depending on a real upload having happened first.
    """
    fake_df = pd.DataFrame({"salary": [50000.0, None, 60000.0, 55000.0]})

    with patch("app.routes.clean.get_session", return_value=fake_df) as mock_get, \
         patch("app.routes.clean.update_session") as mock_update:

        response = client.post("/api/v1/clean", json={
            "session_id": "fake-session-id",
            "actions": [{"type": "IMPUTE", "params": {"column": "salary", "strategy": "median"}}],
        })

        assert response.status_code == 200
        mock_get.assert_called_once_with("fake-session-id")
        mock_update.assert_called_once()

        result_df = mock_update.call_args[0][1]
        assert result_df["salary"].isnull().sum() == 0


def test_clean_returns_404_when_session_missing():
    """Verify a missing session raises 404 without touching the session store."""
    with patch("app.routes.clean.get_session", return_value=None):
        response = client.post("/api/v1/clean", json={
            "session_id": "nonexistent",
            "actions": [{"type": "STRIP_WHITESPACE", "params": {"column": "name"}}],
        })
    assert response.status_code == 404


def test_clean_returns_400_with_no_actions():
    response = client.post("/api/v1/clean", json={"session_id": "any", "actions": []})
    assert response.status_code == 400


# ── Download endpoint — mocked session ────────────────────────────────────────

def test_download_streams_csv_and_deletes_session():
    """
    Confirm the download endpoint returns CSV content and triggers session cleanup,
    using a mock to avoid needing a real session in the store.
    """
    fake_df = pd.DataFrame({"col": [1, 2, 3]})

    with patch("app.routes.clean.get_session", return_value=fake_df), \
         patch("app.routes.clean.delete_session") as mock_delete:

        response = client.get("/api/v1/download/fake-session-id")

        assert response.status_code == 200
        assert "col" in response.text
        mock_delete.assert_called_once_with("fake-session-id")
