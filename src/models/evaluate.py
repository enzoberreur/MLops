"""
Model evaluation and testing utilities.
"""

import sys
from pathlib import Path
from typing import Dict, List, Tuple
import json

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
import numpy as np
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report
)
import matplotlib.pyplot as plt
import seaborn as sns
from tqdm import tqdm
from loguru import logger

sys.path.append(str(Path(__file__).parent.parent.parent))

from src.models.model import load_model
from src.config.config import LABELS


def evaluate_model(
    model: nn.Module,
    dataloader: DataLoader,
    device: torch.device,
    class_names: List[str] = LABELS
) -> Dict:
    """
    Evaluate model on a dataset.
    
    Args:
        model: Model to evaluate
        dataloader: Data loader
        device: Device to use
        class_names: List of class names
    
    Returns:
        Dictionary with metrics
    """
    model.eval()
    
    all_preds = []
    all_labels = []
    all_probs = []
    
    logger.info("Evaluating model...")
    
    with torch.no_grad():
        for images, labels in tqdm(dataloader, desc="Evaluation"):
            images = images.to(device)
            labels = labels.to(device)
            
            # Forward pass
            outputs = model(images)
            probs = torch.softmax(outputs, dim=1)
            _, predicted = outputs.max(1)
            
            all_preds.extend(predicted.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())
            all_probs.extend(probs.cpu().numpy())
    
    # Convert to numpy arrays
    all_preds = np.array(all_preds)
    all_labels = np.array(all_labels)
    all_probs = np.array(all_probs)
    
    # Calculate metrics
    accuracy = accuracy_score(all_labels, all_preds)
    precision = precision_score(all_labels, all_preds, average='weighted')
    recall = recall_score(all_labels, all_preds, average='weighted')
    f1 = f1_score(all_labels, all_preds, average='weighted')
    
    # Confusion matrix
    cm = confusion_matrix(all_labels, all_preds)
    
    # Classification report
    report = classification_report(
        all_labels,
        all_preds,
        target_names=class_names,
        output_dict=True
    )
    
    metrics = {
        'accuracy': float(accuracy),
        'precision': float(precision),
        'recall': float(recall),
        'f1_score': float(f1),
        'confusion_matrix': cm.tolist(),
        'classification_report': report,
        'predictions': all_preds.tolist(),
        'labels': all_labels.tolist(),
        'probabilities': all_probs.tolist()
    }
    
    return metrics


def plot_confusion_matrix(
    cm: np.ndarray,
    class_names: List[str],
    save_path: Path,
    normalize: bool = False
):
    """
    Plot confusion matrix.
    
    Args:
        cm: Confusion matrix
        class_names: List of class names
        save_path: Path to save plot
        normalize: Whether to normalize values
    """
    if normalize:
        cm = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]
        fmt = '.2%'
        title = 'Normalized Confusion Matrix'
    else:
        fmt = 'd'
        title = 'Confusion Matrix'
    
    plt.figure(figsize=(10, 8))
    sns.heatmap(
        cm,
        annot=True,
        fmt=fmt,
        cmap='Blues',
        xticklabels=class_names,
        yticklabels=class_names,
        cbar_kws={'label': 'Count' if not normalize else 'Proportion'}
    )
    plt.title(title, fontsize=16, fontweight='bold')
    plt.ylabel('True Label', fontsize=12)
    plt.xlabel('Predicted Label', fontsize=12)
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    logger.info(f"Confusion matrix saved to {save_path}")


def plot_training_history(
    history: Dict,
    save_path: Path
):
    """
    Plot training history.
    
    Args:
        history: Training history dictionary
        save_path: Path to save plot
    """
    fig, axes = plt.subplots(1, 2, figsize=(15, 5))
    
    # Loss plot
    axes[0].plot(history['train_loss'], label='Train Loss', linewidth=2)
    axes[0].plot(history['val_loss'], label='Val Loss', linewidth=2)
    axes[0].set_xlabel('Epoch', fontsize=12)
    axes[0].set_ylabel('Loss', fontsize=12)
    axes[0].set_title('Training and Validation Loss', fontsize=14, fontweight='bold')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    
    # Accuracy plot
    axes[1].plot([acc*100 for acc in history['train_acc']], label='Train Acc', linewidth=2)
    axes[1].plot([acc*100 for acc in history['val_acc']], label='Val Acc', linewidth=2)
    axes[1].set_xlabel('Epoch', fontsize=12)
    axes[1].set_ylabel('Accuracy (%)', fontsize=12)
    axes[1].set_title('Training and Validation Accuracy', fontsize=14, fontweight='bold')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    logger.info(f"Training history plot saved to {save_path}")


def print_evaluation_report(metrics: Dict, class_names: List[str]):
    """
    Print evaluation report.
    
    Args:
        metrics: Metrics dictionary
        class_names: List of class names
    """
    logger.info("\n" + "="*80)
    logger.info("EVALUATION RESULTS")
    logger.info("="*80)
    
    logger.info(f"\nOverall Metrics:")
    logger.info(f"  Accuracy:  {metrics['accuracy']*100:.2f}%")
    logger.info(f"  Precision: {metrics['precision']*100:.2f}%")
    logger.info(f"  Recall:    {metrics['recall']*100:.2f}%")
    logger.info(f"  F1 Score:  {metrics['f1_score']*100:.2f}%")
    
    logger.info(f"\nPer-Class Metrics:")
    report = metrics['classification_report']
    for class_name in class_names:
        if class_name in report:
            class_metrics = report[class_name]
            logger.info(f"  {class_name.capitalize()}:")
            logger.info(f"    Precision: {class_metrics['precision']*100:.2f}%")
            logger.info(f"    Recall:    {class_metrics['recall']*100:.2f}%")
            logger.info(f"    F1 Score:  {class_metrics['f1-score']*100:.2f}%")
            logger.info(f"    Support:   {class_metrics['support']}")
    
    logger.info(f"\nConfusion Matrix:")
    cm = np.array(metrics['confusion_matrix'])
    logger.info(f"  True \\ Pred | {' | '.join([f'{name:^10}' for name in class_names])}")
    logger.info("  " + "-"*50)
    for i, class_name in enumerate(class_names):
        row = " | ".join([f"{val:^10}" for val in cm[i]])
        logger.info(f"  {class_name:^12} | {row}")
    
    logger.info("\n" + "="*80)


def main():
    """Main evaluation function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Evaluate plant classification model")
    parser.add_argument('--checkpoint', type=str, required=True,
                        help='Path to model checkpoint')
    parser.add_argument('--backbone', type=str, default='resnet50',
                        help='Model backbone')
    parser.add_argument('--split', type=str, default='test',
                        choices=['train', 'val', 'test'],
                        help='Dataset split to evaluate (default: test)')
    parser.add_argument('--batch-size', type=int, default=32,
                        help='Batch size (default: 32)')
    parser.add_argument('--output-dir', type=str, default='models/evaluation',
                        help='Output directory (default: models/evaluation)')
    
    args = parser.parse_args()
    
    # Setup
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    logger.info(f"Using device: {device}")
    
    # Load model
    logger.info(f"Loading model from {args.checkpoint}...")
    model = load_model(
        checkpoint_path=args.checkpoint,
        num_classes=len(LABELS),
        backbone=args.backbone,
        device=device
    )
    
    # Load data
    from src.models.dataset import (
        load_image_paths_and_labels,
        create_data_splits,
        create_dataloaders
    )
    
    logger.info("Loading data...")
    image_paths, labels = load_image_paths_and_labels()
    splits = create_data_splits(image_paths, labels)
    dataloaders = create_dataloaders(splits, batch_size=args.batch_size)
    
    dataloader = dataloaders[args.split]
    logger.info(f"Evaluating on {args.split} set: {len(dataloader.dataset)} samples")
    
    # Evaluate
    metrics = evaluate_model(model, dataloader, device, LABELS)
    
    # Print report
    print_evaluation_report(metrics, LABELS)
    
    # Save metrics
    metrics_path = output_dir / f"{args.split}_metrics.json"
    with open(metrics_path, 'w') as f:
        # Remove large arrays for JSON
        metrics_copy = metrics.copy()
        metrics_copy.pop('predictions', None)
        metrics_copy.pop('labels', None)
        metrics_copy.pop('probabilities', None)
        json.dump(metrics_copy, f, indent=2)
    logger.info(f"\nMetrics saved to {metrics_path}")
    
    # Plot confusion matrix
    cm = np.array(metrics['confusion_matrix'])
    cm_path = output_dir / f"{args.split}_confusion_matrix.png"
    plot_confusion_matrix(cm, LABELS, cm_path, normalize=False)
    
    cm_norm_path = output_dir / f"{args.split}_confusion_matrix_normalized.png"
    plot_confusion_matrix(cm, LABELS, cm_norm_path, normalize=True)
    
    # Plot training history if available
    checkpoint = torch.load(args.checkpoint, map_location=device)
    if 'history' in checkpoint:
        history_path = output_dir / "training_history.png"
        plot_training_history(checkpoint['history'], history_path)
    
    logger.info("\n✓ Evaluation complete!")


if __name__ == "__main__":
    main()
