from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "message": "Hello from FastAPI on Cloud Run!"}

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_openapi_spec():
    # Verify that the OpenAPI JSON endpoint is accessible and valid
    response = client.get("/openapi.json")
    assert response.status_code == 200
    openapi_data = response.json()
    assert "openapi" in openapi_data
    assert openapi_data["info"]["title"] == "FastAPI GCP Deployment"
