from fastapi.testclient import TestClient
from app.main import app, COLLECTION_NAME, qdrant

client = TestClient(app)

def test_reset_qdrant_endpoint():
    # 1. Appel de l'endpoint
    response = client.post("/reset_qdrant")

    # 2. Vérification du statut HTTP
    assert response.status_code == 200

    data = response.json()

    # 3. Vérification du contenu JSON
    assert data["status"] == "ok"
    assert "Qdrant vidé" in data["message"]

    # 4. Vérifier que la collection existe bien après reset
    collections = qdrant.get_collections().collections
    names = [c.name for c in collections]

    assert COLLECTION_NAME in names
