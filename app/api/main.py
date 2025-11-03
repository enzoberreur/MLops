"""FastAPI service exposing the dandelion classifier."""
from __future__ import annotations

import io
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict

import torch
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from PIL import Image
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from models.model import DandelionClassifier
from models.utils import CLASS_NAMES, get_inference_transform, get_minio_client

LOG = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")

app = FastAPI(title="Dandelion Classifier API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MODEL_LOCAL_PATH = Path(os.environ.get("MODEL_LOCAL_PATH", "/tmp/model/best_model.pt"))
MINIO_MODEL_BUCKET = os.environ.get("MINIO_MODEL_BUCKET", "dandelion-models")
MINIO_MODEL_PATH = os.environ.get("MINIO_MODEL_PATH", "models/latest/best_model.pt")
IMAGE_SIZE = int(os.environ.get("IMAGE_SIZE", 128))

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model: DandelionClassifier | None = None
class_names = CLASS_NAMES
transform = get_inference_transform(IMAGE_SIZE)

PREDICTION_COUNTER = Counter("predictions_total", "Number of predictions served", ["result"])
PREDICTION_LATENCY = Histogram("prediction_latency_seconds", "Latency for prediction endpoint")


def _download_model() -> None:
    client = get_minio_client()
    MODEL_LOCAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    client.fget_object(MINIO_MODEL_BUCKET, MINIO_MODEL_PATH, str(MODEL_LOCAL_PATH))
    LOG.info("Downloaded model from MinIO at %s", MINIO_MODEL_PATH)


def _load_model() -> None:
    global model, class_names  # noqa: PLW0603 - module level cache
    if not MODEL_LOCAL_PATH.exists():
        _download_model()
    checkpoint = torch.load(MODEL_LOCAL_PATH, map_location=device)
    class_names = checkpoint.get("class_names", CLASS_NAMES)
    model_instance = DandelionClassifier(num_classes=len(class_names))
    model_instance.load_state_dict(checkpoint["model_state_dict"])
    model_instance.eval()
    model_instance.to(device)
    model = model_instance
    LOG.info("Model loaded with classes: %s", class_names)


@app.on_event("startup")
async def startup_event() -> None:
    try:
        _load_model()
    except Exception as exc:  # pragma: no cover - startup failure should be visible in logs
        LOG.error("Failed to load model on startup: %s", exc)
        raise


@app.get("/health")
def health() -> Dict[str, Any]:
    return {"status": "ok", "classes": class_names}


@app.post("/predict")
def predict(file: UploadFile = File(...)) -> Dict[str, Any]:
    if model is None:
        raise HTTPException(status_code=500, detail="Model not loaded")

    try:
        contents = file.file.read()
        image = Image.open(io.BytesIO(contents)).convert("RGB")
    except Exception as exc:  # pragma: no cover - guard user input
        LOG.error("Invalid image input: %s", exc)
        raise HTTPException(status_code=400, detail="Invalid image file") from exc

    start = time.perf_counter()
    tensor = transform(image).unsqueeze(0).to(device)
    with torch.no_grad():
        outputs = model(tensor)
        probabilities = torch.softmax(outputs, dim=1)[0]
        confidence, predicted_idx = torch.max(probabilities, dim=0)
    duration = time.perf_counter() - start
    PREDICTION_LATENCY.observe(duration)

    prediction = class_names[predicted_idx.item()]
    PREDICTION_COUNTER.labels(result=prediction).inc()
    return {
        "prediction": prediction,
        "confidence": round(float(confidence.item()), 4),
        "class_probabilities": {
            class_names[i]: round(float(probabilities[i].item()), 4) for i in range(len(class_names))
        },
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
