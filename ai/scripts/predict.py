"""
EfficientNetV2-S TorchScript 모델 예측 스크립트

사물함 이미지의 점유 상태를 예측합니다.

사용법:
    python scripts/predict.py image.jpg
    python scripts/predict.py data/test/occupied/*.jpeg
    python scripts/predict.py image.jpg --threshold 0.7
"""
import sys
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.classifier import get_classifier, predict_image


def predict_single(image_path: str, threshold: float = None, verbose: bool = True) -> dict:
    """단일 이미지 예측"""
    classifier = get_classifier()
    classifier.load_model()
    
    if verbose:
        metadata = classifier.get_metadata()
        print(f"\nModel: EfficientNetV2-S v{metadata.get('version', 'unknown')}")
        print(f"Classes: {metadata.get('num_classes', 2)}")
        print(f"Threshold: {threshold or metadata.get('threshold', 0.6)}")
        print("-" * 50)
    
    result = predict_image(image_path, threshold=threshold)
    
    if verbose:
        print(f"Image: {Path(image_path).name}")
        print(f"Status: {result['status']}")
        print(f"Confidence: {result['confidence']:.4f}")
        
        prob_str = ', '.join([f"{k}={v:.4f}" for k, v in result['probabilities'].items()])
        print(f"Probabilities: {prob_str}")
    
    return result


def predict_batch(image_paths: list, threshold: float = None) -> list:
    """여러 이미지 일괄 예측"""
    classifier = get_classifier()
    classifier.load_model()
    metadata = classifier.get_metadata()
    
    print(f"\nModel: EfficientNetV2-S v{metadata.get('version', 'unknown')}")
    print(f"Classes: {metadata.get('num_classes', 2)}")
    print(f"Images: {len(image_paths)}")
    print("=" * 60)
    
    results = []
    for img_path in image_paths:
        try:
            result = predict_image(img_path, threshold=threshold)
            result['path'] = img_path
            results.append(result)
            
            icons = {
                'EMPTY': '🟢',
                'OCCUPIED': '🔴',
                'UNKNOWN': '🟡',
                'INVALID': '⚫'
            }
            icon = icons.get(result['status'], '❓')
            print(f"{icon} {Path(img_path).name}: {result['status']} ({result['confidence']:.2%})")
        except Exception as e:
            print(f"⚠️ {Path(img_path).name}: Error - {e}")
    
    status_counts = {}
    for r in results:
        status = r['status']
        status_counts[status] = status_counts.get(status, 0) + 1
    
    print("=" * 60)
    summary_str = ', '.join([f"{k}={v}" for k, v in sorted(status_counts.items())])
    print(f"Summary: {summary_str}")
    
    return results


def main():
    parser = argparse.ArgumentParser(description='EfficientNetV2 Locker Prediction')
    parser.add_argument('images', nargs='+', help='Image path(s) to predict')
    parser.add_argument('--threshold', type=float, default=None,
                        help='Decision threshold (default: use model metadata)')
    
    args = parser.parse_args()
    
    image_paths = []
    for pattern in args.images:
        if '*' in pattern:
            image_paths.extend([str(p) for p in Path('.').glob(pattern)])
        else:
            image_paths.append(pattern)
    
    if len(image_paths) == 0:
        print("No images found!")
        sys.exit(1)
    elif len(image_paths) == 1:
        predict_single(image_paths[0], args.threshold)
    else:
        predict_batch(image_paths, args.threshold)


if __name__ == "__main__":
    main()
