#!/usr/bin/env python3
"""
EfficientNetV2 모델 성능 측정 스크립트

data/train 및 data/test 데이터셋을 사용하여 모델 성능을 평가합니다.

사용법:
    python scripts/evaluate_model.py
    python scripts/evaluate_model.py --threshold 0.6
    python scripts/evaluate_model.py --output docs/model_evaluation.md
"""
import os
import sys
import argparse
import json
from pathlib import Path
from datetime import datetime

import numpy as np
import cv2
from sklearn.metrics import confusion_matrix, accuracy_score, classification_report

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.classifier import get_classifier
from config import MODEL_PATH, IMAGE_SIZE

# 설정
TRAIN_DATA_DIR = "data/train"
TEST_DATA_DIR = "data/test"
DEFAULT_THRESHOLD = 0.6
CLASS_NAMES = ["EMPTY", "INVALID", "OCCUPIED"]
CLASS_TO_IDX = {"EMPTY": 0, "INVALID": 1, "OCCUPIED": 2}


def get_model_size_mb(filepath: str) -> float:
    """모델 파일 크기 (MB)"""
    if os.path.exists(filepath):
        return os.path.getsize(filepath) / (1024 * 1024)
    return 0.0


def load_images_from_directory(data_dir: str) -> tuple:
    """디렉토리에서 이미지 로드 (3-class)"""
    images = []
    labels = []
    filenames = []

    class_dirs = ["empty", "invalid", "occupied"]
    for class_name in class_dirs:
        class_dir = Path(data_dir) / class_name
        if not class_dir.exists():
            continue
        for fpath in sorted(class_dir.glob("*.jp*g")) + list(class_dir.glob("*.png")):
            img = cv2.imread(str(fpath))
            if img is None:
                continue
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            images.append(img_rgb)
            labels.append(CLASS_TO_IDX[class_name.upper()])
            filenames.append(fpath.name)

    return images, np.array(labels), filenames


def evaluate_model(classifier, images: list, labels: np.ndarray, threshold: float) -> dict:
    """모델 성능 평가 (3-class)"""
    predictions = []
    raw_scores = []

    for img in images:
        pred_status, raw_score, proba = classifier.predict(img, threshold=threshold)

        if pred_status == "UNKNOWN":
            pred_label = int(np.argmax([proba["empty"], proba["invalid"], proba["occupied"]]))
        else:
            pred_label = CLASS_TO_IDX.get(pred_status, int(np.argmax([proba["empty"], proba["invalid"], proba["occupied"]])))

        predictions.append(pred_label)
        raw_scores.append(raw_score)

    y_pred = np.array(predictions)
    y_true = labels

    cm = confusion_matrix(y_true, y_pred, labels=[0, 1, 2])
    accuracy = accuracy_score(y_true, y_pred)
    report = classification_report(y_true, y_pred, labels=[0, 1, 2], target_names=CLASS_NAMES, output_dict=True)

    return {
        "accuracy": accuracy,
        "confusion_matrix": cm.tolist(),
        "predictions": y_pred.tolist(),
        "raw_scores": raw_scores,
        "report": report,
    }


def find_misclassified(filenames: list, labels: np.ndarray, predictions: list) -> list:
    """오분류된 이미지 찾기"""
    misclassified = []
    for fname, true_label, pred_label in zip(filenames, labels, predictions):
        if true_label != pred_label:
            misclassified.append({
                "filename": fname,
                "true": CLASS_NAMES[true_label],
                "predicted": CLASS_NAMES[pred_label],
            })
    return misclassified


def generate_report(train_results: dict, test_results: dict, metadata: dict,
                    threshold: float, misclassified_train: list, misclassified_test: list) -> str:
    """마크다운 리포트 생성"""
    
    report = f"""# EfficientNetV2 모델 성능 평가 리포트

**생성일시**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**모델 버전**: {metadata.get('version', 'unknown')}  
**모델 파일**: `{MODEL_PATH}`  
**결정 임계값**: {threshold}

---

## 요약

| 데이터셋 | 정확도 |
|:--------:|:------:|
| **Train** | {train_results['accuracy']:.1%} |
| **Test** | {test_results['accuracy']:.1%} |

---

## Train 데이터셋 결과

### Confusion Matrix

```
                 Predicted
                 EMPTY  INVALID  OCCUPIED
Actual EMPTY    {train_results['confusion_matrix'][0][0]:5d}    {train_results['confusion_matrix'][0][1]:5d}    {train_results['confusion_matrix'][0][2]:5d}
Actual INVALID  {train_results['confusion_matrix'][1][0]:5d}    {train_results['confusion_matrix'][1][1]:5d}    {train_results['confusion_matrix'][1][2]:5d}
Actual OCCUPIED {train_results['confusion_matrix'][2][0]:5d}    {train_results['confusion_matrix'][2][1]:5d}    {train_results['confusion_matrix'][2][2]:5d}
```

### 성능 지표

| 지표 | EMPTY | INVALID | OCCUPIED |
|------|:-----:|:------:|:--------:|
| **Recall** | {train_results['report']['EMPTY']['recall']:.1%} | {train_results['report']['INVALID']['recall']:.1%} | {train_results['report']['OCCUPIED']['recall']:.1%} |
| **Precision** | {train_results['report']['EMPTY']['precision']:.1%} | {train_results['report']['INVALID']['precision']:.1%} | {train_results['report']['OCCUPIED']['precision']:.1%} |

"""
    
    if misclassified_train:
        report += f"""### 오분류 이미지 ({len(misclassified_train)}개)

| 파일명 | 실제 | 예측 |
|--------|:----:|:----:|
"""
        for item in misclassified_train[:10]:  # 최대 10개만 표시
            report += f"| {item['filename']} | {item['true']} | {item['predicted']} |\n"
        
        if len(misclassified_train) > 10:
            report += f"\n*... 외 {len(misclassified_train) - 10}개*\n"
    
    report += f"""
---

## Test 데이터셋 결과

### Confusion Matrix

```
                 Predicted
                 EMPTY  INVALID  OCCUPIED
Actual EMPTY    {test_results['confusion_matrix'][0][0]:5d}    {test_results['confusion_matrix'][0][1]:5d}    {test_results['confusion_matrix'][0][2]:5d}
Actual INVALID  {test_results['confusion_matrix'][1][0]:5d}    {test_results['confusion_matrix'][1][1]:5d}    {test_results['confusion_matrix'][1][2]:5d}
Actual OCCUPIED {test_results['confusion_matrix'][2][0]:5d}    {test_results['confusion_matrix'][2][1]:5d}    {test_results['confusion_matrix'][2][2]:5d}
```

### 성능 지표

| 지표 | EMPTY | INVALID | OCCUPIED |
|------|:-----:|:------:|:--------:|
| **Recall** | {test_results['report']['EMPTY']['recall']:.1%} | {test_results['report']['INVALID']['recall']:.1%} | {test_results['report']['OCCUPIED']['recall']:.1%} |
| **Precision** | {test_results['report']['EMPTY']['precision']:.1%} | {test_results['report']['INVALID']['precision']:.1%} | {test_results['report']['OCCUPIED']['precision']:.1%} |

"""
    
    if misclassified_test:
        report += f"""### 오분류 이미지 ({len(misclassified_test)}개)

| 파일명 | 실제 | 예측 |
|--------|:----:|:----:|
"""
        for item in misclassified_test:
            report += f"| {item['filename']} | {item['true']} | {item['predicted']} |\n"
    
    report += f"""
---

## 모델 정보

| 항목 | 값 |
|------|:--:|
| **모델 타입** | EfficientNetV2-S |
| **입력 크기** | {IMAGE_SIZE[0]}×{IMAGE_SIZE[1]} |
| **모델 크기** | {get_model_size_mb(MODEL_PATH):.1f} MB |
| **Empty Weight** | {metadata.get('empty_weight', 'N/A')} |
| **학습 정확도** | {metadata.get('accuracy', 'N/A')} |

"""
    return report


def main():
    parser = argparse.ArgumentParser(description='EfficientNetV2 Model Evaluation')
    parser.add_argument('--threshold', type=float, default=DEFAULT_THRESHOLD,
                        help='Decision threshold (default: 0.6)')
    parser.add_argument('--output', type=str, default='docs/model_evaluation.md',
                        help='Output report path')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("EfficientNetV2 TorchScript Model Evaluation")
    print("=" * 60)
    print(f"Model: {MODEL_PATH}")
    print(f"Threshold: {args.threshold}")
    
    # 분류기 로드
    classifier = get_classifier()
    classifier.load_model()
    metadata = classifier.get_metadata()
    
    # Train 데이터 로드 및 평가
    print(f"\n[1/2] Evaluating on Train data: {TRAIN_DATA_DIR}")
    train_images, train_labels, train_filenames = load_images_from_directory(TRAIN_DATA_DIR)
    
    if len(train_images) == 0:
        print(f"  No images found in {TRAIN_DATA_DIR}")
        empty_report = {name: {"recall": 0, "precision": 0} for name in CLASS_NAMES}
        train_results = {
            "accuracy": 0,
            "confusion_matrix": [[0, 0, 0], [0, 0, 0], [0, 0, 0]],
            "predictions": [],
            "report": empty_report,
        }
        misclassified_train = []
    else:
        print(f"  Loaded {len(train_images)} images (empty={sum(train_labels==0)}, invalid={sum(train_labels==1)}, occupied={sum(train_labels==2)})")
        train_results = evaluate_model(classifier, train_images, train_labels, args.threshold)
        misclassified_train = find_misclassified(train_filenames, train_labels, train_results['predictions'])
        print(f"  Accuracy: {train_results['accuracy']:.1%}")
        print(f"  Empty Recall: {train_results['report']['EMPTY']['recall']:.1%}")
        print(f"  Invalid Recall: {train_results['report']['INVALID']['recall']:.1%}")
        print(f"  Occupied Recall: {train_results['report']['OCCUPIED']['recall']:.1%}")
        print(f"  Misclassified: {len(misclassified_train)}")
    
    # Test 데이터 로드 및 평가
    print(f"\n[2/2] Evaluating on Test data: {TEST_DATA_DIR}")
    test_images, test_labels, test_filenames = load_images_from_directory(TEST_DATA_DIR)
    
    if len(test_images) == 0:
        print(f"  No images found in {TEST_DATA_DIR}")
        empty_report = {name: {"recall": 0, "precision": 0} for name in CLASS_NAMES}
        test_results = {
            "accuracy": 0,
            "confusion_matrix": [[0, 0, 0], [0, 0, 0], [0, 0, 0]],
            "predictions": [],
            "report": empty_report,
        }
        misclassified_test = []
    else:
        print(f"  Loaded {len(test_images)} images (empty={sum(test_labels==0)}, invalid={sum(test_labels==1)}, occupied={sum(test_labels==2)})")
        test_results = evaluate_model(classifier, test_images, test_labels, args.threshold)
        misclassified_test = find_misclassified(test_filenames, test_labels, test_results['predictions'])
        print(f"  Accuracy: {test_results['accuracy']:.1%}")
        print(f"  Empty Recall: {test_results['report']['EMPTY']['recall']:.1%}")
        print(f"  Invalid Recall: {test_results['report']['INVALID']['recall']:.1%}")
        print(f"  Occupied Recall: {test_results['report']['OCCUPIED']['recall']:.1%}")
        print(f"  Misclassified: {len(misclassified_test)}")
    
    # 리포트 생성
    print(f"\nGenerating report: {args.output}")
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    
    report = generate_report(train_results, test_results, metadata, 
                            args.threshold, misclassified_train, misclassified_test)
    
    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"Report saved: {args.output}")
    print("\n" + "=" * 60)
    print("Evaluation Complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
