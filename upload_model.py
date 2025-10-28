"""
Script to upload trained model to S3/Minio storage.
"""

import sys
from pathlib import Path
import json

from loguru import logger

sys.path.append(str(Path(__file__).parent))

from src.storage.model_storage import ModelStorage
from src.config.config import PROJECT_ROOT


def upload_best_model():
    """Upload the best trained model to S3."""
    
    # Initialize storage
    logger.info("Initializing model storage...")
    storage = ModelStorage(bucket_name="models")
    
    # Find best model checkpoint
    checkpoint_dir = PROJECT_ROOT / "models" / "checkpoints"
    best_model_path = checkpoint_dir / "best_model.pth"
    
    if not best_model_path.exists():
        logger.error(f"Best model not found at {best_model_path}")
        return
    
    # Load training history to get metrics
    history_path = PROJECT_ROOT / "logs" / "training" / "training_history.json"
    metadata = {}
    
    if history_path.exists():
        with open(history_path, 'r') as f:
            history = json.load(f)
        
        # Get best epoch metrics
        best_epoch = max(
            range(len(history['train_loss'])),
            key=lambda i: history['val_acc'][i]
        )
        
        metadata = {
            'architecture': 'resnet18',
            'num_classes': 2,
            'best_epoch': best_epoch + 1,
            'train_accuracy': history['train_acc'][best_epoch],
            'val_accuracy': history['val_acc'][best_epoch],
            'train_loss': history['train_loss'][best_epoch],
            'val_loss': history['val_loss'][best_epoch],
            'total_epochs': len(history['train_loss']),
            'optimizer': 'AdamW',
            'initial_learning_rate': history.get('learning_rate', [0.001])[0] if 'learning_rate' in history else 0.001
        }
    
    # Additional files to upload
    additional_files = []
    if history_path.exists():
        additional_files.append(history_path)
    
    # Check for latest model
    latest_model_path = checkpoint_dir / "latest_model.pth"
    if latest_model_path.exists():
        additional_files.append(latest_model_path)
    
    # Upload model
    logger.info("Uploading model to S3...")
    manifest = storage.upload_model(
        model_path=best_model_path,
        model_name="plant_classifier",
        metadata=metadata,
        additional_files=additional_files
    )
    
    # Print summary
    logger.success("Model uploaded successfully!")
    logger.info(f"Model: plant_classifier")
    logger.info(f"Version: {manifest['version']}")
    logger.info(f"Validation Accuracy: {metadata.get('val_accuracy', 'N/A'):.2%}")
    logger.info(f"S3 URL: {manifest['model_url']}")
    
    return manifest


if __name__ == "__main__":
    upload_best_model()
