"""
Model architecture using transfer learning.
"""

import sys
from pathlib import Path
from typing import Optional

import torch
import torch.nn as nn
from torchvision import models
from loguru import logger

sys.path.append(str(Path(__file__).parent.parent.parent))


class PlantClassifier(nn.Module):
    """
    Plant classification model using transfer learning.
    Supports multiple pretrained backbones.
    """
    
    def __init__(
        self,
        num_classes: int = 2,
        backbone: str = 'resnet50',
        pretrained: bool = True,
        dropout: float = 0.5
    ):
        """
        Initialize model.
        
        Args:
            num_classes: Number of output classes
            backbone: Pretrained model to use ('resnet50', 'resnet18', 'efficientnet_b0')
            pretrained: Whether to use pretrained weights
            dropout: Dropout rate for final layers
        """
        super(PlantClassifier, self).__init__()
        
        self.backbone_name = backbone
        self.num_classes = num_classes
        
        # Load pretrained backbone
        if backbone == 'resnet50':
            self.backbone = models.resnet50(pretrained=pretrained)
            num_features = self.backbone.fc.in_features
            # Replace final layer
            self.backbone.fc = nn.Identity()
            
        elif backbone == 'resnet18':
            self.backbone = models.resnet18(pretrained=pretrained)
            num_features = self.backbone.fc.in_features
            self.backbone.fc = nn.Identity()
            
        elif backbone == 'efficientnet_b0':
            self.backbone = models.efficientnet_b0(pretrained=pretrained)
            num_features = self.backbone.classifier[1].in_features
            self.backbone.classifier = nn.Identity()
            
        elif backbone == 'mobilenet_v2':
            self.backbone = models.mobilenet_v2(pretrained=pretrained)
            num_features = self.backbone.classifier[1].in_features
            self.backbone.classifier = nn.Identity()
            
        else:
            raise ValueError(f"Unsupported backbone: {backbone}")
        
        # Custom classifier head
        self.classifier = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(num_features, 512),
            nn.ReLU(),
            nn.BatchNorm1d(512),
            nn.Dropout(dropout / 2),
            nn.Linear(512, 128),
            nn.ReLU(),
            nn.BatchNorm1d(128),
            nn.Dropout(dropout / 2),
            nn.Linear(128, num_classes)
        )
        
        logger.info(f"Created {backbone} model with {num_classes} classes")
        logger.info(f"Feature dimension: {num_features}")
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass.
        
        Args:
            x: Input tensor [batch_size, 3, height, width]
        
        Returns:
            Output logits [batch_size, num_classes]
        """
        features = self.backbone(x)
        output = self.classifier(features)
        return output
    
    def freeze_backbone(self):
        """Freeze backbone parameters for fine-tuning."""
        for param in self.backbone.parameters():
            param.requires_grad = False
        logger.info("Backbone frozen")
    
    def unfreeze_backbone(self):
        """Unfreeze backbone parameters."""
        for param in self.backbone.parameters():
            param.requires_grad = True
        logger.info("Backbone unfrozen")
    
    def get_num_trainable_params(self) -> int:
        """Get number of trainable parameters."""
        return sum(p.numel() for p in self.parameters() if p.requires_grad)
    
    def get_num_total_params(self) -> int:
        """Get total number of parameters."""
        return sum(p.numel() for p in self.parameters())


def create_model(
    num_classes: int = 2,
    backbone: str = 'resnet50',
    pretrained: bool = True,
    dropout: float = 0.5,
    device: Optional[torch.device] = None
) -> PlantClassifier:
    """
    Create and initialize a model.
    
    Args:
        num_classes: Number of output classes
        backbone: Pretrained model to use
        pretrained: Whether to use pretrained weights
        dropout: Dropout rate
        device: Device to move model to
    
    Returns:
        Initialized model
    """
    model = PlantClassifier(
        num_classes=num_classes,
        backbone=backbone,
        pretrained=pretrained,
        dropout=dropout
    )
    
    if device is not None:
        model = model.to(device)
        logger.info(f"Model moved to {device}")
    
    # Log model info
    trainable_params = model.get_num_trainable_params()
    total_params = model.get_num_total_params()
    logger.info(f"Total parameters: {total_params:,}")
    logger.info(f"Trainable parameters: {trainable_params:,}")
    
    return model


def load_model(
    checkpoint_path: str,
    num_classes: int = 2,
    backbone: str = 'resnet50',
    device: Optional[torch.device] = None
) -> PlantClassifier:
    """
    Load a model from checkpoint.
    
    Args:
        checkpoint_path: Path to checkpoint file
        num_classes: Number of output classes
        backbone: Backbone architecture
        device: Device to load model to
    
    Returns:
        Loaded model
    """
    model = PlantClassifier(
        num_classes=num_classes,
        backbone=backbone,
        pretrained=False
    )
    
    checkpoint = torch.load(checkpoint_path, map_location=device)
    model.load_state_dict(checkpoint['model_state_dict'])
    
    if device is not None:
        model = model.to(device)
    
    logger.info(f"Model loaded from {checkpoint_path}")
    
    return model


if __name__ == "__main__":
    # Test model creation
    logger.info("Testing model creation...")
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    logger.info(f"Using device: {device}")
    
    # Test different backbones
    backbones = ['resnet18', 'resnet50', 'efficientnet_b0', 'mobilenet_v2']
    
    for backbone in backbones:
        logger.info(f"\nTesting {backbone}...")
        model = create_model(
            num_classes=2,
            backbone=backbone,
            pretrained=False,  # Don't download weights for testing
            device=device
        )
        
        # Test forward pass
        dummy_input = torch.randn(2, 3, 224, 224).to(device)
        output = model(dummy_input)
        logger.info(f"Output shape: {output.shape}")
        
        assert output.shape == (2, 2), f"Expected (2, 2), got {output.shape}"
    
    logger.info("\n✓ Model creation test passed!")
