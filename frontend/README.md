# Robofin Backend

## 1) Local Development & Deployment

### Local Development Setup
We recommend to use virtual environment
```bash
pip install -r requirements.txt
```

### Local Run (Deployment)
```bash
streamlit run app.py # use this url: http://localhost:8501
```

## 2) Deploy on GCP

### 2.1) Create Artifact Registry
Go to GCP Console and select Artifact Registry, then create docker repositories name `image` with default settings.

### 2.2) Build Image
```bash
# inbound-trilogy-461608-e1 is the project_id, we can change it to any project_id
docker build -t asia-southeast1-docker.pkg.dev/inbound-trilogy-461608-e1/image/robofin-frontend:latest -f ./Dockerfile .

# test run
docker run -p 8080:8080 --name front asia-southeast1-docker.pkg.dev/inbound-trilogy-461608-e1/image/robofin-frontend:latest

# push image with latest tag
docker push asia-southeast1-docker.pkg.dev/inbound-trilogy-461608-e1/image/robofin-frontend:latest
```

### 3.3) Create service account for Cloud Run deployment
Goto GCP IAM service account and create new account name `robofin-fronted` with role
- Cloud Run Invoker

### 3.4) Deploy to Cloud Run
Deploy to cloud run with these command
```bash
gcloud run deploy robofin-frontend \
    --allow-unauthenticated \
    --cpu-boost \
    --ingress all \
    --max-instances 1 \
    --min-instances 0 \
    --region asia-southeast1 \
    --service-account robofin-frontend@inbound-trilogy-461608-e1.iam.gserviceaccount.com \
    --timeout 540 \
    --cpu 1 \
    --memory 512Mi \
    --port 8080 \
    --image asia-southeast1-docker.pkg.dev/inbound-trilogy-461608-e1/image/robofin-frontend:latest \
    --set-env-vars BE_URL=backend_cloudrun_url
    --set-env-vars RUN_LOCATION=cloudrun
```