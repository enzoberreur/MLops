"""
Data extraction module for downloading plant images from GitHub.
"""

import requests
from pathlib import Path
from typing import List, Tuple
import time
from loguru import logger
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.config.config import (
    GITHUB_BASE_URL,
    RAW_DATA_DIR,
    NUM_DANDELION_IMAGES,
    NUM_GRASS_IMAGES,
    LABELS,
    DATABASE_PATH
)
from src.data.database import PlantsDatabase

# Configure loguru
logger.remove()
logger.add(sys.stderr, level="INFO")
logger.add("logs/data_extraction.log", rotation="10 MB", level="DEBUG")


def generate_image_urls(label: str, num_images: int) -> List[Tuple[str, str]]:
    """
    Generate URLs for images to download.
    
    Args:
        label: Image label (dandelion or grass)
        num_images: Number of images to generate URLs for
    
    Returns:
        List of tuples (url, filename)
    """
    urls = []
    for i in range(num_images):
        filename = f"{i:08d}.jpg"
        url = f"{GITHUB_BASE_URL}/{label}/{filename}"
        urls.append((url, filename))
    
    return urls


def download_image(url: str, save_path: Path, timeout: int = 10) -> bool:
    """
    Download an image from a URL.
    
    Args:
        url: Image URL
        save_path: Path to save the image
        timeout: Request timeout in seconds
    
    Returns:
        True if download successful, False otherwise
    """
    try:
        response = requests.get(url, timeout=timeout, stream=True)
        response.raise_for_status()
        
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return True
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to download {url}: {e}")
        return False


def extract_images(label: str, num_images: int, db: PlantsDatabase) -> Tuple[int, int]:
    """
    Extract images for a specific label.
    
    Args:
        label: Image label (dandelion or grass)
        num_images: Number of images to download
        db: Database instance
    
    Returns:
        Tuple of (successful_downloads, failed_downloads)
    """
    logger.info(f"Starting extraction for label: {label}")
    
    # Create directory for label
    label_dir = RAW_DATA_DIR / label
    label_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate URLs
    urls = generate_image_urls(label, num_images)
    
    successful = 0
    failed = 0
    
    for url, filename in urls:
        save_path = label_dir / filename
        
        # Skip if already exists
        if save_path.exists():
            logger.debug(f"Image already exists: {filename}")
            # Check if in database
            image_id = db.insert_image(url, label)
            db.update_download_status(image_id, True)
            successful += 1
            continue
        
        # Insert into database
        image_id = db.insert_image(url, label)
        
        # Download image
        logger.debug(f"Downloading {filename} from {url}")
        if download_image(url, save_path):
            db.update_download_status(image_id, True)
            successful += 1
            logger.debug(f"Successfully downloaded: {filename}")
        else:
            db.update_download_status(image_id, False)
            failed += 1
            logger.warning(f"Failed to download: {filename}")
        
        # Small delay to avoid overwhelming the server
        time.sleep(0.1)
    
    logger.info(f"Completed extraction for {label}: {successful} successful, {failed} failed")
    return successful, failed


def main():
    """Main function to extract all images."""
    logger.info("="*80)
    logger.info("Starting data extraction process")
    logger.info("="*80)
    
    # Initialize database
    db = PlantsDatabase(DATABASE_PATH)
    
    # Get initial statistics
    initial_stats = db.get_statistics()
    logger.info(f"Initial database statistics: {initial_stats}")
    
    total_successful = 0
    total_failed = 0
    
    # Extract dandelion images
    logger.info(f"\n{'='*80}")
    logger.info(f"Extracting DANDELION images")
    logger.info(f"{'='*80}")
    successful, failed = extract_images("dandelion", NUM_DANDELION_IMAGES, db)
    total_successful += successful
    total_failed += failed
    
    # Extract grass images
    logger.info(f"\n{'='*80}")
    logger.info(f"Extracting GRASS images")
    logger.info(f"{'='*80}")
    successful, failed = extract_images("grass", NUM_GRASS_IMAGES, db)
    total_successful += successful
    total_failed += failed
    
    # Final statistics
    final_stats = db.get_statistics()
    
    logger.info(f"\n{'='*80}")
    logger.info("Data extraction completed!")
    logger.info(f"{'='*80}")
    logger.info(f"Total successful downloads: {total_successful}")
    logger.info(f"Total failed downloads: {total_failed}")
    logger.info(f"\nFinal database statistics:")
    logger.info(f"  Total images: {final_stats['total']}")
    logger.info(f"  Downloaded: {final_stats['downloaded']}")
    logger.info(f"  By label: {final_stats['by_label']}")
    logger.info(f"\nRaw data saved to: {RAW_DATA_DIR}")
    logger.info(f"Database saved to: {DATABASE_PATH}")


if __name__ == "__main__":
    # Create logs directory
    Path("logs").mkdir(exist_ok=True)
    main()
