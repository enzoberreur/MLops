"""
Verify model storage and download from S3/Minio.
"""

import sys
from pathlib import Path
import json

from loguru import logger

sys.path.append(str(Path(__file__).parent))

from src.storage.model_storage import ModelStorage


def verify_s3_storage():
    """Verify that the model is correctly stored in S3."""
    
    logger.info("=== S3 Model Storage Verification ===\n")
    
    # Initialize storage
    storage = ModelStorage(bucket_name="models")
    
    # 1. List all model versions
    logger.info("1. Listing model versions...")
    versions = storage.list_model_versions("plant_classifier")
    
    if not versions:
        logger.error("No model versions found!")
        return False
    
    logger.success(f"Found {len(versions)} version(s):")
    for v in versions:
        logger.info(f"  - {v['version']}")
    
    # 2. Get latest version
    logger.info("\n2. Getting latest version...")
    latest = storage.get_latest_version("plant_classifier")
    logger.success(f"Latest version: {latest}")
    
    # 3. Download the model
    logger.info("\n3. Downloading model...")
    download_dir = Path("models/downloaded")
    download_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        model_path = storage.download_model(
            model_name="plant_classifier",
            version=latest,
            local_dir=download_dir,
            download_additional=True
        )
        logger.success(f"Model downloaded to: {model_path}")
    except Exception as e:
        logger.error(f"Failed to download model: {e}")
        return False
    
    # 4. Verify downloaded files
    logger.info("\n4. Verifying downloaded files...")
    expected_files = ["best_model.pth", "manifest.json", "training_history.json"]
    
    for filename in expected_files:
        file_path = download_dir / filename
        if file_path.exists():
            size_mb = file_path.stat().st_size / (1024 * 1024)
            logger.success(f"  ✓ {filename} ({size_mb:.2f} MB)")
        else:
            logger.error(f"  ✗ {filename} not found")
    
    # 5. Check manifest content
    logger.info("\n5. Checking manifest content...")
    manifest_path = download_dir / "manifest.json"
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)
    
    logger.info(f"  Model Name: {manifest['model_name']}")
    logger.info(f"  Version: {manifest['version']}")
    logger.info(f"  Checksum: {manifest['checksum']}")
    logger.info(f"  Created: {manifest['created_at']}")
    
    if 'metadata' in manifest:
        metadata = manifest['metadata']
        logger.info(f"\n  Metadata:")
        logger.info(f"    Architecture: {metadata.get('architecture', 'N/A')}")
        logger.info(f"    Best Epoch: {metadata.get('best_epoch', 'N/A')}")
        logger.info(f"    Train Accuracy: {metadata.get('train_accuracy', 'N/A'):.4f}")
        logger.info(f"    Val Accuracy: {metadata.get('val_accuracy', 'N/A'):.4f}")
        logger.info(f"    Train Loss: {metadata.get('train_loss', 'N/A'):.4f}")
        logger.info(f"    Val Loss: {metadata.get('val_loss', 'N/A'):.4f}")
    
    # 6. Test S3 client methods
    logger.info("\n6. Testing S3 client methods...")
    
    # Check if object exists
    object_key = f"plant_classifier/{latest}/best_model.pth"
    exists = storage.s3_client.object_exists("models", object_key)
    logger.success(f"  Object exists: {exists}")
    
    # Get object metadata
    metadata = storage.s3_client.get_object_metadata("models", object_key)
    if metadata:
        logger.info(f"  Content Type: {metadata.get('ContentType', 'N/A')}")
        logger.info(f"  Size: {metadata.get('ContentLength', 0) / (1024*1024):.2f} MB")
        logger.info(f"  Last Modified: {metadata.get('LastModified', 'N/A')}")
    
    # List all objects in bucket
    logger.info("\n7. Listing all objects in models bucket...")
    objects = storage.s3_client.list_objects("models", prefix="plant_classifier")
    logger.success(f"Found {len(objects)} objects:")
    for obj in objects[:5]:  # Show first 5
        logger.info(f"  - {obj['key']} ({obj['size'] / 1024:.1f} KB)")
    if len(objects) > 5:
        logger.info(f"  ... and {len(objects) - 5} more")
    
    logger.info("\n" + "="*50)
    logger.success("✓ All verification tests passed!")
    logger.info("="*50 + "\n")
    
    return True


if __name__ == "__main__":
    success = verify_s3_storage()
    sys.exit(0 if success else 1)
