"""
FastAPI application for plant classification.
Provides REST API for image classification (dandelion vs grass).
"""

import sys
from pathlib import Path
import io
import time
from typing import Dict, Any, Optional
from datetime import datetime

import torch
import numpy as np
from PIL import Image
from fastapi import FastAPI, File, UploadFile, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import torchvision.transforms as transforms
from loguru import logger

sys.path.append(str(Path(__file__).parent.parent.parent))

from src.api.model_loader import get_default_model_loader, ModelLoader
from src.config.config import IMAGE_SIZE

# Initialize FastAPI app
app = FastAPI(
    title="Plant Classification API",
    description="API for classifying images of plants (dandelion vs grass)",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
model_loader: Optional[ModelLoader] = None
class_names = ["dandelion", "grass"]
prediction_count = 0
total_inference_time = 0.0

# Image preprocessing
transform = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(IMAGE_SIZE),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])


# Pydantic models
class PredictionResponse(BaseModel):
    """Response model for predictions."""
    prediction: str
    confidence: float
    probabilities: Dict[str, float]
    inference_time_ms: float
    model_info: Dict[str, Any]


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str
    model_loaded: bool
    model_info: Dict[str, Any]
    predictions_count: int
    avg_inference_time_ms: float


@app.on_event("startup")
async def startup_event():
    """Initialize model on startup."""
    global model_loader
    
    logger.info("Starting Plant Classification API...")
    
    try:
        model_loader = get_default_model_loader(device="cpu")
        logger.success("Model loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        logger.warning("API starting without model - will fail on predictions")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down Plant Classification API...")


@app.get("/", tags=["General"])
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Plant Classification API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "predict": "/predict"
    }


@app.get("/health", response_model=HealthResponse, tags=["General"])
async def health_check():
    """
    Health check endpoint.
    Returns API status and model information.
    """
    global prediction_count, total_inference_time
    
    model_loaded = model_loader is not None and model_loader.model is not None
    model_info = model_loader.get_model_info() if model_loaded else {}
    
    avg_time = (total_inference_time / prediction_count) if prediction_count > 0 else 0.0
    
    return HealthResponse(
        status="healthy" if model_loaded else "model_not_loaded",
        model_loaded=model_loaded,
        model_info=model_info,
        predictions_count=prediction_count,
        avg_inference_time_ms=avg_time
    )


@app.post("/predict", response_model=PredictionResponse, tags=["Prediction"])
async def predict(file: UploadFile = File(...)):
    """
    Predict plant class from image.
    
    Args:
        file: Image file (JPEG, PNG)
        
    Returns:
        Prediction result with confidence scores
    """
    global model_loader, prediction_count, total_inference_time
    
    # Check if model is loaded
    if model_loader is None or model_loader.model is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model not loaded. Please try again later."
        )
    
    # Validate file type
    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type: {file.content_type}. Please upload an image."
        )
    
    try:
        # Read and preprocess image
        start_time = time.time()
        
        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert("RGB")
        
        # Preprocess
        input_tensor = transform(image).unsqueeze(0)
        
        # Get model
        model = model_loader.get_model()
        
        # Inference
        with torch.no_grad():
            output = model(input_tensor)
            probabilities = torch.softmax(output, dim=1)
            confidence, predicted_idx = torch.max(probabilities, dim=1)
            
            predicted_class = class_names[predicted_idx.item()]
            confidence_value = confidence.item()
            
            # Get probabilities for all classes
            probs_dict = {
                class_names[i]: float(probabilities[0][i].item())
                for i in range(len(class_names))
            }
        
        inference_time = (time.time() - start_time) * 1000  # Convert to ms
        
        # Update statistics
        prediction_count += 1
        total_inference_time += inference_time
        
        logger.info(f"Prediction: {predicted_class} (confidence: {confidence_value:.4f})")
        
        return PredictionResponse(
            prediction=predicted_class,
            confidence=confidence_value,
            probabilities=probs_dict,
            inference_time_ms=round(inference_time, 2),
            model_info=model_loader.get_model_info()
        )
        
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction failed: {str(e)}"
        )


@app.post("/predict/batch", tags=["Prediction"])
async def predict_batch(files: list[UploadFile] = File(...)):
    """
    Predict plant class for multiple images.
    
    Args:
        files: List of image files
        
    Returns:
        List of prediction results
    """
    if len(files) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 10 images per batch"
        )
    
    start_time = time.time()
    results = []
    successful = 0
    failed = 0
    
    for file in files:
        try:
            result = await predict(file)
            results.append({
                "filename": file.filename,
                "success": True,
                "result": result.dict()
            })
            successful += 1
        except HTTPException as e:
            results.append({
                "filename": file.filename,
                "success": False,
                "error": e.detail
            })
            failed += 1
    
    total_time = (time.time() - start_time) * 1000  # Convert to milliseconds
    
    return {
        "predictions": results,
        "total_images": len(files),
        "successful": successful,
        "failed": failed,
        "total_time_ms": round(total_time, 2)
    }


@app.get("/model/info", tags=["Model"])
async def get_model_info():
    """Get information about the loaded model."""
    if model_loader is None or model_loader.model is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model not loaded"
        )
    
    return {
        "model_info": model_loader.get_model_info(),
        "model_source": model_loader.model_source,
        "device": model_loader.device,
        "class_names": class_names,
        "input_size": IMAGE_SIZE
    }


@app.post("/model/reload", tags=["Model"])
async def reload_model():
    """Reload the model (useful after model updates)."""
    global model_loader
    
    try:
        if model_loader is not None:
            model_loader.reload()
            return {
                "status": "success",
                "message": "Model reloaded successfully",
                "model_info": model_loader.get_model_info()
            }
        else:
            model_loader = get_default_model_loader(device="cpu")
            return {
                "status": "success",
                "message": "Model loaded successfully",
                "model_info": model_loader.get_model_info()
            }
    except Exception as e:
        logger.error(f"Failed to reload model: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Model reload failed: {str(e)}"
        )


@app.get("/stats", tags=["Statistics"])
async def get_stats():
    """Get API usage statistics."""
    global prediction_count, total_inference_time
    
    avg_time = (total_inference_time / prediction_count) if prediction_count > 0 else 0.0
    
    return {
        "total_predictions": prediction_count,
        "total_inference_time_ms": round(total_inference_time, 2),
        "avg_inference_time_ms": round(avg_time, 2),
        "model_loaded": model_loader is not None and model_loader.model is not None
    }


if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting Plant Classification API...")
    logger.info("API will be available at: http://localhost:8000")
    logger.info("Documentation at: http://localhost:8000/docs")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
