"""
Configuration module for the MLOps project.
Loads environment variables and provides configuration settings.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"

# Database Configuration
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "database": os.getenv("DB_NAME", "mlops_plants"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "postgres"),
}

DATABASE_PATH = os.getenv("DATABASE_PATH", str(DATA_DIR / "plants.db"))

# GitHub Data Source
GITHUB_BASE_URL = os.getenv(
    "GITHUB_BASE_URL",
    "https://raw.githubusercontent.com/btphan95/greenr-airflow/refs/heads/master/data"
)

# Image Configuration
IMAGE_SIZE = int(os.getenv("IMAGE_SIZE", 224))
NUM_DANDELION_IMAGES = int(os.getenv("NUM_DANDELION_IMAGES", 200))
NUM_GRASS_IMAGES = int(os.getenv("NUM_GRASS_IMAGES", 200))

# S3/Minio Configuration
S3_CONFIG = {
    "endpoint_url": os.getenv("S3_ENDPOINT", "http://localhost:9000"),
    "aws_access_key_id": os.getenv("S3_ACCESS_KEY", "minioadmin"),
    "aws_secret_access_key": os.getenv("S3_SECRET_KEY", "minioadmin"),
    "region_name": os.getenv("S3_REGION", "us-east-1"),
}
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "plants-images")

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Labels
LABELS = ["dandelion", "grass"]

# Create directories if they don't exist
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
(RAW_DATA_DIR / "dandelion").mkdir(exist_ok=True)
(RAW_DATA_DIR / "grass").mkdir(exist_ok=True)
(PROCESSED_DATA_DIR / "dandelion").mkdir(exist_ok=True)
(PROCESSED_DATA_DIR / "grass").mkdir(exist_ok=True)
