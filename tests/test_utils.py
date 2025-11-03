from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from models.utils import CLASS_NAMES, DataConfig, create_dataloaders


@pytest.fixture()
def tmp_dataset(tmp_path: Path) -> Path:
    for class_name in CLASS_NAMES:
        class_dir = tmp_path / class_name
        class_dir.mkdir(parents=True)
        for idx in range(2):
            image = Image.new("RGB", (32, 32), color=(idx * 40, idx * 40, idx * 40))
            image.save(class_dir / f"{idx}.jpg")
    return tmp_path


def test_create_dataloaders(tmp_dataset: Path) -> None:
    config = DataConfig(data_dir=tmp_dataset, image_size=32, batch_size=2, val_split=0.5)
    train_loader, val_loader, classes = create_dataloaders(config)

    assert set(classes) == set(CLASS_NAMES)
    train_batch = next(iter(train_loader))
    val_batch = next(iter(val_loader))
    assert train_batch[0].shape[1:] == (3, 32, 32)
    assert val_batch[0].shape[1:] == (3, 32, 32)
