"""Utility script to create MinIO buckets required by the project."""
from __future__ import annotations

import argparse
import logging

from models.utils import ensure_bucket, get_minio_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
LOGGER = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bootstrap MinIO buckets")
    parser.add_argument("--data-bucket", default="dandelion-data")
    parser.add_argument("--model-bucket", default="dandelion-models")
    parser.add_argument("--mlflow-bucket", default="mlflow-artifacts")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    client = get_minio_client()
    for bucket in {args.data_bucket, args.model_bucket, args.mlflow_bucket}:
        ensure_bucket(client, bucket)
        LOGGER.info("Ensured bucket %s exists", bucket)


if __name__ == "__main__":
    main()
