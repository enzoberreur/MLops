"""
Verify MLflow setup and test tracking.
"""

import sys
from pathlib import Path
import time
import requests
from loguru import logger

sys.path.append(str(Path(__file__).parent))

from src.tracking.mlflow_tracker import MLflowTracker


def wait_for_mlflow(url: str = "http://localhost:5001", timeout: int = 120):
    """Wait for MLflow server to be ready."""
    logger.info(f"Waiting for MLflow server at {url}...")
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{url}/health", timeout=5)
            if response.status_code == 200:
                logger.success(f"MLflow server is ready!")
                return True
        except Exception:
            pass
        
        time.sleep(5)
        elapsed = int(time.time() - start_time)
        logger.info(f"Still waiting... ({elapsed}s / {timeout}s)")
    
    logger.error(f"MLflow server did not respond within {timeout} seconds")
    return False


def verify_mlflow():
    """Verify MLflow setup and run a test."""
    
    logger.info("="*70)
    logger.info("MLFLOW VERIFICATION")
    logger.info("="*70)
    
    # Wait for MLflow
    if not wait_for_mlflow():
        logger.error("MLflow server is not accessible")
        return False
    
    # Initialize tracker
    logger.info("\n1. Initializing MLflow tracker...")
    try:
        tracker = MLflowTracker(
            tracking_uri="http://localhost:5001",
            experiment_name="verification_test",
            s3_endpoint="http://localhost:9000",
            aws_access_key="minioadmin",
            aws_secret_key="minioadmin"
        )
        logger.success("✓ MLflow tracker initialized")
    except Exception as e:
        logger.error(f"✗ Failed to initialize tracker: {e}")
        return False
    
    # Start a test run
    logger.info("\n2. Starting test run...")
    try:
        tracker.start_run(
            run_name="verification_run",
            tags={"test": "true", "purpose": "verification"}
        )
        logger.success("✓ Test run started")
    except Exception as e:
        logger.error(f"✗ Failed to start run: {e}")
        return False
    
    # Log parameters
    logger.info("\n3. Logging parameters...")
    try:
        tracker.log_params({
            "test_param_1": "value1",
            "test_param_2": 42,
            "test_param_3": 3.14
        })
        logger.success("✓ Parameters logged")
    except Exception as e:
        logger.error(f"✗ Failed to log parameters: {e}")
        return False
    
    # Log metrics
    logger.info("\n4. Logging metrics...")
    try:
        for step in range(5):
            tracker.log_metrics({
                "accuracy": 0.80 + step * 0.04,
                "loss": 1.0 - step * 0.15
            }, step=step)
        logger.success("✓ Metrics logged (5 steps)")
    except Exception as e:
        logger.error(f"✗ Failed to log metrics: {e}")
        return False
    
    # Log artifacts
    logger.info("\n5. Logging test artifact...")
    try:
        test_file = Path("/tmp/test_artifact.txt")
        test_file.write_text("This is a test artifact from MLflow verification")
        tracker.log_artifact(test_file)
        test_file.unlink()
        logger.success("✓ Artifact logged")
    except Exception as e:
        logger.error(f"✗ Failed to log artifact: {e}")
        return False
    
    # Set tags
    logger.info("\n6. Setting tags...")
    try:
        tracker.set_tags({
            "status": "completed",
            "version": "1.0"
        })
        logger.success("✓ Tags set")
    except Exception as e:
        logger.error(f"✗ Failed to set tags: {e}")
        return False
    
    # Get run info
    logger.info("\n7. Getting run info...")
    try:
        run_info = tracker.get_run_info()
        if run_info:
            logger.success("✓ Run info retrieved:")
            logger.info(f"   Run ID: {run_info['run_id']}")
            logger.info(f"   Run Name: {run_info['run_name']}")
            logger.info(f"   Experiment ID: {run_info['experiment_id']}")
            logger.info(f"   Artifact URI: {run_info['artifact_uri']}")
        else:
            logger.warning("⚠ No run info available")
    except Exception as e:
        logger.error(f"✗ Failed to get run info: {e}")
    
    # End run
    logger.info("\n8. Ending run...")
    try:
        tracker.end_run(status="FINISHED")
        logger.success("✓ Run ended")
    except Exception as e:
        logger.error(f"✗ Failed to end run: {e}")
        return False
    
    # Final summary
    logger.info("\n" + "="*70)
    logger.success("✓ ALL MLFLOW TESTS PASSED")
    logger.info("="*70)
    logger.info("\nMLflow UI Access:")
    logger.info("  URL: http://localhost:5001")
    logger.info("  Experiment: verification_test")
    logger.info("\nMinio Console:")
    logger.info("  URL: http://localhost:9001")
    logger.info("  Bucket: mlflow")
    logger.info("  Username: minioadmin")
    logger.info("  Password: minioadmin")
    logger.info("\n" + "="*70)
    
    return True


if __name__ == "__main__":
    success = verify_mlflow()
    sys.exit(0 if success else 1)
