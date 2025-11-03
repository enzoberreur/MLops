"""Airflow DAG for data ingestion and initial model training."""
from __future__ import annotations

import concurrent.futures
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict

import requests
from airflow import DAG
from airflow.models import Variable
from airflow.operators.python import PythonOperator
from PIL import Image, ImageOps

from models.train import train as train_model
from models.utils import CLASS_NAMES, get_minio_client, upload_file_to_minio

LOG = logging.getLogger(__name__)

DATA_BASE_PATH = Path(Variable.get("data_base_path", "/opt/airflow/data"))
RAW_DATA_DIR = DATA_BASE_PATH / "raw"
PROCESSED_DATA_DIR = DATA_BASE_PATH / "processed"
MINIO_DATA_BUCKET = Variable.get("minio_data_bucket", "dandelion-data")
MINIO_MODEL_BUCKET = Variable.get("minio_model_bucket", "dandelion-models")
IMAGE_COUNT = int(Variable.get("image_count_per_class", 200))
IMAGE_SIZE = int(Variable.get("image_size", 128))
DOWNLOAD_BASE_URLS: Dict[str, str] = {
    "dandelion": "https://raw.githubusercontent.com/btphan95/greenr-airflow/refs/heads/master/data/dandelion",
    "grass": "https://raw.githubusercontent.com/btphan95/greenr-airflow/refs/heads/master/data/grass",
}


def _format_index(idx: int) -> str:
    return f"{idx:08d}.jpg"


def create_local_folders() -> None:
    for path in (RAW_DATA_DIR, PROCESSED_DATA_DIR):
        path.mkdir(parents=True, exist_ok=True)
    LOG.info("Ensured local data folders exist under %s", DATA_BASE_PATH)


def download_images() -> None:
    create_local_folders()

    def _download_single(class_name: str, idx: int) -> Path:
        filename = _format_index(idx)
        url = f"{DOWNLOAD_BASE_URLS[class_name]}/{filename}"
        target_dir = RAW_DATA_DIR / class_name
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / filename
        if target_path.exists():
            return target_path
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        target_path.write_bytes(response.content)
        return target_path

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = []
        for class_name in CLASS_NAMES:
            for idx in range(IMAGE_COUNT):
                futures.append(executor.submit(_download_single, class_name, idx))
        for future in concurrent.futures.as_completed(futures):
            try:
                downloaded = future.result()
                LOG.debug("Downloaded %s", downloaded)
            except Exception as exc:  # pragma: no cover - logging convenience inside DAG
                LOG.error("Download failed: %s", exc)
                raise

    LOG.info("Downloaded %d images per class", IMAGE_COUNT)


def upload_raw_to_minio() -> None:
    client = get_minio_client()
    for image_path in RAW_DATA_DIR.rglob("*.jpg"):
        object_name = f"raw/{image_path.relative_to(RAW_DATA_DIR)}"
        upload_file_to_minio(client, MINIO_DATA_BUCKET, str(object_name), image_path, content_type="image/jpeg")


def preprocess_images() -> None:
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    for image_path in RAW_DATA_DIR.rglob("*.jpg"):
        relative = image_path.relative_to(RAW_DATA_DIR)
        target_path = PROCESSED_DATA_DIR / relative
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(image_path) as img:
            img = img.convert("RGB")
            processed = ImageOps.fit(img, (IMAGE_SIZE, IMAGE_SIZE), method=Image.Resampling.BILINEAR)
            processed.save(target_path, format="JPEG")


def upload_processed_to_minio() -> None:
    client = get_minio_client()
    for image_path in PROCESSED_DATA_DIR.rglob("*.jpg"):
        object_name = f"processed/{image_path.relative_to(PROCESSED_DATA_DIR)}"
        upload_file_to_minio(client, MINIO_DATA_BUCKET, str(object_name), image_path, content_type="image/jpeg")


def run_training() -> None:
    train_model(["--data-dir", str(PROCESSED_DATA_DIR)])


def build_dag() -> DAG:
    default_args = {
        "owner": "mlops",
        "depends_on_past": False,
        "retries": 1,
        "retry_delay": timedelta(minutes=5),
    }

    with DAG(
        dag_id="dandelion_data_pipeline",
        default_args=default_args,
        schedule="@weekly",
        start_date=datetime(2024, 1, 1),
        catchup=False,
        tags=["dandelion", "mlops"],
    ) as dag:
        create_folders = PythonOperator(task_id="create_folders", python_callable=create_local_folders)
        download = PythonOperator(task_id="download_images", python_callable=download_images)
        upload_raw = PythonOperator(task_id="upload_raw", python_callable=upload_raw_to_minio)
        preprocess = PythonOperator(task_id="preprocess", python_callable=preprocess_images)
        upload_processed = PythonOperator(task_id="upload_processed", python_callable=upload_processed_to_minio)
        train = PythonOperator(task_id="train_model", python_callable=run_training)

        create_folders >> download >> upload_raw >> preprocess >> upload_processed >> train

    return dag


globals()["dandelion_data_pipeline"] = build_dag()
