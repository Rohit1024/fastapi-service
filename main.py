import json
from fastapi import FastAPI

app = FastAPI(
    title="FastAPI GCP Deployment",
    description="A template service running on Cloud Run",
    version="1.0.0",
)

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Hello from FastAPI on Cloud Run!"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

def export_openapi():
    """Helper to export the OpenAPI spec to a file."""
    with open("openapi.json", "w") as f:
        json.dump(app.openapi(), f, indent=2)

if __name__ == "__main__":
    export_openapi()
