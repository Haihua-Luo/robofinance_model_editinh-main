# Robofin Model

This repositories is based on [GRACE](https://github.com/Thartvigsen/GRACE.git). We add backend code to wrap the GRACE logic and make it deployable.

When the backend is start for the first time, it will read `MODEL_PATH` environment variables. if we don't set it, the default will be `{current_path}/model_cache` directory.

We also implement model saving feature to save previous edited model and load it for next server startup, so you don't have to worry about server shutdown. 

If we start for a second time and have environment variable name `LOAD_EDITED_MODEL=load`, it will try to load edited model from previous session if exist. (You can remove this LOAD_EDITED_MODEL environment variable to disable this feature)

## 1) Local Development & Deployment

### Local Development Setup
CPU Environment setup
```bash
conda env create --name grace_env --file environment-cpu.yml
conda activate grace_env
pip install -e . # install grace

conda env update --file environment-cpu.yml --prune # run this if we update the environment.yml file
```

GPU Environment setup
```bash
conda env create --name grace_env --file environment-gpu.yml
conda activate grace_env
pip install -e . # install grace

conda env update --file environment-gpu.yml --prune # run this if we update the environment.yml file
```

### Local Run (Deployment)
```bash
conda activate grace_env
python app.py
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

## 3.1) Create Artifact Registry
Go to GCP Console and select Artifact Registry, then create docker repositories name `image` with default settings.

## 3.2) Build Image
GPU
```bash
# inbound-trilogy-461608-e1 is the project_id, we can change it to any project_id
docker build -t asia-southeast1-docker.pkg.dev/inbound-trilogy-461608-e1/image/robofin-model:latest -f ./Dockerfile.gpu .

# [Optional] test run
docker run -p 8000:8000 --gpus=all --name back -v ./model_cache:/app/model_cache asia-southeast1-docker.pkg.dev/inbound-trilogy-461608-e1/image/robofin-model:latest

# push image with latest tag (You can add tag too, if you want)
docker push asia-southeast1-docker.pkg.dev/inbound-trilogy-461608-e1/image/robofin-model:latest
```
CPU
```bash
# inbound-trilogy-461608-e1 is the project_id, we can change it to any project_id
docker build -t asia-southeast1-docker.pkg.dev/inbound-trilogy-461608-e1/image/robofin-model-cpu:latest -f ./Dockerfile.cpu .

# [Optional] test run
docker run -p 8000:8000 --name back -v ./model_cache:/app/model_cache asia-southeast1-docker.pkg.dev/inbound-trilogy-461608-e1/image/robofin-model-cpu:latest

# push image with latest tag (You can add tag too, if you want)
docker push asia-southeast1-docker.pkg.dev/inbound-trilogy-461608-e1/image/robofin-model-cpu:latest
```

## 3.3) Create service account for GCE deployment
Goto GCP IAM service account and create new account name `robofin-model` with role
- Artifact Registry Reader

## 3.4) Deploy to GCE
create GCE with these setting
```
name = robofin-model
machine type = any is fine

Container=Deploy container
- container image = asia-southeast1-docker.pkg.dev/inbound-trilogy-461608-e1/image/robofin-model:latest
- Environment variable
  - MODEL_PATH = /app/model_cache
  - LOAD_EDITED_MODEL = load
  - MODEL_NAME = deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B
  - LAYER_TO_EDIT = model.layers[15].mlp.gate_proj.weight
  - EPS = 1.0
  - LR = 1.0
  - MAX_NEW_TOKENS = 512
- Volume map
  - mount path = /app/model_cache
  - host path = /home/model_cache
  - mode = read/write

Data protection = no backups

Allow HTTP traffic = True

Service account = use service account from 3)
```

## 3.5) Re-deployment
Just edit container image of GCE to latest one and restart GCE to fetch new image.