"""
Start the FastAPI server for plant classification.
"""

import uvicorn
from loguru import logger

if __name__ == "__main__":
    logger.info("="*70)
    logger.info("PLANT CLASSIFICATION API")
    logger.info("="*70)
    logger.info("Starting server...")
    logger.info("API URL: http://localhost:8000")
    logger.info("Documentation: http://localhost:8000/docs")
    logger.info("Health Check: http://localhost:8000/health")
    logger.info("="*70)
    
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
