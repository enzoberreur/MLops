"""
Test the Plant Classification API.
"""

import sys
from pathlib import Path
import requests
import json
from loguru import logger

sys.path.append(str(Path(__file__).parent))

API_URL = "http://localhost:8000"


def test_health():
    """Test health endpoint."""
    logger.info("Testing /health endpoint...")
    response = requests.get(f"{API_URL}/health")
    
    if response.status_code == 200:
        data = response.json()
        logger.success(f"✓ Health check passed")
        logger.info(f"  Status: {data['status']}")
        logger.info(f"  Model loaded: {data['model_loaded']}")
        logger.info(f"  Model info: {data['model_info']}")
        return True
    else:
        logger.error(f"✗ Health check failed: {response.status_code}")
        return False


def test_root():
    """Test root endpoint."""
    logger.info("\nTesting / endpoint...")
    response = requests.get(f"{API_URL}/")
    
    if response.status_code == 200:
        data = response.json()
        logger.success(f"✓ Root endpoint works")
        logger.info(f"  Message: {data['message']}")
        return True
    else:
        logger.error(f"✗ Root endpoint failed: {response.status_code}")
        return False


def test_model_info():
    """Test model info endpoint."""
    logger.info("\nTesting /model/info endpoint...")
    response = requests.get(f"{API_URL}/model/info")
    
    if response.status_code == 200:
        data = response.json()
        logger.success(f"✓ Model info retrieved")
        logger.info(f"  Model source: {data['model_source']}")
        logger.info(f"  Device: {data['device']}")
        logger.info(f"  Classes: {data['class_names']}")
        logger.info(f"  Input size: {data['input_size']}")
        return True
    else:
        logger.error(f"✗ Model info failed: {response.status_code}")
        return False


def test_prediction(image_path: Path):
    """Test prediction endpoint with an image."""
    logger.info(f"\nTesting /predict endpoint with {image_path.name}...")
    
    if not image_path.exists():
        logger.warning(f"Image not found: {image_path}")
        return False
    
    with open(image_path, 'rb') as f:
        files = {'file': (image_path.name, f, 'image/jpeg')}
        response = requests.post(f"{API_URL}/predict", files=files)
    
    if response.status_code == 200:
        data = response.json()
        logger.success(f"✓ Prediction successful")
        logger.info(f"  Prediction: {data['prediction']}")
        logger.info(f"  Confidence: {data['confidence']:.4f}")
        logger.info(f"  Probabilities:")
        for class_name, prob in data['probabilities'].items():
            logger.info(f"    - {class_name}: {prob:.4f}")
        logger.info(f"  Inference time: {data['inference_time_ms']:.2f} ms")
        return True
    else:
        logger.error(f"✗ Prediction failed: {response.status_code}")
        logger.error(f"  Response: {response.text}")
        return False


def test_batch_prediction(image_paths: list[Path]):
    """Test batch prediction endpoint."""
    logger.info(f"\nTesting /predict/batch endpoint with {len(image_paths)} images...")
    
    files = []
    for image_path in image_paths:
        if image_path.exists():
            files.append(('files', (image_path.name, open(image_path, 'rb'), 'image/jpeg')))
    
    if not files:
        logger.warning("No valid images found for batch prediction")
        return False
    
    response = requests.post(f"{API_URL}/predict/batch", files=files)
    
    # Close file handles
    for _, (_, file, _) in files:
        file.close()
    
    if response.status_code == 200:
        data = response.json()
        logger.success(f"✓ Batch prediction successful")
        logger.info(f"  Results: {len(data['predictions'])} predictions")
        for pred in data['predictions']:
            if pred['success']:
                logger.info(f"    - {pred['filename']}: {pred['result']['prediction']} ({pred['result']['confidence']:.4f})")
            else:
                logger.error(f"    - {pred['filename']}: FAILED - {pred['error']}")
        return True
    else:
        logger.error(f"✗ Batch prediction failed: {response.status_code}")
        return False


def test_stats():
    """Test stats endpoint."""
    logger.info("\nTesting /stats endpoint...")
    response = requests.get(f"{API_URL}/stats")
    
    if response.status_code == 200:
        data = response.json()
        logger.success(f"✓ Stats retrieved")
        logger.info(f"  Total predictions: {data['total_predictions']}")
        logger.info(f"  Avg inference time: {data['avg_inference_time_ms']:.2f} ms")
        return True
    else:
        logger.error(f"✗ Stats failed: {response.status_code}")
        return False


def main():
    """Run all tests."""
    logger.info("="*70)
    logger.info("PLANT CLASSIFICATION API TESTS")
    logger.info("="*70)
    
    results = []
    
    # Test endpoints
    results.append(("Health Check", test_health()))
    results.append(("Root", test_root()))
    results.append(("Model Info", test_model_info()))
    
    # Test predictions with sample images
    from src.config.config import PROJECT_ROOT
    processed_dir = PROJECT_ROOT / "data" / "processed"
    
    # Find sample dandelion image
    dandelion_images = list((processed_dir / "dandelion").glob("*.jpg"))
    if dandelion_images:
        results.append(("Prediction (dandelion)", test_prediction(dandelion_images[0])))
    else:
        logger.warning("No dandelion images found for testing")
    
    # Find sample grass image
    grass_images = list((processed_dir / "grass").glob("*.jpg"))
    if grass_images:
        results.append(("Prediction (grass)", test_prediction(grass_images[0])))
    else:
        logger.warning("No grass images found for testing")
    
    # Test batch prediction
    sample_images = []
    if dandelion_images:
        sample_images.append(dandelion_images[0])
    if grass_images:
        sample_images.append(grass_images[0])
    
    if sample_images:
        results.append(("Batch Prediction", test_batch_prediction(sample_images)))
    
    # Test stats
    results.append(("Stats", test_stats()))
    
    # Summary
    logger.info("\n" + "="*70)
    logger.info("TEST SUMMARY")
    logger.info("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        logger.info(f"{test_name}: {status}")
    
    logger.info("="*70)
    logger.info(f"TOTAL: {passed}/{total} tests passed")
    logger.info("="*70)
    
    if passed == total:
        logger.success("\n🎉 All tests passed!")
        return 0
    else:
        logger.error(f"\n❌ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("\nTests interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Test suite failed: {e}")
        sys.exit(1)
