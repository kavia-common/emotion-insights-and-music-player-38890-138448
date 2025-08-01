import pytest
from fastapi.testclient import TestClient

# Import the FastAPI app from the main module
from emotion_document_backend.main import app

# PUBLIC_INTERFACE
def test_health_endpoint():
    """
    Test the /health endpoint.

    Ensures that /health returns status 200 and JSON {"status": "ok"}.
    """
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
