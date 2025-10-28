"""
Prepare data for training - Extract and preprocess images from database.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.append(str(PROJECT_ROOT))

from src.data.extract_data import ImageExtractor
from src.data.preprocess_data import ImagePreprocessor
from src.config.config import DATA_DIR, PROCESSED_DATA_DIR
from loguru import logger


def main():
    """Extract and preprocess images from database."""
    logger.info("="*70)
    logger.info("DATA PREPARATION PIPELINE")
    logger.info("="*70)
    
    # Step 1: Extract images from database
    logger.info("\n📥 Step 1/2: Extracting images from database...")
    extractor = ImageExtractor()
    
    try:
        results = extractor.extract_all_images()
        logger.success(f"✓ Extracted {results['total']} images")
        logger.info(f"  - Dandelion: {results['dandelion']} images")
        logger.info(f"  - Grass: {results['grass']} images")
    except Exception as e:
        logger.error(f"✗ Extraction failed: {e}")
        return 1
    
    # Step 2: Preprocess images
    logger.info("\n🔄 Step 2/2: Preprocessing images...")
    preprocessor = ImagePreprocessor()
    
    try:
        processed = preprocessor.preprocess_all()
        logger.success(f"✓ Preprocessed {processed['total']} images")
        logger.info(f"  - Success: {processed['success']}")
        logger.info(f"  - Failed: {processed['failed']}")
    except Exception as e:
        logger.error(f"✗ Preprocessing failed: {e}")
        return 1
    
    # Summary
    logger.info("\n" + "="*70)
    logger.success("✅ DATA PREPARATION COMPLETE")
    logger.info("="*70)
    logger.info(f"\n📁 Processed data location: {PROCESSED_DATA_DIR}")
    logger.info(f"   - Dandelion images: {PROCESSED_DATA_DIR}/dandelion/")
    logger.info(f"   - Grass images: {PROCESSED_DATA_DIR}/grass/")
    logger.info("\n📊 Next steps:")
    logger.info("   1. Train model: python3 train_model.py --fast")
    logger.info("   2. Or with MLflow: python3 train_with_mlflow.py")
    logger.info("   3. View experiments: http://localhost:5001\n")
    
    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("\n\n❌ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
