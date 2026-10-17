"""
Torch 전처리 유틸리티 모듈

EfficientNetV2-S (torchvision) 기준 전처리를 제공합니다.
중앙 크롭 + (선택) CLAHE + 384x384 리사이즈 + 정규화.
"""
from __future__ import annotations

import numpy as np
import cv2
import torch
from torchvision.models import EfficientNet_V2_S_Weights

try:
    from config import IMAGE_SIZE, DEFAULT_CONFIG
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from config import IMAGE_SIZE, DEFAULT_CONFIG


_WEIGHTS = EfficientNet_V2_S_Weights.DEFAULT
_MEAN = _WEIGHTS.meta.get("mean", [0.485, 0.456, 0.406])
_STD = _WEIGHTS.meta.get("std", [0.229, 0.224, 0.225])


def center_crop(img: np.ndarray, ratio: float = 0.8) -> np.ndarray:
    """이미지 중앙 영역만 크롭"""
    h, w = img.shape[:2]
    margin_h = int(h * (1 - ratio) / 2)
    margin_w = int(w * (1 - ratio) / 2)
    return img[margin_h:h - margin_h, margin_w:w - margin_w]


def apply_clahe(img: np.ndarray, clip_limit: float = 3.0, tile_size: int = 8) -> np.ndarray:
    """CLAHE 적용 (RGB 입력/출력)."""
    lab = cv2.cvtColor(img, cv2.COLOR_RGB2LAB)
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(tile_size, tile_size))
    lab[:, :, 0] = clahe.apply(lab[:, :, 0])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)


def _normalize(img: np.ndarray) -> np.ndarray:
    """[0,1] 스케일 후 mean/std 정규화"""
    img = img.astype(np.float32) / 255.0
    mean = np.array(_MEAN, dtype=np.float32)
    std = np.array(_STD, dtype=np.float32)
    return (img - mean) / std


def preprocess_image(image: np.ndarray) -> torch.Tensor:
    """
    이미지 전처리 (중앙 크롭 + CLAHE + Resize + Torch 정규화)

    Returns:
        torch.Tensor: (1, 3, 384, 384)
    """
    img = image.copy()

    if DEFAULT_CONFIG.get("use_center_crop", True):
        crop_ratio = DEFAULT_CONFIG.get("center_crop_ratio", 0.8)
        img = center_crop(img, crop_ratio)

    if DEFAULT_CONFIG.get("use_clahe", False):
        clip_limit = DEFAULT_CONFIG.get("clahe_clip_limit", 3.0)
        img = apply_clahe(img, clip_limit=clip_limit)

    resized = cv2.resize(img, IMAGE_SIZE)
    normalized = _normalize(resized)

    chw = np.transpose(normalized, (2, 0, 1))
    tensor = torch.from_numpy(chw).unsqueeze(0)
    return tensor
