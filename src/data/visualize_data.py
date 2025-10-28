"""
Utility script to visualize sample images from the dataset.
"""

import sys
from pathlib import Path
import random
from PIL import Image
import matplotlib.pyplot as plt

sys.path.append(str(Path(__file__).parent.parent))

from src.config.config import RAW_DATA_DIR, PROCESSED_DATA_DIR, LABELS


def visualize_samples(data_dir: Path, num_samples: int = 5):
    """
    Visualize random samples from the dataset.
    
    Args:
        data_dir: Directory containing the images
        num_samples: Number of samples per label to display
    """
    fig, axes = plt.subplots(len(LABELS), num_samples, figsize=(15, 6))
    fig.suptitle(f'Sample Images from {data_dir.name.upper()} Dataset', fontsize=16)
    
    for i, label in enumerate(LABELS):
        label_dir = data_dir / label
        if not label_dir.exists():
            print(f"Directory not found: {label_dir}")
            continue
        
        image_files = list(label_dir.glob("*.jpg"))
        if not image_files:
            print(f"No images found in: {label_dir}")
            continue
        
        # Select random samples
        samples = random.sample(image_files, min(num_samples, len(image_files)))
        
        for j, img_path in enumerate(samples):
            img = Image.open(img_path)
            
            if len(LABELS) == 1:
                ax = axes[j]
            else:
                ax = axes[i, j]
            
            ax.imshow(img)
            ax.axis('off')
            if j == 0:
                ax.set_title(f'{label.capitalize()}', fontsize=12, fontweight='bold')
    
    plt.tight_layout()
    plt.show()


def get_dataset_info(data_dir: Path):
    """
    Get information about the dataset.
    
    Args:
        data_dir: Directory containing the images
    """
    print(f"\n{'='*60}")
    print(f"Dataset Information: {data_dir.name.upper()}")
    print(f"{'='*60}")
    print(f"Location: {data_dir}")
    print(f"\nImages per label:")
    
    total_images = 0
    for label in LABELS:
        label_dir = data_dir / label
        if label_dir.exists():
            num_images = len(list(label_dir.glob("*.jpg")))
            print(f"  {label.capitalize()}: {num_images}")
            total_images += num_images
        else:
            print(f"  {label.capitalize()}: 0 (directory not found)")
    
    print(f"\nTotal images: {total_images}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    # Get dataset information
    print("\nRAW DATASET:")
    get_dataset_info(RAW_DATA_DIR)
    
    print("\nPROCESSED DATASET:")
    get_dataset_info(PROCESSED_DATA_DIR)
    
    # Visualize samples
    print("\nGenerating visualizations...")
    print("Note: You need matplotlib installed to see the visualizations")
    
    try:
        if RAW_DATA_DIR.exists():
            visualize_samples(RAW_DATA_DIR, num_samples=5)
        
        if PROCESSED_DATA_DIR.exists():
            visualize_samples(PROCESSED_DATA_DIR, num_samples=5)
    except Exception as e:
        print(f"Could not generate visualizations: {e}")
        print("Make sure matplotlib is installed: pip install matplotlib")
