from unittest.mock import MagicMock
from app.main import app, qdrant, COLLECTION_NAME
from fastapi.testclient import TestClient

client = TestClient(app)

def test_reset_qdrant_endpoint(monkeypatch):
    # Mock des méthodes Qdrant
    monkeypatch.setattr(qdrant, "delete_collection", MagicMock(return_value=None))
    monkeypatch.setattr(qdrant, "create_collection", MagicMock(return_value=None))

    response = client.post("/reset_qdrant")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
