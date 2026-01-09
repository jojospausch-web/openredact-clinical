import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root():
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    assert "version" in response.json()


def test_health():
    """Test health check"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_get_whitelist():
    """Test get whitelist"""
    response = client.get("/api/whitelist")
    assert response.status_code == 200
    assert "entries" in response.json()


def test_add_whitelist_entry():
    """Test add whitelist entry"""
    response = client.post(
        "/api/whitelist",
        json={"entry": "test_entry"}
    )
    assert response.status_code == 201


def test_get_templates():
    """Test get templates"""
    response = client.get("/api/templates")
    assert response.status_code == 200
    assert "templates" in response.json()


def test_find_piis_placeholder():
    """Test PII detection (placeholder)"""
    response = client.post(
        "/api/find-piis",
        json={"text": "Test text", "language": "de"}
    )
    assert response.status_code == 200
    assert "piis" in response.json()
