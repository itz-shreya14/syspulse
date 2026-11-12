import pytest
from fastapi.testclient import TestClient
from server import app

client = TestClient(app)

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert "SysPulse" in response.text

def test_system_specs():
    response = client.get("/api/system")
    assert response.status_code == 200
    data = response.json()
    assert "logical_cores" in data
    assert "hostname" in data
    assert data["logical_cores"] >= 1

def test_full_snapshot():
    response = client.get("/api/snapshot")
    assert response.status_code == 200
    data = response.json()
    assert "telemetry" in data
    assert "health" in data
    assert 0 <= data["health"]["health_score"] <= 100

def test_processes_query():
    response = client.get("/api/processes?sort_by=memory&limit=15")
    assert response.status_code == 200
    procs = response.json()
    assert isinstance(procs, list)
    assert len(procs) > 0
    assert "pid" in procs[0]
    assert "cpu_percent" in procs[0]

def test_network_endpoints():
    r_conn = client.get("/api/network/connections?limit=10")
    assert r_conn.status_code == 200
    assert isinstance(r_conn.json(), list)

    r_lat = client.get("/api/network/latency")
    assert r_lat.status_code == 200
    assert "latency_ms" in r_lat.json()

def test_diagnostics_endpoints():
    r_health = client.get("/api/diagnostics/health")
    assert r_health.status_code == 200
    assert "findings" in r_health.json()

    r_cache = client.get("/api/diagnostics/cache")
    assert r_cache.status_code == 200
    assert "size_mb" in r_cache.json()

def test_pdf_report_endpoint():
    response = client.get("/api/reports/pdf")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "syspulse_audit_report" in response.headers.get("content-disposition", "")
    assert len(response.content) > 1000
    assert response.content.startswith(b"%PDF")

