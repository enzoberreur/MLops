"""
Training script with MLflow tracking integration.
"""

import sys
from pathlib import Path
import torch
import argparse
import json
from datetime import datetime

from loguru import logger

sys.path.append(str(Path(__file__).parent.parent))

from src.models.dataset import create_data_splits, create_dataloaders, load_image_paths_and_labels
from src.models.model import PlantClassifier
from src.models.trainer import Trainer
from src.tracking.mlflow_tracker import MLflowTracker
from src.config.config import PROJECT_ROOT, IMAGE_SIZE

import os
from dotenv import load_dotenv

load_dotenv()


def train_with_mlflow(
    backbone: str = 'resnet18',
    epochs: int = 10,
    batch_size: int = 32,
    learning_rate: float = 1e-3,
    device: str = 'cuda' if torch.cuda.is_available() else 'cpu',
    freeze_backbone: bool = True,
    unfreeze_epoch: int = 5,
    early_stopping_patience: int = 10,
    experiment_name: str = "plant_classification",
    run_name: str = None,
    track_mlflow: bool = True
):
    """
    Train model with MLflow tracking.
    
    Args:
        backbone: Backbone architecture name
        epochs: Number of training epochs
        batch_size: Batch size
        learning_rate: Initial learning rate
        device: Device to train on
        freeze_backbone: Whether to freeze backbone initially
        unfreeze_epoch: Epoch to unfreeze backbone
        early_stopping_patience: Patience for early stopping
        experiment_name: MLflow experiment name
        run_name: MLflow run name
        track_mlflow: Whether to use MLflow tracking
    """
    logger.info("="*70)
    logger.info("TRAINING WITH MLFLOW TRACKING")
    logger.info("="*70)
    
    # Initialize MLflow tracker
    mlflow_tracker = None
    if track_mlflow:
        try:
            mlflow_tracker = MLflowTracker(
                tracking_uri=os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5001"),
                experiment_name=experiment_name,
                s3_endpoint=os.getenv("MLFLOW_S3_ENDPOINT_URL", "http://localhost:9000"),
                aws_access_key=os.getenv("AWS_ACCESS_KEY_ID", "minioadmin"),
                aws_secret_key=os.getenv("AWS_SECRET_ACCESS_KEY", "minioadmin")
            )
            logger.success("MLflow tracker initialized")
        except Exception as e:
            logger.warning(f"Could not initialize MLflow: {e}")
            logger.info("Continuing without MLflow tracking")
            mlflow_tracker = None
    
    # Start MLflow run
    if mlflow_tracker:
        if run_name is None:
            run_name = f"{backbone}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        mlflow_tracker.start_run(
            run_name=run_name,
            tags={
                "model_type": "classification",
                "backbone": backbone,
                "task": "dandelion_vs_grass"
            }
        )
        
        # Log system info
        mlflow_tracker.log_system_metrics()
    
    # Configuration
    data_dir = PROJECT_ROOT / "data" / "processed"
    checkpoint_dir = PROJECT_ROOT / "models" / "checkpoints"
    log_dir = PROJECT_ROOT / "logs" / "training"
    
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Log parameters to MLflow
    params = {
        "backbone": backbone,
        "epochs": epochs,
        "batch_size": batch_size,
        "learning_rate": learning_rate,
        "device": device,
        "freeze_backbone": freeze_backbone,
        "unfreeze_epoch": unfreeze_epoch,
        "early_stopping_patience": early_stopping_patience,
        "optimizer": "AdamW",
        "scheduler": "CosineAnnealingLR",
        "loss_function": "CrossEntropyLoss",
        "num_classes": 2
    }
    
    if mlflow_tracker:
        mlflow_tracker.log_params(params)
    
    logger.info(f"\nTraining Configuration:")
    for key, value in params.items():
        logger.info(f"  {key}: {value}")
    
    # Load data
    logger.info(f"\nLoading image paths and labels...")
    image_paths, labels = load_image_paths_and_labels()
    logger.info(f"Total images: {len(image_paths)}")
    
    # Create data splits
    logger.info("\nCreating data splits...")
    splits = create_data_splits(
        image_paths,
        labels,
        train_ratio=0.7,
        val_ratio=0.15,
        test_ratio=0.15,
        random_state=42
    )
    
    train_paths = len(splits['train'][0])
    val_paths = len(splits['val'][0])
    test_paths = len(splits['test'][0])
    
    logger.info(f"Train: {train_paths}, Val: {val_paths}, Test: {test_paths}")
    
    # Log dataset info
    if mlflow_tracker:
        mlflow_tracker.log_params({
            "train_size": train_paths,
            "val_size": val_paths,
            "test_size": test_paths
        })
    
    # Create dataloaders
    logger.info("\nCreating data loaders...")
    dataloaders = create_dataloaders(
        splits,
        batch_size=batch_size,
        num_workers=0,
        image_size=IMAGE_SIZE
    )
    
    train_loader = dataloaders['train']
    val_loader = dataloaders['val']
    test_loader = dataloaders['test']
    
    # Create model
    logger.info(f"\nInitializing {backbone} model...")
    model = PlantClassifier(
        backbone=backbone,
        num_classes=2,
        dropout=0.3
    )
    
    if freeze_backbone:
        model.freeze_backbone()
        logger.info("Backbone frozen initially")
    
    model = model.to(device)
    
    # Log model info
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    
    logger.info(f"Total parameters: {total_params:,}")
    logger.info(f"Trainable parameters: {trainable_params:,}")
    
    if mlflow_tracker:
        mlflow_tracker.log_params({
            "total_parameters": total_params,
            "trainable_parameters": trainable_params
        })
    
    # Create trainer
    trainer = Trainer(
        model=model,
        train_loader=train_loader,
        val_loader=val_loader,
        device=device,
        checkpoint_dir=checkpoint_dir,
        log_dir=log_dir,
        learning_rate=learning_rate
    )
    
    # Training callback for MLflow
    def mlflow_callback(epoch, metrics):
        if mlflow_tracker:
            mlflow_tracker.log_training_metrics(
                epoch=epoch,
                train_loss=metrics['train_loss'],
                train_acc=metrics['train_acc'],
                val_loss=metrics['val_loss'],
                val_acc=metrics['val_acc'],
                learning_rate=metrics.get('learning_rate', learning_rate)
            )
    
    # Train
    logger.info("\n" + "="*70)
    logger.info("STARTING TRAINING")
    logger.info("="*70 + "\n")
    
    history = trainer.train(
        epochs=epochs,
        early_stopping_patience=early_stopping_patience,
        unfreeze_epoch=unfreeze_epoch if freeze_backbone else None,
        epoch_callback=mlflow_callback
    )
    
    # Save history
    history_path = log_dir / "training_history.json"
    with open(history_path, 'w') as f:
        json.dump(history, f, indent=2)
    
    logger.info(f"\nTraining history saved to {history_path}")
    
    # Log final metrics
    best_val_acc = max(history['val_acc'])
    best_epoch = history['val_acc'].index(best_val_acc) + 1
    final_train_acc = history['train_acc'][-1]
    final_val_acc = history['val_acc'][-1]
    
    logger.info("\n" + "="*70)
    logger.info("TRAINING COMPLETED")
    logger.info("="*70)
    logger.info(f"Best validation accuracy: {best_val_acc:.4f} (epoch {best_epoch})")
    logger.info(f"Final training accuracy: {final_train_acc:.4f}")
    logger.info(f"Final validation accuracy: {final_val_acc:.4f}")
    
    # Log artifacts to MLflow
    if mlflow_tracker:
        # Log training history
        mlflow_tracker.log_artifact(history_path, "training")
        
        # Log best model
        best_model_path = checkpoint_dir / "best_model.pth"
        if best_model_path.exists():
            mlflow_tracker.log_artifact(best_model_path, "models")
        
        # Log model with PyTorch flavor
        try:
            mlflow_tracker.log_model(
                model=model,
                artifact_path="model",
                registered_model_name=f"{backbone}_plant_classifier"
            )
            logger.success("Model logged to MLflow registry")
        except Exception as e:
            logger.warning(f"Could not log model to MLflow: {e}")
        
        # Set final tags
        mlflow_tracker.set_tags({
            "best_val_accuracy": f"{best_val_acc:.4f}",
            "best_epoch": str(best_epoch),
            "status": "completed"
        })
        
        # End run
        mlflow_tracker.end_run(status="FINISHED")
        
        # Print run info
        logger.info("\nMLflow Tracking:")
        logger.info(f"Experiment: {experiment_name}")
        logger.info(f"Run: {run_name}")
        logger.info(f"Tracking UI: {os.getenv('MLFLOW_TRACKING_URI', 'http://localhost:5001')}")
    
    return history, model


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train plant classifier with MLflow")
    
    # Model parameters
    parser.add_argument('--backbone', type=str, default='resnet18',
                       choices=['resnet18', 'resnet50', 'efficientnet_b0', 'mobilenet_v2'],
                       help='Backbone architecture')
    parser.add_argument('--epochs', type=int, default=10,
                       help='Number of training epochs')
    parser.add_argument('--batch-size', type=int, default=32,
                       help='Batch size')
    parser.add_argument('--learning-rate', type=float, default=1e-3,
                       help='Initial learning rate')
    parser.add_argument('--device', type=str, default='cuda' if torch.cuda.is_available() else 'cpu',
                       help='Device to train on')
    
    # Training parameters
    parser.add_argument('--freeze-backbone', action='store_true', default=True,
                       help='Freeze backbone initially')
    parser.add_argument('--unfreeze-epoch', type=int, default=5,
                       help='Epoch to unfreeze backbone')
    parser.add_argument('--early-stopping-patience', type=int, default=10,
                       help='Early stopping patience')
    
    # MLflow parameters
    parser.add_argument('--experiment-name', type=str, default='plant_classification',
                       help='MLflow experiment name')
    parser.add_argument('--run-name', type=str, default=None,
                       help='MLflow run name')
    parser.add_argument('--no-mlflow', action='store_true',
                       help='Disable MLflow tracking')
    
    args = parser.parse_args()
    
    # Train
    history, model = train_with_mlflow(
        backbone=args.backbone,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        device=args.device,
        freeze_backbone=args.freeze_backbone,
        unfreeze_epoch=args.unfreeze_epoch,
        early_stopping_patience=args.early_stopping_patience,
        experiment_name=args.experiment_name,
        run_name=args.run_name,
        track_mlflow=not args.no_mlflow
    )
