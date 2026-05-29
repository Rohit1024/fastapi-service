# FastAPI GCP Deployment Template

A production-ready Python FastAPI service template designed for deployment on Google Cloud Run. This project includes a fully integrated CI/CD pipeline using GitHub Actions, secure Google Cloud authentication via Workload Identity Federation (WIF), high-performance packaging with `uv`, custom health check liveness probes, traffic-tag splitting, and Slack notifications.

---

## Features

- **FastAPI Core**: Lightweight FastAPI service with `/` and `/health` endpoints.
- **OpenAPI Schema Check**: Automated test suite that validates the OpenAPI specification (`openapi.json`) format on every test run.
- **Ruff & Pytest**: Modern Python linting, formatting check, and testing configurations.
- **High-Performance Containerization**: Multi-stage Docker image built on top of `python:3.14-slim` utilizing `uv` for lightning-fast, system-clean dependency management.
- **CI/CD Pipeline via GitHub Actions**:
  - Run linting, formatting, and tests.
  - Export and upload the OpenAPI spec as a workflow artifact.
  - Authenticate to GCP securely using OIDC (Workload Identity Federation) without long-lived Service Account keys.
  - Build and push Docker images to Artifact Registry.
  - Deploy to Cloud Run with custom liveness probes and `green` revision tagging.
  - Perform traffic splitting to route 100% traffic to the new revision once successfully verified.
  - Send status updates to Slack on pipeline events.

---

## Project Structure

```text
├── .github/
│   └── workflows/
│       └── deploy.yml       # GitHub Actions CI/CD pipeline config
├── .gcloudignore            # Files ignored during GCP uploads
├── .gitignore               # Files ignored by Git
├── Dockerfile               # Multi-stage optimized Docker build config
├── main.py                  # Main FastAPI application & OpenAPI exporter
├── pyproject.toml           # Python package & dependency configuration
└── test_main.py             # Pytest suite verifying endpoints and OpenAPI spec
```

---

## Local Development Setup

### Prerequisites
- Python 3.12+ (Python 3.14 recommended)
- [uv](https://github.com/astral-sh/uv) (fast Python package installer and resolver)

### 1. Initialize Virtual Environment & Install Dependencies
```bash
# Create the virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install uv package manager locally
pip install uv

# Install dependencies including development tools
uv pip install -r pyproject.toml --extra dev
```

### 2. Run Linting and Tests
```bash
# Run Ruff lint checks
ruff check .

# Run Ruff formatting checks
ruff format --check .

# Run the unit test suite
pytest
```

### 3. Run the Application
```bash
uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```
Once running, you can access:
- **Interactive API Docs**: `http://localhost:8080/docs`
- **OpenAPI Schema**: `http://localhost:8080/openapi.json`
- **Health Endpoint**: `http://localhost:8080/health`

---

## Google Cloud & GitHub CI/CD Setup

To authenticate GitHub Actions to Google Cloud securely and deploy your service, complete the following setup steps.

### 1. Enable GCP Services
Enable the required APIs in your GCP project:
```bash
gcloud services enable iamcredentials.googleapis.com \
    artifactregistry.googleapis.com \
    run.googleapis.com \
    cloudbuild.googleapis.com
```

### 2. Set Up Workload Identity Federation (WIF)
Create the workload identity pool, provider, and service account, replacing `sidekick-1024` with your project ID and `PROJECT_NUMBER` with your GCP project number:

```bash
# Create the WIF Pool
gcloud iam workload-identity-pools create "github-pool" \
    --project="sidekick-1024" \
    --location="global" \
    --display-name="GitHub Actions Pool"

# Create the OIDC Provider trusting GitHub Actions OIDC Issuer
gcloud iam workload-identity-pools providers create-oidc "github-provider" \
    --project="sidekick-1024" \
    --location="global" \
    --workload-identity-pool="github-pool" \
    --display-name="GitHub Actions Provider" \
    --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
    --issuer-uri="https://token.actions.githubusercontent.com"

# Create the Service Account
gcloud iam service-accounts create "github-actions-sa" \
    --project="sidekick-1024" \
    --display-name="GitHub Actions Deployment SA"
```

### 3. Grant IAM Permissions to the Service Account
```bash
# Allow pushing to Artifact Registry
gcloud projects add-iam-policy-binding "sidekick-1024" \
    --member="serviceAccount:github-actions-sa@sidekick-1024.iam.gserviceaccount.com" \
    --role="roles/artifactregistry.writer"

# Allow deploying to Cloud Run
gcloud projects add-iam-policy-binding "sidekick-1024" \
    --member="serviceAccount:github-actions-sa@sidekick-1024.iam.gserviceaccount.com" \
    --role="roles/run.developer"

# Allow SA to act as the Cloud Run runtime service account
gcloud iam service-accounts add-iam-policy-binding "PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
    --member="serviceAccount:github-actions-sa@sidekick-1024.iam.gserviceaccount.com" \
    --role="roles/iam.serviceAccountUser"
```

### 4. Bind the WIF Provider to the Service Account
Allow the repository `Rohit1024/fastapi-service` to assume the service account:
```bash
gcloud iam service-accounts add-iam-policy-binding "github-actions-sa@sidekick-1024.iam.gserviceaccount.com" \
    --project="sidekick-1024" \
    --role="roles/iam.workloadIdentityUser" \
    --member="principalSet://iam.googleapis.com/projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-pool/attribute.repository/Rohit1024/fastapi-service"
```

### 5. Add Secrets in GitHub Repository
Navigate to your GitHub repository **Settings > Secrets and variables > Actions** and add the following:

- **`GCP_PROJECT_ID`**: `sidekick-1024`
- **`GCP_PROJECT_NUMBER`**: Your GCP Project Number
- **`SLACK_WEBHOOK_URL`**: Your incoming Slack Webhook URL (configured to post to your Slack deployment channel)

### 6. Configure GitHub Branch Protection
Navigate to **Settings > Branches** and add a branch protection rule for `main`:
- Check **Require a pull request before merging**.
- Check **Require status checks to pass before merging** and search for/add the `Lint & Test` job status check.
- Check **Require branches to be up to date before merging**.
- Check **Do not allow bypassing the above settings**.

---

## Traffic Management & Rollback

If a newly deployed version fails verification or introduces errors, you can immediately shift traffic back to a previous stable revision.

### List Revisions
List all deployed revisions to find the stable revision name:
```bash
gcloud run revisions list \
    --service=fastapi-service \
    --region=us-central1 \
    --project=sidekick-1024
```

### Rollback (Route 100% to a specific revision)
Redirect 100% of the traffic back to the target known-good revision:
```bash
gcloud run services update-traffic fastapi-service \
    --region=us-central1 \
    --project=sidekick-1024 \
    --to-revisions=PREVIOUS_REVISION_NAME=100
```

### Canary Rollout (e.g., Canary 10% new tag, 90% old revision)
You can route traffic proportionally for testing changes in production:
```bash
gcloud run services update-traffic fastapi-service \
    --region=us-central1 \
    --project=sidekick-1024 \
    --to-tags=green=10,PREVIOUS_REVISION_NAME=90
```
