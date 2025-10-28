"""
Main training script for plant classification model.
"""

import sys
from pathlib import Path
import argparse

import torch
import torch.nn as nn
from loguru import logger

sys.path.append(str(Path(__file__).parent.parent.parent))

from src.models.dataset import (
    load_image_paths_and_labels,
    create_data_splits,
    create_dataloaders
)
from src.models.model import create_model
from src.models.trainer import Trainer, create_optimizer, create_scheduler
from src.config.config import IMAGE_SIZE, LABELS


def main(args):
    """Main training function."""
    # Setup
    logger.info("="*80)
    logger.info("PLANT CLASSIFICATION MODEL TRAINING")
    logger.info("="*80)
    
    # Set random seed for reproducibility
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(args.seed)
    
    # Device
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    logger.info(f"Using device: {device}")
    if torch.cuda.is_available():
        logger.info(f"GPU: {torch.cuda.get_device_name(0)}")
    
    # Load data
    logger.info("\nLoading data...")
    image_paths, labels = load_image_paths_and_labels()
    logger.info(f"Total images: {len(image_paths)}")
    
    # Create splits
    logger.info("\nCreating data splits...")
    splits = create_data_splits(
        image_paths,
        labels,
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
        test_ratio=args.test_ratio,
        random_state=args.seed
    )
    
    # Create dataloaders
    logger.info("\nCreating data loaders...")
    dataloaders = create_dataloaders(
        splits,
        batch_size=args.batch_size,
        num_workers=args.num_workers,
        image_size=IMAGE_SIZE
    )
    
    # Create model
    logger.info(f"\nCreating {args.backbone} model...")
    model = create_model(
        num_classes=len(LABELS),
        backbone=args.backbone,
        pretrained=args.pretrained,
        dropout=args.dropout,
        device=device
    )
    
    # Optionally freeze backbone for initial training
    if args.freeze_backbone:
        model.freeze_backbone()
        logger.info("Backbone frozen for initial training")
    
    # Loss function
    criterion = nn.CrossEntropyLoss()
    logger.info(f"Loss function: CrossEntropyLoss")
    
    # Optimizer
    optimizer = create_optimizer(
        model,
        optimizer_name=args.optimizer,
        learning_rate=args.learning_rate,
        weight_decay=args.weight_decay
    )
    
    # Scheduler
    scheduler = create_scheduler(
        optimizer,
        scheduler_name=args.scheduler,
        num_epochs=args.epochs
    )
    
    # Create trainer
    checkpoint_dir = Path(args.checkpoint_dir)
    log_dir = Path(args.log_dir)
    
    trainer = Trainer(
        model=model,
        train_loader=dataloaders['train'],
        val_loader=dataloaders['val'],
        criterion=criterion,
        optimizer=optimizer,
        device=device,
        scheduler=scheduler,
        checkpoint_dir=checkpoint_dir,
        log_dir=log_dir
    )
    
    # Train
    logger.info("\n" + "="*80)
    history = trainer.train(
        num_epochs=args.epochs,
        early_stopping_patience=args.early_stopping_patience
    )
    
    # Save final model info
    model_info = {
        'backbone': args.backbone,
        'num_classes': len(LABELS),
        'image_size': IMAGE_SIZE,
        'best_val_acc': trainer.best_val_acc,
        'best_epoch': trainer.best_epoch,
        'labels': LABELS
    }
    
    import json
    info_path = checkpoint_dir / "model_info.json"
    with open(info_path, 'w') as f:
        json.dump(model_info, f, indent=2)
    logger.info(f"\nModel info saved to {info_path}")
    
    logger.info("\n" + "="*80)
    logger.info("Training complete!")
    logger.info(f"Best model saved to: {checkpoint_dir / 'best_model.pth'}")
    logger.info(f"Best validation accuracy: {trainer.best_val_acc*100:.2f}%")
    logger.info("="*80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train plant classification model")
    
    # Data parameters
    parser.add_argument('--train-ratio', type=float, default=0.7,
                        help='Training set ratio (default: 0.7)')
    parser.add_argument('--val-ratio', type=float, default=0.15,
                        help='Validation set ratio (default: 0.15)')
    parser.add_argument('--test-ratio', type=float, default=0.15,
                        help='Test set ratio (default: 0.15)')
    parser.add_argument('--batch-size', type=int, default=32,
                        help='Batch size (default: 32)')
    parser.add_argument('--num-workers', type=int, default=4,
                        help='Number of data loading workers (default: 4)')
    
    # Model parameters
    parser.add_argument('--backbone', type=str, default='resnet50',
                        choices=['resnet18', 'resnet50', 'efficientnet_b0', 'mobilenet_v2'],
                        help='Model backbone (default: resnet50)')
    parser.add_argument('--pretrained', action='store_true', default=True,
                        help='Use pretrained weights (default: True)')
    parser.add_argument('--no-pretrained', dest='pretrained', action='store_false',
                        help='Do not use pretrained weights')
    parser.add_argument('--dropout', type=float, default=0.5,
                        help='Dropout rate (default: 0.5)')
    parser.add_argument('--freeze-backbone', action='store_true',
                        help='Freeze backbone during training')
    
    # Training parameters
    parser.add_argument('--epochs', type=int, default=50,
                        help='Number of epochs (default: 50)')
    parser.add_argument('--optimizer', type=str, default='adam',
                        choices=['adam', 'adamw', 'sgd'],
                        help='Optimizer (default: adam)')
    parser.add_argument('--learning-rate', type=float, default=1e-3,
                        help='Learning rate (default: 1e-3)')
    parser.add_argument('--weight-decay', type=float, default=1e-4,
                        help='Weight decay (default: 1e-4)')
    parser.add_argument('--scheduler', type=str, default='cosine',
                        choices=['cosine', 'step', 'none'],
                        help='Learning rate scheduler (default: cosine)')
    parser.add_argument('--early-stopping-patience', type=int, default=10,
                        help='Early stopping patience (default: 10)')
    
    # Other parameters
    parser.add_argument('--seed', type=int, default=42,
                        help='Random seed (default: 42)')
    parser.add_argument('--checkpoint-dir', type=str, default='models/checkpoints',
                        help='Checkpoint directory (default: models/checkpoints)')
    parser.add_argument('--log-dir', type=str, default='logs/training',
                        help='Log directory (default: logs/training)')
    
    args = parser.parse_args()
    
    # Create directories
    Path("logs/training").mkdir(parents=True, exist_ok=True)
    
    main(args)
