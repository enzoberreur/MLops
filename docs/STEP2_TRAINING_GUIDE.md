# Step 2: Model Training Guide

## Overview

This guide covers building and training a deep learning model for binary classification of dandelion and grass images using PyTorch and transfer learning.

## Model Architecture

### Transfer Learning Approach

We use **transfer learning** with pretrained models from ImageNet:

- **ResNet18** (default) - 11M parameters, fast training
- **ResNet50** - 23M parameters, better accuracy
- **EfficientNet-B0** - 5M parameters, efficient
- **MobileNet-V2** - 3M parameters, lightweight

### Custom Classifier Head

```
Backbone (pretrained) 
    ↓
Dropout (0.5)
    ↓
Linear (features → 512)
    ↓
ReLU + BatchNorm
    ↓
Dropout (0.25)
    ↓
Linear (512 → 128)
    ↓
ReLU + BatchNorm
    ↓
Dropout (0.25)
    ↓
Linear (128 → 2)
```

## Data Augmentation

### Training Augmentations
- Random horizontal flip (p=0.5)
- Random vertical flip (p=0.5)
- Random rotation (±30°)
- Color jitter (brightness, contrast, saturation, hue)
- Random affine (translation, scale)
- Normalization (ImageNet mean/std)

### Validation/Test
- Resize to 224x224
- Normalization only (no augmentation)

## Training Configuration

### Data Splits
- **Train**: 70% (280 images)
- **Validation**: 15% (60 images)
- **Test**: 15% (60 images)

### Hyperparameters (Default)
```python
backbone = 'resnet18'
epochs = 30
batch_size = 32
learning_rate = 1e-3
optimizer = 'adam'
weight_decay = 1e-4
scheduler = 'cosine'
dropout = 0.5
early_stopping_patience = 10
```

## Training the Model

### Option 1: Simplified Training (Recommended)

```bash
# Fast training (10 epochs, ResNet18)
python train_model.py --fast

# Standard training (30 epochs)
python train_model.py --backbone resnet18 --epochs 30

# High-quality training (50 epochs, ResNet50)
python train_model.py --backbone resnet50 --epochs 50
```

### Option 2: Advanced Training

```bash
python src/models/train.py \
    --backbone resnet18 \
    --epochs 30 \
    --batch-size 32 \
    --learning-rate 1e-3 \
    --optimizer adam \
    --scheduler cosine \
    --dropout 0.5 \
    --early-stopping-patience 10
```

### Available Arguments

```
Data:
  --train-ratio         Training set ratio (default: 0.7)
  --val-ratio           Validation set ratio (default: 0.15)
  --test-ratio          Test set ratio (default: 0.15)
  --batch-size          Batch size (default: 32)
  --num-workers         Data loading workers (default: 4)

Model:
  --backbone            Model architecture (resnet18, resnet50, efficientnet_b0, mobilenet_v2)
  --pretrained          Use pretrained weights (default: True)
  --dropout             Dropout rate (default: 0.5)
  --freeze-backbone     Freeze backbone during training

Training:
  --epochs              Number of epochs (default: 30)
  --optimizer           Optimizer (adam, adamw, sgd)
  --learning-rate       Learning rate (default: 1e-3)
  --weight-decay        Weight decay (default: 1e-4)
  --scheduler           LR scheduler (cosine, step, none)
  --early-stopping-patience  Early stopping patience (default: 10)

Other:
  --seed                Random seed (default: 42)
  --checkpoint-dir      Checkpoint directory
  --log-dir             Log directory
```

## Training Process

### What Happens During Training

1. **Data Loading**
   - Images loaded and split into train/val/test
   - Data augmentation applied to training set
   - DataLoaders created with batching

2. **Model Initialization**
   - Pretrained backbone loaded
   - Custom classifier head attached
   - Model moved to GPU/CPU

3. **Training Loop** (for each epoch)
   - Forward pass on training data
   - Loss calculation (CrossEntropyLoss)
   - Backward pass and optimization
   - Validation on validation set
   - Learning rate scheduling
   - Checkpoint saving

4. **Early Stopping**
   - Monitors validation accuracy
   - Stops if no improvement for N epochs
   - Saves best model automatically

### Monitoring Training

Training progress is logged to:
- **Console**: Real-time progress bars
- **File**: `logs/training/data_*.log`
- **Checkpoints**: `models/checkpoints/`

Example output:
```
Epoch 1/30
--------------------------------------------------------------------------------
Training: 100%|███████████████| 9/9 [00:15<00:00, loss=0.6234, acc=65.71%]
Validation: 100%|█████████████| 2/2 [00:01<00:00, loss=0.5123, acc=75.00%]

Epoch 1 Summary:
  Train Loss: 0.6234 | Train Acc: 65.71%
  Val Loss:   0.5123 | Val Acc:   75.00%
  LR: 0.001000
  Time: 16.23s
  ✓ New best model!
```

## Model Outputs

### Checkpoints
- `models/checkpoints/best_model.pth` - Best model based on validation accuracy
- `models/checkpoints/latest_checkpoint.pth` - Latest epoch checkpoint
- `models/checkpoints/model_info.json` - Model metadata

### Training History
- `logs/training/training_history.json` - Metrics for all epochs

### Model Info (JSON)
```json
{
  "backbone": "resnet18",
  "num_classes": 2,
  "image_size": 224,
  "best_val_acc": 0.9167,
  "best_epoch": 15,
  "labels": ["dandelion", "grass"]
}
```

## Evaluating the Model

### Run Evaluation

```bash
# Evaluate on test set
python src/models/evaluate.py \
    --checkpoint models/checkpoints/best_model.pth \
    --backbone resnet18 \
    --split test

# Evaluate on validation set
python src/models/evaluate.py \
    --checkpoint models/checkpoints/best_model.pth \
    --backbone resnet18 \
    --split val
```

### Evaluation Outputs

1. **Console Report**
   - Overall metrics (accuracy, precision, recall, F1)
   - Per-class metrics
   - Confusion matrix

2. **Saved Files** (`models/evaluation/`)
   - `test_metrics.json` - Detailed metrics
   - `test_confusion_matrix.png` - Confusion matrix plot
   - `test_confusion_matrix_normalized.png` - Normalized confusion matrix
   - `training_history.png` - Loss and accuracy curves

### Expected Performance

With default settings (ResNet18, 30 epochs):
- **Accuracy**: 90-95%
- **Training time**: ~5-10 minutes (CPU), ~2-3 minutes (GPU)
- **Model size**: ~45 MB

## Tips for Better Performance

### 1. Use a Larger Model
```bash
python train_model.py --backbone resnet50 --epochs 50
```

### 2. Adjust Learning Rate
```bash
python src/models/train.py --learning-rate 5e-4
```

### 3. Increase Training Time
```bash
python train_model.py --epochs 50 --early-stopping-patience 15
```

### 4. Fine-tune Pretrained Model
```bash
# First: Train with frozen backbone
python src/models/train.py --freeze-backbone --epochs 10

# Then: Unfreeze and train end-to-end
python src/models/train.py --epochs 30
```

### 5. Use GPU if Available
Model automatically detects and uses GPU if available:
```
Using device: cuda
GPU: NVIDIA GeForce RTX 3080
```

## Troubleshooting

### Low Accuracy
- Increase epochs
- Try different backbone (ResNet50)
- Adjust learning rate
- Check data quality

### Overfitting (Train >> Val)
- Increase dropout
- Add more data augmentation
- Use smaller model
- Add weight decay

### Out of Memory
- Reduce batch size
- Use smaller model (MobileNet-V2)
- Reduce image size in config

### Slow Training
- Use GPU
- Increase num_workers
- Use smaller model (ResNet18)

## Code Structure

```
src/models/
├── __init__.py
├── dataset.py          # Data loading and augmentation
├── model.py            # Model architecture
├── trainer.py          # Training loop and utilities
├── train.py            # Main training script
└── evaluate.py         # Evaluation and metrics

train_model.py          # Simplified training interface
```

## Next Steps

After training, you can:
1. **Step 3**: Upload model to S3/Minio
2. **Step 4**: Track experiments with MLflow
3. **Step 5**: Deploy model as API
4. **Step 6**: Create WebApp interface

## Quick Reference

```bash
# Quick start
python train_model.py --fast

# Standard training
python train_model.py

# Evaluation
python src/models/evaluate.py \
    --checkpoint models/checkpoints/best_model.pth \
    --backbone resnet18 \
    --split test

# Check model info
cat models/checkpoints/model_info.json
```

---

**Model training complete!** 🎉 Proceed to Step 3 when ready.
