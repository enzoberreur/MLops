"""
Data preprocessing module for cleaning and preparing plant images.
"""

import sys
from pathlib import Path
from typing import Tuple, Optional
import numpy as np
from PIL import Image
import cv2
from loguru import logger

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.config.config import (
    RAW_DATA_DIR,
    PROCESSED_DATA_DIR,
    IMAGE_SIZE,
    LABELS,
    DATABASE_PATH
)
from src.data.database import PlantsDatabase

# Configure loguru
logger.remove()
logger.add(sys.stderr, level="INFO")
logger.add("logs/data_preprocessing.log", rotation="10 MB", level="DEBUG")


class ImagePreprocessor:
    """Image preprocessing and validation utilities."""
    
    def __init__(self, target_size: int = IMAGE_SIZE):
        """
        Initialize preprocessor.
        
        Args:
            target_size: Target size for square images
        """
        self.target_size = target_size
        self.min_size = 50  # Minimum acceptable image size
        self.max_size = 5000  # Maximum acceptable image size
    
    def validate_image(self, image_path: Path) -> Tuple[bool, str]:
        """
        Validate if an image is usable.
        
        Args:
            image_path: Path to image file
        
        Returns:
            Tuple of (is_valid, reason)
        """
        try:
            # Check file exists and has size
            if not image_path.exists():
                return False, "File does not exist"
            
            if image_path.stat().st_size == 0:
                return False, "File is empty"
            
            # Try to open with PIL
            with Image.open(image_path) as img:
                # Check format
                if img.format not in ['JPEG', 'JPG', 'PNG']:
                    return False, f"Unsupported format: {img.format}"
                
                # Check dimensions
                width, height = img.size
                if width < self.min_size or height < self.min_size:
                    return False, f"Image too small: {width}x{height}"
                
                if width > self.max_size or height > self.max_size:
                    return False, f"Image too large: {width}x{height}"
                
                # Check if image can be converted to RGB
                img.convert('RGB')
            
            return True, "Valid"
        
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def preprocess_image(self, image_path: Path, output_path: Path) -> bool:
        """
        Preprocess an image: resize, normalize, and save.
        
        Args:
            image_path: Path to input image
            output_path: Path to save processed image
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Read image with PIL
            with Image.open(image_path) as img:
                # Convert to RGB (handles grayscale and RGBA)
                img_rgb = img.convert('RGB')
                
                # Resize with high-quality resampling
                # Using LANCZOS for downsampling (best quality)
                img_resized = img_rgb.resize(
                    (self.target_size, self.target_size),
                    Image.Resampling.LANCZOS
                )
                
                # Save processed image
                output_path.parent.mkdir(parents=True, exist_ok=True)
                img_resized.save(output_path, 'JPEG', quality=95)
            
            return True
        
        except Exception as e:
            logger.error(f"Error preprocessing {image_path}: {e}")
            return False
    
    def get_image_statistics(self, image_path: Path) -> Optional[dict]:
        """
        Get statistics about an image.
        
        Args:
            image_path: Path to image
        
        Returns:
            Dictionary with image statistics or None if error
        """
        try:
            with Image.open(image_path) as img:
                img_array = np.array(img.convert('RGB'))
                
                return {
                    "width": img.size[0],
                    "height": img.size[1],
                    "format": img.format,
                    "mode": img.mode,
                    "mean": img_array.mean(),
                    "std": img_array.std(),
                    "file_size": image_path.stat().st_size
                }
        
        except Exception as e:
            logger.error(f"Error getting statistics for {image_path}: {e}")
            return None


def process_images_for_label(label: str, preprocessor: ImagePreprocessor, db: PlantsDatabase) -> Tuple[int, int]:
    """
    Process all images for a specific label.
    
    Args:
        label: Image label (dandelion or grass)
        preprocessor: ImagePreprocessor instance
        db: Database instance
    
    Returns:
        Tuple of (successful_count, failed_count)
    """
    logger.info(f"Processing images for label: {label}")
    
    raw_dir = RAW_DATA_DIR / label
    processed_dir = PROCESSED_DATA_DIR / label
    processed_dir.mkdir(parents=True, exist_ok=True)
    
    # Get all images for this label
    if not raw_dir.exists():
        logger.warning(f"Raw directory does not exist: {raw_dir}")
        return 0, 0
    
    image_files = list(raw_dir.glob("*.jpg"))
    logger.info(f"Found {len(image_files)} images to process")
    
    successful = 0
    failed = 0
    
    for image_path in image_files:
        # Validate image
        is_valid, reason = preprocessor.validate_image(image_path)
        
        if not is_valid:
            logger.warning(f"Invalid image {image_path.name}: {reason}")
            failed += 1
            continue
        
        # Process image
        output_path = processed_dir / image_path.name
        
        if preprocessor.preprocess_image(image_path, output_path):
            successful += 1
            logger.debug(f"Successfully processed: {image_path.name}")
            
            # Get statistics
            stats = preprocessor.get_image_statistics(output_path)
            if stats:
                logger.debug(f"  Size: {stats['width']}x{stats['height']}, "
                           f"Mean: {stats['mean']:.2f}, Std: {stats['std']:.2f}")
        else:
            failed += 1
            logger.warning(f"Failed to process: {image_path.name}")
    
    logger.info(f"Completed processing for {label}: {successful} successful, {failed} failed")
    return successful, failed


def main():
    """Main function to preprocess all images."""
    logger.info("="*80)
    logger.info("Starting data preprocessing process")
    logger.info("="*80)
    
    # Initialize database
    db = PlantsDatabase(DATABASE_PATH)
    
    # Initialize preprocessor
    preprocessor = ImagePreprocessor(target_size=IMAGE_SIZE)
    logger.info(f"Target image size: {IMAGE_SIZE}x{IMAGE_SIZE}")
    
    total_successful = 0
    total_failed = 0
    
    # Process each label
    for label in LABELS:
        logger.info(f"\n{'='*80}")
        logger.info(f"Processing {label.upper()} images")
        logger.info(f"{'='*80}")
        
        successful, failed = process_images_for_label(label, preprocessor, db)
        total_successful += successful
        total_failed += failed
    
    # Final summary
    logger.info(f"\n{'='*80}")
    logger.info("Data preprocessing completed!")
    logger.info(f"{'='*80}")
    logger.info(f"Total successful: {total_successful}")
    logger.info(f"Total failed: {total_failed}")
    logger.info(f"Success rate: {total_successful/(total_successful+total_failed)*100:.2f}%")
    logger.info(f"\nProcessed data saved to: {PROCESSED_DATA_DIR}")
    
    # Get dataset statistics
    logger.info(f"\n{'='*80}")
    logger.info("Dataset Statistics")
    logger.info(f"{'='*80}")
    
    for label in LABELS:
        processed_dir = PROCESSED_DATA_DIR / label
        num_images = len(list(processed_dir.glob("*.jpg")))
        logger.info(f"{label.capitalize()}: {num_images} images")


if __name__ == "__main__":
    # Create logs directory
    Path("logs").mkdir(exist_ok=True)
    main()
