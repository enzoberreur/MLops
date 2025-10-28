"""
Test the Streamlit WebApp by simulating API calls.
This validates that the WebApp would work correctly with the API.
"""

import requests
import sys
from pathlib import Path
from loguru import logger

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.append(str(PROJECT_ROOT))

API_URL = "http://localhost:8000"
WEBAPP_URL = "http://localhost:8501"


def test_api_connectivity():
    """Test if API is accessible."""
    logger.info("Testing API connectivity...")
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "healthy" and data.get("model_loaded"):
                logger.success("✓ API is healthy and model is loaded")
                return True
            else:
                logger.error("✗ API is not healthy or model not loaded")
                return False
        else:
            logger.error(f"✗ API returned status code: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"✗ Cannot connect to API: {e}")
        return False


def test_webapp_accessibility():
    """Test if WebApp is accessible."""
    logger.info("Testing WebApp accessibility...")
    try:
        response = requests.get(WEBAPP_URL, timeout=5)
        if response.status_code == 200:
            logger.success("✓ WebApp is accessible")
            return True
        else:
            logger.error(f"✗ WebApp returned status code: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"✗ Cannot connect to WebApp: {e}")
        logger.warning("  Make sure WebApp is running: python3 run_webapp.py")
        return False


def test_api_endpoints():
    """Test all API endpoints that WebApp uses."""
    logger.info("\nTesting API endpoints used by WebApp...")
    
    endpoints = {
        "/health": "GET",
        "/stats": "GET",
        "/model/info": "GET"
    }
    
    results = []
    
    for endpoint, method in endpoints.items():
        try:
            response = requests.request(method, f"{API_URL}{endpoint}", timeout=5)
            if response.status_code == 200:
                logger.success(f"✓ {method} {endpoint} - OK")
                results.append(True)
            else:
                logger.error(f"✗ {method} {endpoint} - Failed ({response.status_code})")
                results.append(False)
        except Exception as e:
            logger.error(f"✗ {method} {endpoint} - Error: {e}")
            results.append(False)
    
    return all(results)


def test_prediction_endpoint():
    """Test prediction endpoint with a sample image."""
    logger.info("\nTesting prediction endpoint...")
    
    from src.config.config import PROJECT_ROOT
    processed_dir = PROJECT_ROOT / "data" / "processed"
    
    # Find a sample image
    dandelion_images = list((processed_dir / "dandelion").glob("*.jpg"))
    
    if not dandelion_images:
        logger.warning("⚠ No sample images found, skipping prediction test")
        return True
    
    sample_image = dandelion_images[0]
    
    try:
        with open(sample_image, 'rb') as f:
            files = {'file': (sample_image.name, f, 'image/jpeg')}
            response = requests.post(f"{API_URL}/predict", files=files, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            logger.success(f"✓ Prediction successful: {data['prediction']} ({data['confidence']:.2%})")
            return True
        else:
            logger.error(f"✗ Prediction failed: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"✗ Prediction error: {e}")
        return False


def test_batch_prediction():
    """Test batch prediction endpoint."""
    logger.info("\nTesting batch prediction endpoint...")
    
    from src.config.config import PROJECT_ROOT
    processed_dir = PROJECT_ROOT / "data" / "processed"
    
    # Find sample images
    dandelion_images = list((processed_dir / "dandelion").glob("*.jpg"))[:2]
    grass_images = list((processed_dir / "grass").glob("*.jpg"))[:2]
    
    sample_images = dandelion_images + grass_images
    
    if len(sample_images) < 2:
        logger.warning("⚠ Not enough sample images, skipping batch test")
        return True
    
    try:
        files = []
        for img in sample_images:
            files.append(('files', (img.name, open(img, 'rb'), 'image/jpeg')))
        
        response = requests.post(f"{API_URL}/predict/batch", files=files, timeout=60)
        
        # Close files
        for _, (_, f, _) in files:
            f.close()
        
        if response.status_code == 200:
            data = response.json()
            logger.success(f"✓ Batch prediction successful: {data['successful']}/{data['total_images']} images")
            return True
        else:
            logger.error(f"✗ Batch prediction failed: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"✗ Batch prediction error: {e}")
        return False


def check_webapp_features():
    """Display checklist of WebApp features to test manually."""
    logger.info("\n" + "="*70)
    logger.info("MANUAL TESTING CHECKLIST")
    logger.info("="*70)
    logger.info("\n📋 Please verify these features manually in the WebApp:")
    logger.info("\n🔧 System Status (Sidebar)")
    logger.info("  [ ] API status indicator (green ✅)")
    logger.info("  [ ] Model information displayed")
    logger.info("  [ ] Statistics showing correct values")
    logger.info("  [ ] Reload model button works")
    logger.info("\n📷 Single Image Tab")
    logger.info("  [ ] File uploader widget present")
    logger.info("  [ ] Can upload JPEG/PNG images")
    logger.info("  [ ] Image displays correctly")
    logger.info("  [ ] Classify button appears")
    logger.info("  [ ] Prediction results show:")
    logger.info("      - Prediction class")
    logger.info("      - Confidence score")
    logger.info("      - Probability bars")
    logger.info("      - Inference time")
    logger.info("\n📚 Batch Upload Tab")
    logger.info("  [ ] Multiple file uploader works")
    logger.info("  [ ] Thumbnails display correctly")
    logger.info("  [ ] Max 10 images limit enforced")
    logger.info("  [ ] Batch classify button works")
    logger.info("  [ ] Results show for all images")
    logger.info("  [ ] Individual expandable results")
    logger.info("\nℹ️ About Tab")
    logger.info("  [ ] Documentation displayed")
    logger.info("  [ ] All sections present")
    logger.info("  [ ] Links are correct")
    logger.info("\n🎨 Design & UX")
    logger.info("  [ ] Colors match class (yellow/green)")
    logger.info("  [ ] Confidence indicators (🟢🟡🔴)")
    logger.info("  [ ] Layout is responsive")
    logger.info("  [ ] No visual glitches")
    logger.info("\n❌ Error Handling")
    logger.info("  [ ] Shows error when API down")
    logger.info("  [ ] Invalid files rejected")
    logger.info("  [ ] Network errors handled gracefully")
    logger.info("\n" + "="*70)


def main():
    """Run all tests."""
    logger.info("="*70)
    logger.info("WEBAPP INTEGRATION TESTS")
    logger.info("="*70)
    
    results = []
    
    # Test API first
    results.append(("API Connectivity", test_api_connectivity()))
    
    # Only continue if API is available
    if not results[-1][1]:
        logger.error("\n❌ API is not available. Start it with: python3 run_api.py")
        return 1
    
    # Test WebApp
    results.append(("WebApp Accessibility", test_webapp_accessibility()))
    
    # Test API endpoints
    results.append(("API Endpoints", test_api_endpoints()))
    results.append(("Single Prediction", test_prediction_endpoint()))
    results.append(("Batch Prediction", test_batch_prediction()))
    
    # Summary
    logger.info("\n" + "="*70)
    logger.info("AUTOMATED TEST SUMMARY")
    logger.info("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        logger.info(f"{test_name}: {status}")
    
    logger.info("="*70)
    logger.info(f"TOTAL: {passed}/{total} tests passed")
    logger.info("="*70)
    
    # Show manual checklist
    check_webapp_features()
    
    if passed == total:
        logger.success("\n✅ All automated tests passed!")
        logger.info("\n🌐 Access the WebApp at: http://localhost:8501")
        logger.info("📚 API Documentation at: http://localhost:8000/docs")
        return 0
    else:
        logger.error(f"\n❌ {total - passed} automated test(s) failed")
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
        import traceback
        traceback.print_exc()
        sys.exit(1)
