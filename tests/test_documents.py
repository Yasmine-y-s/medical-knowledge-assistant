from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

def test_create_document():
    response = client.post("/documents", json={
        "title": "Test Document",
        "condition": "test-condition",
        "source": "test-source",
        "source_url": "https://example.com",
        "filename": "test.pdf",
    })
    assert response.status_code == 201
    assert response.json()["title"] == "Test Document"