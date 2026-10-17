"""
EfficientNetV2-S PyTorch 학습 스크립트 (3-class)

사용법:
    python scripts/train_torch.py --version 2.0.0 --epochs 10
"""
from __future__ import annotations

import argparse
import json
import os
import random
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader, random_split
from torchvision.models import efficientnet_v2_s, EfficientNet_V2_S_Weights

try:
    from config import IMAGE_SIZE, DEFAULT_CONFIG, CLASS_NAMES
    from app.preprocess import center_crop, apply_clahe
except ImportError:
    import sys
    from pathlib import Path
    PROJECT_ROOT = Path(__file__).parent.parent
    sys.path.insert(0, str(PROJECT_ROOT))
    from config import IMAGE_SIZE, DEFAULT_CONFIG, CLASS_NAMES
    from app.preprocess import center_crop, apply_clahe


class CabinetDataset(Dataset):
    def __init__(self, data_dir: str, augment: bool = False):
        self.data_dir = Path(data_dir)
        self.augment = augment
        self.samples = []

        class_dirs = ["empty", "invalid", "occupied"]
        for idx, name in enumerate(class_dirs):
            class_dir = self.data_dir / name
            if not class_dir.exists():
                continue
            for ext in ["*.jpg", "*.jpeg", "*.png", "*.JPG", "*.JPEG", "*.PNG"]:
                for img_path in class_dir.glob(ext):
                    self.samples.append((str(img_path), idx))

    def __len__(self) -> int:
        return len(self.samples)

    def _augment(self, img: np.ndarray) -> np.ndarray:
        if random.random() < 0.5:
            img = cv2.flip(img, 1)
        if random.random() < 0.5:
            angle = random.uniform(-15, 15)
            h, w = img.shape[:2]
            m = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
            img = cv2.warpAffine(img, m, (w, h), borderMode=cv2.BORDER_REFLECT)
        if random.random() < 0.5:
            value = random.uniform(0.8, 1.2)
            img = np.clip(img * value, 0, 255).astype(np.uint8)
        return img

    def __getitem__(self, idx: int):
        img_path, label = self.samples[idx]
        img = cv2.imread(img_path)
        if img is None:
            img = np.zeros((*IMAGE_SIZE, 3), dtype=np.uint8)
        else:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        if DEFAULT_CONFIG.get("use_center_crop", True):
            img = center_crop(img, DEFAULT_CONFIG.get("center_crop_ratio", 0.8))

        if DEFAULT_CONFIG.get("use_clahe", False):
            img = apply_clahe(img, clip_limit=DEFAULT_CONFIG.get("clahe_clip_limit", 3.0))

        if self.augment:
            img = self._augment(img)

        img = cv2.resize(img, IMAGE_SIZE)
        img = img.astype(np.float32) / 255.0

        weights = EfficientNet_V2_S_Weights.DEFAULT
        mean = np.array(weights.meta.get("mean", [0.485, 0.456, 0.406]), dtype=np.float32)
        std = np.array(weights.meta.get("std", [0.229, 0.224, 0.225]), dtype=np.float32)
        img = (img - mean) / std

        img = np.transpose(img, (2, 0, 1))
        tensor = torch.from_numpy(img)
        return tensor, label


def calculate_class_weights(dataset: CabinetDataset, empty_weight_multiplier: float) -> torch.Tensor:
    counts = [0, 0, 0]
    for _, label in dataset.samples:
        counts[label] += 1

    total = sum(counts)
    weights = []
    for count in counts:
        weights.append(total / (len(counts) * max(count, 1)))

    weights[0] *= empty_weight_multiplier
    return torch.tensor(weights, dtype=torch.float32)


def build_model(num_classes: int = 3) -> nn.Module:
    weights = EfficientNet_V2_S_Weights.DEFAULT
    model = efficientnet_v2_s(weights=weights)
    in_features = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(in_features, num_classes)
    return model


def train_one_epoch(model: nn.Module, loader: DataLoader, criterion, optimizer, device: str) -> float:
    model.train()
    running_loss = 0.0
    for inputs, labels in loader:
        inputs = inputs.to(device)
        labels = labels.to(device)

        optimizer.zero_grad(set_to_none=True)
        outputs = model(inputs)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()
        running_loss += loss.item() * inputs.size(0)

    return running_loss / len(loader.dataset)


def evaluate(model: nn.Module, loader: DataLoader, device: str) -> float:
    model.eval()
    correct = 0
    total = 0
    with torch.inference_mode():
        for inputs, labels in loader:
            inputs = inputs.to(device)
            labels = labels.to(device)
            outputs = model(inputs)
            preds = torch.argmax(outputs, dim=1)
            correct += (preds == labels).sum().item()
            total += labels.size(0)
    return correct / max(total, 1)


def main():
    parser = argparse.ArgumentParser(description="Train EfficientNetV2-S with PyTorch")
    parser.add_argument("--data-dir", type=str, default="data/train_augmented")
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--version", type=str, default="2.0.0")
    parser.add_argument("--empty-weight", type=float, default=2.0)
    parser.add_argument("--val-split", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", type=str, default="models")
    args = parser.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print("=" * 60)
    print("EfficientNetV2-S Training (PyTorch)")
    print("=" * 60)
    print(f"Device: {device}")
    print(f"Data: {args.data_dir}")
    print(f"Epochs: {args.epochs}")
    print(f"Empty weight: {args.empty_weight}x")

    dataset = CabinetDataset(args.data_dir, augment=True)
    val_size = int(len(dataset) * args.val_split)
    train_size = len(dataset) - val_size

    train_dataset, val_dataset = random_split(dataset, [train_size, val_size])
    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True, num_workers=2)
    val_loader = DataLoader(val_dataset, batch_size=args.batch_size, shuffle=False, num_workers=2)

    class_weights = calculate_class_weights(dataset, args.empty_weight).to(device)

    model = build_model(num_classes=3).to(device)
    criterion = nn.CrossEntropyLoss(weight=class_weights)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)

    best_acc = 0.0
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    ckpt_path = output_dir / f"efficientnetv2s_3class_v{args.version}.pth"

    for epoch in range(args.epochs):
        loss = train_one_epoch(model, train_loader, criterion, optimizer, device)
        acc = evaluate(model, val_loader, device)
        print(f"Epoch {epoch + 1}/{args.epochs} - loss: {loss:.4f}, val_acc: {acc:.4f}")

        if acc > best_acc:
            best_acc = acc
            torch.save(model.state_dict(), ckpt_path)

    metadata = {
        "version": args.version,
        "accuracy": float(best_acc),
        "threshold": DEFAULT_CONFIG.get("threshold", 0.6),
        "empty_weight": args.empty_weight,
        "model_type": "EfficientNetV2-S",
        "input_size": list(IMAGE_SIZE),
        "class_indices": {name: idx for idx, name in enumerate(["empty", "invalid", "occupied"])},
        "num_classes": 3,
        "created_at": datetime.now().isoformat(),
    }

    metadata_path = ckpt_path.with_name(ckpt_path.stem + "_metadata.json")
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print(f"Model saved: {ckpt_path}")
    print(f"Metadata saved: {metadata_path}")


if __name__ == "__main__":
    main()
