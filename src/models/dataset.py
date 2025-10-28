"""
PyTorch Dataset and DataLoader for plant image classification.
"""

import sys
from pathlib import Path
from typing import Tuple, List, Optional, Dict
import random

import torch
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from PIL import Image
import numpy as np
from sklearn.model_selection import train_test_split
from loguru import logger

sys.path.append(str(Path(__file__).parent.parent.parent))

from src.config.config import PROCESSED_DATA_DIR, LABELS, IMAGE_SIZE


class PlantDataset(Dataset):
    """PyTorch Dataset for plant images."""
    
    def __init__(
        self,
        image_paths: List[Path],
        labels: List[int],
        transform: Optional[transforms.Compose] = None
    ):
        """
        Initialize dataset.
        
        Args:
            image_paths: List of paths to images
            labels: List of corresponding labels (0 or 1)
            transform: Optional transform to apply to images
        """
        self.image_paths = image_paths
        self.labels = labels
        self.transform = transform
        
        assert len(image_paths) == len(labels), "Mismatch between images and labels"
    
    def __len__(self) -> int:
        """Return the number of samples."""
        return len(self.image_paths)
    
    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, int]:
        """
        Get a sample.
        
        Args:
            idx: Index of sample
        
        Returns:
            Tuple of (image_tensor, label)
        """
        # Load image
        img_path = self.image_paths[idx]
        image = Image.open(img_path).convert('RGB')
        
        # Apply transforms
        if self.transform:
            image = self.transform(image)
        
        # Get label
        label = self.labels[idx]
        
        return image, label


def get_data_transforms(image_size: int = IMAGE_SIZE) -> Dict[str, transforms.Compose]:
    """
    Get train and validation transforms.
    
    Args:
        image_size: Target image size
    
    Returns:
        Dictionary with 'train' and 'val' transforms
    """
    # Training transforms with data augmentation
    train_transforms = transforms.Compose([
        transforms.Resize((image_size, image_size)),
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.RandomVerticalFlip(p=0.5),
        transforms.RandomRotation(degrees=30),
        transforms.ColorJitter(
            brightness=0.2,
            contrast=0.2,
            saturation=0.2,
            hue=0.1
        ),
        transforms.RandomAffine(
            degrees=0,
            translate=(0.1, 0.1),
            scale=(0.9, 1.1)
        ),
        transforms.ToTensor(),
        transforms.Normalize(
            mean=[0.485, 0.456, 0.406],  # ImageNet mean
            std=[0.229, 0.224, 0.225]     # ImageNet std
        )
    ])
    
    # Validation transforms (no augmentation)
    val_transforms = transforms.Compose([
        transforms.Resize((image_size, image_size)),
        transforms.ToTensor(),
        transforms.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225]
        )
    ])
    
    return {
        'train': train_transforms,
        'val': val_transforms,
        'test': val_transforms
    }


def load_image_paths_and_labels(
    data_dir: Path = PROCESSED_DATA_DIR,
    label_mapping: Optional[Dict[str, int]] = None
) -> Tuple[List[Path], List[int]]:
    """
    Load all image paths and their corresponding labels.
    
    Args:
        data_dir: Directory containing processed images
        label_mapping: Optional mapping from label names to integers
    
    Returns:
        Tuple of (image_paths, labels)
    """
    if label_mapping is None:
        label_mapping = {label: idx for idx, label in enumerate(LABELS)}
    
    image_paths = []
    labels = []
    
    for label_name, label_idx in label_mapping.items():
        label_dir = data_dir / label_name
        
        if not label_dir.exists():
            logger.warning(f"Directory not found: {label_dir}")
            continue
        
        # Get all images
        images = list(label_dir.glob("*.jpg"))
        logger.info(f"Found {len(images)} images for label '{label_name}' (id={label_idx})")
        
        image_paths.extend(images)
        labels.extend([label_idx] * len(images))
    
    # Shuffle data
    combined = list(zip(image_paths, labels))
    random.shuffle(combined)
    image_paths, labels = zip(*combined)
    
    return list(image_paths), list(labels)


def create_data_splits(
    image_paths: List[Path],
    labels: List[int],
    train_ratio: float = 0.7,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    random_state: int = 42
) -> Dict[str, Tuple[List[Path], List[int]]]:
    """
    Split data into train, validation, and test sets.
    
    Args:
        image_paths: List of image paths
        labels: List of labels
        train_ratio: Ratio for training set
        val_ratio: Ratio for validation set
        test_ratio: Ratio for test set
        random_state: Random seed for reproducibility
    
    Returns:
        Dictionary with 'train', 'val', and 'test' splits
    """
    assert abs(train_ratio + val_ratio + test_ratio - 1.0) < 1e-6, \
        "Ratios must sum to 1.0"
    
    # First split: train and temp (val + test)
    train_paths, temp_paths, train_labels, temp_labels = train_test_split(
        image_paths,
        labels,
        test_size=(val_ratio + test_ratio),
        random_state=random_state,
        stratify=labels
    )
    
    # Second split: val and test
    val_size = val_ratio / (val_ratio + test_ratio)
    val_paths, test_paths, val_labels, test_labels = train_test_split(
        temp_paths,
        temp_labels,
        test_size=(1 - val_size),
        random_state=random_state,
        stratify=temp_labels
    )
    
    logger.info(f"Data splits created:")
    logger.info(f"  Train: {len(train_paths)} samples")
    logger.info(f"  Val:   {len(val_paths)} samples")
    logger.info(f"  Test:  {len(test_paths)} samples")
    
    return {
        'train': (train_paths, train_labels),
        'val': (val_paths, val_labels),
        'test': (test_paths, test_labels)
    }


def create_dataloaders(
    data_splits: Dict[str, Tuple[List[Path], List[int]]],
    batch_size: int = 32,
    num_workers: int = 4,
    image_size: int = IMAGE_SIZE
) -> Dict[str, DataLoader]:
    """
    Create DataLoaders for train, val, and test sets.
    
    Args:
        data_splits: Dictionary with data splits
        batch_size: Batch size for training
        num_workers: Number of worker processes for data loading
        image_size: Target image size
    
    Returns:
        Dictionary with DataLoaders for each split
    """
    transforms_dict = get_data_transforms(image_size)
    dataloaders = {}
    
    for split_name, (paths, labels) in data_splits.items():
        dataset = PlantDataset(
            image_paths=paths,
            labels=labels,
            transform=transforms_dict[split_name]
        )
        
        # Use shuffle for train, not for val/test
        shuffle = (split_name == 'train')
        
        dataloader = DataLoader(
            dataset,
            batch_size=batch_size,
            shuffle=shuffle,
            num_workers=num_workers,
            pin_memory=True if torch.cuda.is_available() else False
        )
        
        dataloaders[split_name] = dataloader
        logger.info(f"Created {split_name} DataLoader: "
                   f"{len(dataset)} samples, "
                   f"{len(dataloader)} batches")
    
    return dataloaders


def get_class_distribution(labels: List[int]) -> Dict[int, int]:
    """
    Get class distribution from labels.
    
    Args:
        labels: List of labels
    
    Returns:
        Dictionary mapping class to count
    """
    distribution = {}
    for label in labels:
        distribution[label] = distribution.get(label, 0) + 1
    return distribution


if __name__ == "__main__":
    # Test data loading
    logger.info("Testing data loading...")
    
    # Load paths and labels
    image_paths, labels = load_image_paths_and_labels()
    logger.info(f"Loaded {len(image_paths)} images")
    
    # Show distribution
    dist = get_class_distribution(labels)
    logger.info(f"Class distribution: {dist}")
    
    # Create splits
    splits = create_data_splits(image_paths, labels)
    
    # Create dataloaders
    dataloaders = create_dataloaders(splits, batch_size=16)
    
    # Test one batch
    train_loader = dataloaders['train']
    images, labels = next(iter(train_loader))
    logger.info(f"Batch shape: images={images.shape}, labels={labels.shape}")
    logger.info("✓ Data loading test passed!")
