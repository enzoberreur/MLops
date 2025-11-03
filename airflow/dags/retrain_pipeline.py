"""Airflow DAG to retrain the classifier using the latest processed dataset from MinIO."""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.models import Variable
from airflow.operators.python import PythonOperator

from models.train import train as train_model
from models.utils import get_minio_client, pull_directory_from_minio

DATA_BASE_PATH = Path(Variable.get("data_base_path", "/opt/airflow/data"))
PROCESSED_DATA_DIR = DATA_BASE_PATH / "processed"
MINIO_DATA_BUCKET = Variable.get("minio_data_bucket", "dandelion-data")


def sync_processed_from_minio() -> None:
    client = get_minio_client()
    pull_directory_from_minio(client, MINIO_DATA_BUCKET, "processed", PROCESSED_DATA_DIR)


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
        dag_id="dandelion_retrain_pipeline",
        default_args=default_args,
        schedule="@monthly",
        start_date=datetime(2024, 1, 1),
        catchup=False,
        tags=["dandelion", "mlops", "retrain"],
    ) as dag:
        sync = PythonOperator(task_id="sync_processed_data", python_callable=sync_processed_from_minio)
        train = PythonOperator(task_id="train_model", python_callable=run_training)

        sync >> train

    return dag


globals()["dandelion_retrain_pipeline"] = build_dag()
