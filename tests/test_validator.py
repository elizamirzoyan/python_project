"""
API integration tests for DataSnoop endpoints.

Run with:  pytest tests/test_validator.py -v
Requires:  pip install httpx pytest
"""
import io
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ── Health ────────────────────────────────────────────────────────────────────

def test_health_returns_200():
    r = client.get("/health")
    assert r.status_code == 200


def test_health_payload():
    data = client.get("/health").json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "app" in data


# ── Landing page ──────────────────────────────────────────────────────────────

def test_root_returns_html():
    r = client.get("/")
    assert r.status_code == 200
    assert "DataSnoop" in r.text


# ── Demo ──────────────────────────────────────────────────────────────────────

def test_demo_returns_200():
    r = client.get("/api/v1/demo")
    assert r.status_code == 200


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


# ── Live datasets list ────────────────────────────────────────────────────────

def test_datasets_returns_list():
    r = client.get("/api/v1/datasets")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_datasets_have_required_fields():
    items = client.get("/api/v1/datasets").json()
    assert len(items) > 0
    for item in items:
        assert "id" in item
        assert "name" in item
        assert "description" in item


# ── Local datasets list ───────────────────────────────────────────────────────

def test_local_datasets_returns_list():
    r = client.get("/api/v1/local-datasets")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_local_datasets_includes_sample():
    items = client.get("/api/v1/local-datasets").json()
    ids = [i["id"] for i in items]
    assert "sample" in ids


def test_local_dataset_analyze_sample():
    r = client.get("/api/v1/local-datasets/sample")
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert data["total_rows"] > 0


def test_local_dataset_not_found():
    r = client.get("/api/v1/local-datasets/does_not_exist")
    assert r.status_code == 404


# ── File upload ───────────────────────────────────────────────────────────────

def _csv(content: bytes, filename: str = "test.csv"):
    return {"file": (filename, io.BytesIO(content), "text/csv")}


def test_upload_valid_csv():
    csv = b"name,age,score\nAlice,25,90.5\nBob,30,85.0\nCarol,28,92.0\n"
    r = client.post("/api/v1/scan/file", files=_csv(csv))
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert data["total_rows"] == 3
    assert data["total_columns"] == 3


def test_upload_wrong_extension():
    r = client.post("/api/v1/scan/file", files=_csv(b"a,b\n1,2", "data.txt"))
    assert r.status_code == 400


def test_upload_detects_nulls():
    csv = b"a,b,c\n1,,3\n,2,\n1,2,3\n"
    data = client.post("/api/v1/scan/file", files=_csv(csv)).json()
    assert data["null_percentage"] > 0


def test_upload_column_breakdown():
    csv = b"x,y\n1.0,a\n2.0,b\n3.0,c\n"
    data = client.post("/api/v1/scan/file", files=_csv(csv)).json()
    col_names = [c["name"] for c in data["columns"]]
    assert "x" in col_names
    assert "y" in col_names


def test_upload_detects_outlier():
    # 18 normal values + 2 extreme outliers
    rows = "\n".join(f"{v},ok" for v in ([10.0] * 18 + [99999.0, -99999.0]))
    csv = f"value,label\n{rows}\n".encode()
    data = client.post("/api/v1/scan/file", files=_csv(csv)).json()
    assert data["outlier_count"] >= 1


def test_upload_empty_csv():
    r = client.post("/api/v1/scan/file", files=_csv(b"", "empty.csv"))
    assert r.status_code in (400, 500)
