# Robofin Backend

## 1) Local Development & Deployment

### Local Development Setup
We recommend to use virtual environment
```bash
pip install -r requirements.txt
```

### Local Run (Deployment)
```bash
python app.py # use this url: http://localhost:8081
```

## 2) Endpoint Manual

### /health
- method: GET
- description: health check
- response: if the server is healthy, it will return {"status": 200}

### /predict
- method: POST
- description: generate text from model
- request: request json body with payload in this format {text: "input for model"}
- response: json in this format {message: "output from model"}
- raises: HTTP Exception with status 500 and error detail

### /edit
- method: POST
- description: edit the model with GRACE
- request: request json body with payload in this format {text: "input for model", edit: "correction text"}
- response: json in this format {message: "output from model after edit"}
- raises: HTTP Exception with status 500 and error detail

## 3) Deploy on GCP

### 3.1) Create Artifact Registry
Go to GCP Console and select Artifact Registry, then create docker repositories name `image` with default settings.

### 3.2) Build Image
```bash
# inbound-trilogy-461608-e1 is the project_id, we can change it to any project_id
docker build -t asia-southeast1-docker.pkg.dev/inbound-trilogy-461608-e1/image/robofin-backend:latest -f ./Dockerfile .

# [Optional test run
docker run -p 8081:8081 --name back asia-southeast1-docker.pkg.dev/inbound-trilogy-461608-e1/image/robofin-backend:latest

# push image with latest tag
docker push asia-southeast1-docker.pkg.dev/inbound-trilogy-461608-e1/image/robofin-backend:latest
```

### 3.3) Create service account for Cloud Run deployment
Goto GCP IAM service account and create new account name `robofin-backend` with no roles.

### 3.4) Deploy to Cloud Run
Deploy to cloud run with these command
```bash
gcloud run deploy robofin-backend \
    --no-allow-unauthenticated \
    --cpu-boost \
    --ingress all \
    --max-instances 1 \
    --min-instances 0 \
    --region asia-southeast1 \
    --service-account robofin-backend@inbound-trilogy-461608-e1.iam.gserviceaccount.com \
    --timeout 300 \
    --cpu 1 \
    --memory 512Mi \
    --port 8081 \
    --image asia-southeast1-docker.pkg.dev/inbound-trilogy-461608-e1/image/robofin-backend:latest \
    --set-env-vars MODEL_URL=http://internal_gce_ip:8000
```