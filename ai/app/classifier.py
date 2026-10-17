#!/usr/bin/env python3
"""
EfficientNetV2-S TorchScript 분류기 모듈

TorchScript 모델을 로드하고 CPU에서 추론합니다.
384x384 입력 크기를 사용하며, 중앙 크롭 + CLAHE 전처리를 적용합니다.
"""
from __future__ import annotations

import json
import os
from typing import Dict, Tuple

import cv2
import numpy as np
import torch

try:
    from config import MODEL_PATH, DEFAULT_CONFIG
    from app.preprocess import preprocess_image
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from config import MODEL_PATH, DEFAULT_CONFIG
    from app.preprocess import preprocess_image


def _load_metadata(model_path: str) -> Dict:
    metadata_path = model_path.replace(".pt", "_metadata.json")
    if os.path.exists(metadata_path):
        with open(metadata_path) as f:
            return json.load(f)
    return {}


class EfficientNetClassifier:
    """
    EfficientNetV2-S TorchScript 기반 분류기 (CPU 전용)

    지원 클래스:
    - 3-class: empty, invalid, occupied
    """
    _instance = None
    _model = None
    _metadata = None
    _num_classes = 3

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def load_model(self, model_path: str | None = None):
        """TorchScript 모델 로드 (CPU 전용)"""
        if model_path is None:
            model_path = MODEL_PATH

        if self._model is None:
            torch_num_threads = DEFAULT_CONFIG.get("torch_num_threads")
            if torch_num_threads:
                torch.set_num_threads(int(torch_num_threads))

            print(f"Loading TorchScript model: {model_path}")
            self._model = torch.jit.load(model_path, map_location="cpu")
            self._model.eval()

            self._metadata = _load_metadata(model_path)
            self._num_classes = int(self._metadata.get("num_classes", 3))

            print(f"Model version: {self._metadata.get('version', 'unknown')}")
            print(f"Model accuracy: {self._metadata.get('accuracy', 'unknown')}")
            print(f"Model classes: {self._num_classes}")
            print("TorchScript model loaded successfully on CPU")

        return self._model

    def predict(
        self,
        image: np.ndarray,
        threshold: float | None = None,
        unknown_threshold: float | None = None,
        invalid_threshold: float | None = None,
    ) -> Tuple[str, float, Dict[str, float]]:
        """이미지 예측"""
        if self._model is None:
            self.load_model()

        if threshold is None:
            threshold = self._metadata.get("threshold", DEFAULT_CONFIG.get("threshold", 0.6))
        if unknown_threshold is None:
            unknown_threshold = DEFAULT_CONFIG.get("unknown_threshold", 0.2)
        if invalid_threshold is None:
            invalid_threshold = DEFAULT_CONFIG.get("invalid_threshold", 0.5)

        input_tensor = preprocess_image(image)

        with torch.inference_mode():
            logits = self._model(input_tensor)
            if logits.ndim == 2 and logits.shape[1] > 1:
                probs = torch.softmax(logits, dim=1)[0].cpu().numpy()
            else:
                probs = torch.sigmoid(logits)[0].cpu().numpy()

        if self._num_classes == 2:
            occupied_prob = float(probs[0])
            empty_prob = 1 - occupied_prob
            proba = {"empty": empty_prob, "occupied": occupied_prob}

            if abs(empty_prob - occupied_prob) < unknown_threshold:
                status = "UNKNOWN"
                confidence = max(empty_prob, occupied_prob)
            elif occupied_prob > threshold:
                status = "OCCUPIED"
                confidence = occupied_prob
            else:
                status = "EMPTY"
                confidence = empty_prob
        else:
            empty_prob = float(probs[0])
            invalid_prob = float(probs[1])
            occupied_prob = float(probs[2])

            proba = {
                "empty": empty_prob,
                "invalid": invalid_prob,
                "occupied": occupied_prob,
            }

            if invalid_prob >= invalid_threshold:
                status = "INVALID"
                confidence = invalid_prob
            elif abs(empty_prob - occupied_prob) < unknown_threshold:
                status = "UNKNOWN"
                confidence = max(empty_prob, occupied_prob)
            elif occupied_prob > threshold:
                status = "OCCUPIED"
                confidence = occupied_prob
            else:
                status = "EMPTY"
                confidence = empty_prob

        return status, confidence, proba

    def get_metadata(self) -> Dict:
        return self._metadata or {}


_classifier: EfficientNetClassifier | None = None


def get_classifier() -> EfficientNetClassifier:
    global _classifier
    if _classifier is None:
        _classifier = EfficientNetClassifier()
    return _classifier


def predict_image(image_path: str, threshold: float | None = None) -> Dict:
    """이미지 파일 예측 (편의 함수)"""
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Cannot read image: {image_path}")

    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    classifier = get_classifier()
    status, confidence, proba = classifier.predict(img_rgb, threshold=threshold)

    return {
        "model": "EfficientNetV2-S TorchScript",
        "status": status,
        "confidence": confidence,
        "probabilities": proba,
    }


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python classifier.py <image_path>")
        sys.exit(1)

    result = predict_image(sys.argv[1])
    print(f"Status: {result['status']}")
    print(f"Confidence: {result['confidence']:.4f}")
    print(f"Probabilities: {result['probabilities']}")
