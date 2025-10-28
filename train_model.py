"""
Simplified training script with common configurations.
"""

import sys
from pathlib import Path
import subprocess

sys.path.append(str(Path(__file__).parent.parent))

from loguru import logger


def train_model(
    backbone: str = 'resnet18',
    epochs: int = 30,
    batch_size: int = 32,
    learning_rate: float = 1e-3,
    fast_mode: bool = False
):
    """
    Train a model with specified configuration.
    
    Args:
        backbone: Model architecture
        epochs: Number of training epochs
        batch_size: Batch size
        learning_rate: Learning rate
        fast_mode: Use faster training for testing (smaller model, fewer epochs)
    """
    if fast_mode:
        backbone = 'resnet18'
        epochs = 10
        batch_size = 32
        logger.info("Fast mode enabled: using ResNet18 with 10 epochs")
    
    cmd = [
        'python3', 'src/models/train.py',
        '--backbone', backbone,
        '--epochs', str(epochs),
        '--batch-size', str(batch_size),
        '--learning-rate', str(learning_rate),
        '--early-stopping-patience', '10'
    ]
    
    logger.info(f"Training command: {' '.join(cmd)}")
    
    result = subprocess.run(cmd, cwd=Path(__file__).parent.parent)
    return result.returncode == 0


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Train plant classification model (simplified)")
    parser.add_argument('--backbone', type=str, default='resnet18',
                        choices=['resnet18', 'resnet50', 'efficientnet_b0', 'mobilenet_v2'],
                        help='Model backbone (default: resnet18)')
    parser.add_argument('--epochs', type=int, default=30,
                        help='Number of epochs (default: 30)')
    parser.add_argument('--batch-size', type=int, default=32,
                        help='Batch size (default: 32)')
    parser.add_argument('--learning-rate', type=float, default=1e-3,
                        help='Learning rate (default: 1e-3)')
    parser.add_argument('--fast', action='store_true',
                        help='Fast mode for testing (ResNet18, 10 epochs)')
    
    args = parser.parse_args()
    
    success = train_model(
        backbone=args.backbone,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        fast_mode=args.fast
    )
    
    if success:
        logger.success("✓ Training completed successfully!")
    else:
        logger.error("✗ Training failed!")
        sys.exit(1)
