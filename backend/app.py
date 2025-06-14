# load variables
import os

MODEL_URL = os.getenv("MODEL_URL", "http://localhost:8000")

# load required package
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict
import uvicorn
import traceback
import requests
import logging

# create logger
logger = logging.getLogger(name="robofin_backend")
logger.setLevel(logging.INFO)

# create fastapi app
app = FastAPI(
    title="Robofin Backend",
    description="Robofin Backend",
    version="1.0.0",
)


# define data model
class GenerateRequest(BaseModel):
    text: str


class EditRequest(BaseModel):
    text: str
    edit: str


# define api
@app.get("/health")
def health():
    """health check

    Returns:
        Dict[str, int]: {"status": 200} if the server is in healthy state
    """
    return {"status": 200}


@app.post("/predict", response_model=Dict[str, str])
def generate_text(request: GenerateRequest) -> Dict[str, str]:
    """generate a response from model.

    Args:
        request (GenerateRequest): The request body containing the 'text' field.

    Returns:
        Dict[str, str]: A JSON response with a 'message' field.

    Raises:
        HTTPException: status 500 with detail in case of error
    """
    try:
        text = request.text
        response = requests.post(url=f"{MODEL_URL}/predict", json={"text": text})
        response.raise_for_status()
        result = response.json()["message"]
        logger.info(f"Endpoint: /predict, text: {text}, result: {result}")
        return {"message": result}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/edit", response_model=Dict[str, str])
def edit_text(
    request: EditRequest,
) -> Dict[str, str]:
    """edit the model

    Args:
        request (EditRequest): The request body containing 'text' and 'edit' fields.

    Returns:
        Dict[str, str]: A JSON response with a 'message' field.

    Raises:
        HTTPException: status 500 with detail in case of error
    """
    try:
        text = request.text
        edit = request.edit
        response = requests.post(
            url=f"{MODEL_URL}/edit", json={"text": text, "edit": edit}
        )
        response.raise_for_status()
        result = response.json()["message"]
        logger.info(f"Endpoint: /edit, text: {text}, edit: {edit}, result: {result}")
        return {"message": result}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# for local run
if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8081, reload=True)
