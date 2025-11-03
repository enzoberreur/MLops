"""Utility helpers for training, evaluation, and storage."""
from __future__ import annotations

import os
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

import numpy as np
import torch
try:
    from minio import Minio
    from minio.error import S3Error
except ImportError:  # pragma: no cover - MinIO optional for unit tests
    Minio = None  # type: ignore[assignment]
    S3Error = Exception  # type: ignore[assignment]
from torch.utils.data import DataLoader, Dataset, Subset, random_split
from torchvision import datasets, transforms

CLASS_NAMES = ["dandelion", "grass"]


def seed_everything(seed: int = 42) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def get_device() -> torch.device:
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


@dataclass
class DataConfig:
    data_dir: Path
    image_size: int
    batch_size: int
    val_split: float = 0.2
    num_workers: int = 2
    seed: int = 42


class _TransformSubset(Dataset):
    """Apply transforms on top of an existing subset without altering the base dataset."""

    def __init__(self, subset: Subset, transform: transforms.Compose) -> None:
        self.subset = subset
        self.transform = transform

    def __len__(self) -> int:
        return len(self.subset)

    def __getitem__(self, idx: int):
        image, label = self.subset[idx]
        if self.transform:
            image = self.transform(image)
        return image, label


def _build_transforms(image_size: int) -> Tuple[transforms.Compose, transforms.Compose]:
    train_transform = transforms.Compose(
        [
            transforms.Resize((image_size + 16, image_size + 16)),
            transforms.RandomResizedCrop(image_size),
            transforms.RandomHorizontalFlip(),
            transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )
    eval_transform = transforms.Compose(
        [
            transforms.Resize((image_size, image_size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )
    return train_transform, eval_transform


def get_inference_transform(image_size: int) -> transforms.Compose:
    """Transformation used during inference outside of the training loop."""
    _, eval_transform = _build_transforms(image_size)
    return eval_transform


def create_dataloaders(config: DataConfig) -> Tuple[DataLoader, DataLoader, list[str]]:
    seed_everything(config.seed)
    base_dataset = datasets.ImageFolder(root=str(config.data_dir))
    train_transform, eval_transform = _build_transforms(config.image_size)

    val_size = int(len(base_dataset) * config.val_split)
    if val_size == 0:
        val_size = 1
    if val_size == len(base_dataset):
        val_size = max(1, len(base_dataset) - 1)
    train_size = len(base_dataset) - val_size
    train_subset, val_subset = random_split(
        base_dataset,
        [train_size, val_size],
        generator=torch.Generator().manual_seed(config.seed),
    )

    train_dataset = _TransformSubset(train_subset, train_transform)
    val_dataset = _TransformSubset(val_subset, eval_transform)

    pin_memory = torch.cuda.is_available()

    train_loader = DataLoader(
        train_dataset,
        batch_size=config.batch_size,
        shuffle=True,
        num_workers=config.num_workers,
        pin_memory=pin_memory,
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=config.batch_size,
        shuffle=False,
        num_workers=config.num_workers,
        pin_memory=pin_memory,
    )
    class_names = base_dataset.classes
    return train_loader, val_loader, class_names


def get_minio_client() -> Minio:
    if Minio is None:  # pragma: no cover - guarded for tests
        raise ImportError(
            "Le package 'minio' est requis pour interagir avec MinIO. "
            "Installez-le avec `pip install minio`."
        )
    endpoint = os.environ.get("MINIO_ENDPOINT", "http://localhost:9000")
    access_key = os.environ.get("MINIO_ACCESS_KEY", "minioadmin")
    secret_key = os.environ.get("MINIO_SECRET_KEY", "minioadmin")
    secure = os.environ.get("MINIO_SECURE", "false").lower() == "true"
    # Minio library expects host without protocol when secure flag is used
    if endpoint.startswith("http://"):
        endpoint = endpoint.replace("http://", "", 1)
    elif endpoint.startswith("https://"):
        endpoint = endpoint.replace("https://", "", 1)
    return Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)


def ensure_bucket(client: Minio, bucket_name: str) -> None:
    if not client.bucket_exists(bucket_name):
        client.make_bucket(bucket_name)


def upload_file_to_minio(client: Minio, bucket: str, object_name: str, file_path: Path, content_type: str = "application/octet-stream") -> None:
    ensure_bucket(client, bucket)
    client.fput_object(bucket, object_name, file_path, content_type=content_type)


def download_file_from_minio(client: Minio, bucket: str, object_name: str, destination: Path) -> None:
    ensure_bucket(client, bucket)
    destination.parent.mkdir(parents=True, exist_ok=True)
    client.fget_object(bucket, object_name, destination)


def pull_directory_from_minio(client: Minio, bucket: str, prefix: str, destination: Path) -> None:
    """Recursively download all objects under ``prefix`` into destination."""
    destination.mkdir(parents=True, exist_ok=True)
    try:
        objects = client.list_objects(bucket, prefix=prefix, recursive=True)
        for obj in objects:
            rel_path = Path(obj.object_name).relative_to(prefix)
            target_path = destination / rel_path
            target_path.parent.mkdir(parents=True, exist_ok=True)
            client.fget_object(bucket, obj.object_name, target_path)
    except S3Error as exc:  # pragma: no cover - network errors
        raise RuntimeError(f"Failed to pull directory from MinIO: {exc}") from exc
