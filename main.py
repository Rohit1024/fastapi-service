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

