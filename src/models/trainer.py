"""
Training utilities and functions.
"""

import sys
from pathlib import Path
from typing import Dict, Optional, Tuple
import time
import json

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from tqdm import tqdm
from loguru import logger

sys.path.append(str(Path(__file__).parent.parent.parent))


class Trainer:
    """Model trainer with validation and checkpointing."""
    
    def __init__(
        self,
        model: nn.Module,
        train_loader: DataLoader,
        val_loader: DataLoader,
        criterion: nn.Module,
        optimizer: optim.Optimizer,
        device: torch.device,
        scheduler: Optional[optim.lr_scheduler._LRScheduler] = None,
        checkpoint_dir: Path = Path("models/checkpoints"),
        log_dir: Path = Path("logs")
    ):
        """
        Initialize trainer.
        
        Args:
            model: Model to train
            train_loader: Training data loader
            val_loader: Validation data loader
            criterion: Loss function
            optimizer: Optimizer
            device: Device to train on
            scheduler: Optional learning rate scheduler
            checkpoint_dir: Directory to save checkpoints
            log_dir: Directory to save logs
        """
        self.model = model
        self.train_loader = train_loader
        self.val_loader = val_loader
        self.criterion = criterion
        self.optimizer = optimizer
        self.device = device
        self.scheduler = scheduler
        
        self.checkpoint_dir = checkpoint_dir
        self.log_dir = log_dir
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.history = {
            'train_loss': [],
            'train_acc': [],
            'val_loss': [],
            'val_acc': [],
            'lr': []
        }
        
        self.best_val_acc = 0.0
        self.best_epoch = 0
    
    def train_epoch(self) -> Tuple[float, float]:
        """
        Train for one epoch.
        
        Returns:
            Tuple of (average_loss, accuracy)
        """
        self.model.train()
        running_loss = 0.0
        correct = 0
        total = 0
        
        pbar = tqdm(self.train_loader, desc="Training")
        for images, labels in pbar:
            images = images.to(self.device)
            labels = labels.to(self.device)
            
            # Forward pass
            self.optimizer.zero_grad()
            outputs = self.model(images)
            loss = self.criterion(outputs, labels)
            
            # Backward pass
            loss.backward()
            self.optimizer.step()
            
            # Statistics
            running_loss += loss.item() * images.size(0)
            _, predicted = outputs.max(1)
            total += labels.size(0)
            correct += predicted.eq(labels).sum().item()
            
            # Update progress bar
            pbar.set_postfix({
                'loss': f'{loss.item():.4f}',
                'acc': f'{100.*correct/total:.2f}%'
            })
        
        epoch_loss = running_loss / total
        epoch_acc = correct / total
        
        return epoch_loss, epoch_acc
    
    def validate(self) -> Tuple[float, float]:
        """
        Validate the model.
        
        Returns:
            Tuple of (average_loss, accuracy)
        """
        self.model.eval()
        running_loss = 0.0
        correct = 0
        total = 0
        
        with torch.no_grad():
            pbar = tqdm(self.val_loader, desc="Validation")
            for images, labels in pbar:
                images = images.to(self.device)
                labels = labels.to(self.device)
                
                # Forward pass
                outputs = self.model(images)
                loss = self.criterion(outputs, labels)
                
                # Statistics
                running_loss += loss.item() * images.size(0)
                _, predicted = outputs.max(1)
                total += labels.size(0)
                correct += predicted.eq(labels).sum().item()
                
                # Update progress bar
                pbar.set_postfix({
                    'loss': f'{loss.item():.4f}',
                    'acc': f'{100.*correct/total:.2f}%'
                })
        
        epoch_loss = running_loss / total
        epoch_acc = correct / total
        
        return epoch_loss, epoch_acc
    
    def save_checkpoint(
        self,
        epoch: int,
        val_acc: float,
        is_best: bool = False
    ):
        """
        Save model checkpoint.
        
        Args:
            epoch: Current epoch
            val_acc: Validation accuracy
            is_best: Whether this is the best model so far
        """
        checkpoint = {
            'epoch': epoch,
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'val_acc': val_acc,
            'history': self.history
        }
        
        if self.scheduler:
            checkpoint['scheduler_state_dict'] = self.scheduler.state_dict()
        
        # Save latest checkpoint
        checkpoint_path = self.checkpoint_dir / "latest_checkpoint.pth"
        torch.save(checkpoint, checkpoint_path)
        
        # Save best checkpoint
        if is_best:
            best_path = self.checkpoint_dir / "best_model.pth"
            torch.save(checkpoint, best_path)
            logger.info(f"✓ Best model saved with val_acc={val_acc:.4f}")
    
    def train(
        self,
        num_epochs: int,
        early_stopping_patience: int = 10
    ) -> Dict:
        """
        Train the model for multiple epochs.
        
        Args:
            num_epochs: Number of epochs to train
            early_stopping_patience: Patience for early stopping
        
        Returns:
            Training history
        """
        logger.info("="*80)
        logger.info("Starting training...")
        logger.info("="*80)
        logger.info(f"Device: {self.device}")
        logger.info(f"Epochs: {num_epochs}")
        logger.info(f"Train batches: {len(self.train_loader)}")
        logger.info(f"Val batches: {len(self.val_loader)}")
        logger.info("="*80)
        
        epochs_without_improvement = 0
        start_time = time.time()
        
        for epoch in range(1, num_epochs + 1):
            epoch_start = time.time()
            
            logger.info(f"\nEpoch {epoch}/{num_epochs}")
            logger.info("-" * 80)
            
            # Get current learning rate
            current_lr = self.optimizer.param_groups[0]['lr']
            
            # Train
            train_loss, train_acc = self.train_epoch()
            
            # Validate
            val_loss, val_acc = self.validate()
            
            # Update scheduler
            if self.scheduler:
                self.scheduler.step()
            
            # Update history
            self.history['train_loss'].append(train_loss)
            self.history['train_acc'].append(train_acc)
            self.history['val_loss'].append(val_loss)
            self.history['val_acc'].append(val_acc)
            self.history['lr'].append(current_lr)
            
            # Check if best model
            is_best = val_acc > self.best_val_acc
            if is_best:
                self.best_val_acc = val_acc
                self.best_epoch = epoch
                epochs_without_improvement = 0
            else:
                epochs_without_improvement += 1
            
            # Save checkpoint
            self.save_checkpoint(epoch, val_acc, is_best)
            
            # Log epoch results
            epoch_time = time.time() - epoch_start
            logger.info(f"\nEpoch {epoch} Summary:")
            logger.info(f"  Train Loss: {train_loss:.4f} | Train Acc: {train_acc*100:.2f}%")
            logger.info(f"  Val Loss:   {val_loss:.4f} | Val Acc:   {val_acc*100:.2f}%")
            logger.info(f"  LR: {current_lr:.6f}")
            logger.info(f"  Time: {epoch_time:.2f}s")
            if is_best:
                logger.info(f"  ✓ New best model!")
            
            # Early stopping
            if epochs_without_improvement >= early_stopping_patience:
                logger.info(f"\nEarly stopping triggered after {epoch} epochs")
                logger.info(f"Best validation accuracy: {self.best_val_acc*100:.2f}% at epoch {self.best_epoch}")
                break
        
        total_time = time.time() - start_time
        
        logger.info("\n" + "="*80)
        logger.info("Training completed!")
        logger.info("="*80)
        logger.info(f"Total time: {total_time/60:.2f} minutes")
        logger.info(f"Best validation accuracy: {self.best_val_acc*100:.2f}% at epoch {self.best_epoch}")
        
        # Save training history
        history_path = self.log_dir / "training_history.json"
        with open(history_path, 'w') as f:
            json.dump(self.history, f, indent=2)
        logger.info(f"Training history saved to {history_path}")
        
        return self.history


def create_optimizer(
    model: nn.Module,
    optimizer_name: str = 'adam',
    learning_rate: float = 1e-3,
    weight_decay: float = 1e-4
) -> optim.Optimizer:
    """
    Create optimizer.
    
    Args:
        model: Model to optimize
        optimizer_name: Optimizer name ('adam', 'sgd', 'adamw')
        learning_rate: Initial learning rate
        weight_decay: Weight decay (L2 regularization)
    
    Returns:
        Optimizer instance
    """
    if optimizer_name.lower() == 'adam':
        optimizer = optim.Adam(
            model.parameters(),
            lr=learning_rate,
            weight_decay=weight_decay
        )
    elif optimizer_name.lower() == 'adamw':
        optimizer = optim.AdamW(
            model.parameters(),
            lr=learning_rate,
            weight_decay=weight_decay
        )
    elif optimizer_name.lower() == 'sgd':
        optimizer = optim.SGD(
            model.parameters(),
            lr=learning_rate,
            momentum=0.9,
            weight_decay=weight_decay
        )
    else:
        raise ValueError(f"Unsupported optimizer: {optimizer_name}")
    
    logger.info(f"Created {optimizer_name} optimizer with lr={learning_rate}")
    return optimizer


def create_scheduler(
    optimizer: optim.Optimizer,
    scheduler_name: str = 'cosine',
    num_epochs: int = 50
) -> Optional[optim.lr_scheduler._LRScheduler]:
    """
    Create learning rate scheduler.
    
    Args:
        optimizer: Optimizer
        scheduler_name: Scheduler name ('cosine', 'step', 'none')
        num_epochs: Total number of epochs
    
    Returns:
        Scheduler instance or None
    """
    if scheduler_name.lower() == 'cosine':
        scheduler = optim.lr_scheduler.CosineAnnealingLR(
            optimizer,
            T_max=num_epochs
        )
        logger.info(f"Created CosineAnnealingLR scheduler")
    elif scheduler_name.lower() == 'step':
        scheduler = optim.lr_scheduler.StepLR(
            optimizer,
            step_size=10,
            gamma=0.1
        )
        logger.info(f"Created StepLR scheduler")
    elif scheduler_name.lower() == 'none':
        scheduler = None
        logger.info("No scheduler used")
    else:
        raise ValueError(f"Unsupported scheduler: {scheduler_name}")
    
    return scheduler
