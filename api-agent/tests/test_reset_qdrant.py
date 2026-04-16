from unittest.mock import MagicMock
from app.main import app, qdrant
from fastapi.testclient import TestClient

client = TestClient(app)

def test_reset_qdrant_endpoint(monkeypatch):
    # Mock complet de l'objet qdrant
    mock_qdrant = MagicMock()
    mock_qdrant.delete_collection.return_value = None
    mock_qdrant.create_collection.return_value = None

    # Remplace l'objet qdrant dans ton code par le mock
    monkeypatch.setattr("app.main.qdrant", mock_qdrant)

    response = client.post("/reset_qdrant")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"

