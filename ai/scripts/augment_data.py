"""
데이터 증강 스크립트 (v2.0)

이 스크립트는 기존 학습 이미지를 다양한 방식으로 변형하여
학습 데이터를 확장합니다.

증강 기법:
1. 회전 (Rotation): -15° ~ +15° 범위의 미세 회전
2. 좌우 반전 (Horizontal Flip): 이미지 좌우 뒤집기
3. 밝기 조정 (Brightness): 어둡게/밝게 변형
4. 대비 조정 (Contrast): 대비 증가/감소
5. 노이즈 추가 (Gaussian Noise): 미세한 잡음 추가
6. [NEW] 그림자 시뮬레이션 (Shadow): 부분 영역 어둡게
7. [NEW] 감마 보정 (Gamma): 비선형 밝기 변화
8. [NEW] 그라데이션 조명 (Gradient): 한쪽이 밝고 반대쪽이 어두움
"""
import os
import cv2
import numpy as np
import random
from pathlib import Path
from typing import List, Tuple

INPUT_DIR = "data/train"
OUTPUT_DIR = "data/train_augmented"
IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png']


def rotate_image(image: np.ndarray, angle: float) -> np.ndarray:
    """
    이미지 회전
    
    회전은 사물함의 설치 각도 차이나 카메라 기울기에 대한
    모델의 강건성을 높여줍니다.
    """
    h, w = image.shape[:2]
    center = (w // 2, h // 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(image, matrix, (w, h), borderMode=cv2.BORDER_REFLECT)
    return rotated


def flip_horizontal(image: np.ndarray) -> np.ndarray:
    """
    좌우 반전
    
    물건의 위치가 좌/우 어디든 감지할 수 있도록
    모델의 위치 불변성을 학습시킵니다.
    """
    return cv2.flip(image, 1)


def adjust_brightness(image: np.ndarray, factor: float) -> np.ndarray:
    """
    밝기 조정
    
    조명 조건이 달라도 물체를 인식할 수 있도록
    다양한 밝기의 이미지를 학습합니다.
    
    factor > 1.0: 밝게
    factor < 1.0: 어둡게
    """
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    hsv = hsv.astype(np.float32)
    hsv[:, :, 2] = np.clip(hsv[:, :, 2] * factor, 0, 255)
    hsv = hsv.astype(np.uint8)
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)


def adjust_contrast(image: np.ndarray, factor: float) -> np.ndarray:
    """
    대비 조정
    
    대비가 낮은 환경(흐린 날, 형광등)이나
    높은 환경(직사광선)에서도 인식할 수 있도록 합니다.
    
    factor > 1.0: 대비 증가
    factor < 1.0: 대비 감소
    """
    mean = np.mean(image)
    adjusted = np.clip((image - mean) * factor + mean, 0, 255)
    return adjusted.astype(np.uint8)


def add_gaussian_noise(image: np.ndarray, sigma: float = 10) -> np.ndarray:
    """
    가우시안 노이즈 추가
    
    카메라 센서 노이즈나 압축 아티팩트에 강건한
    모델을 만들기 위해 약간의 노이즈를 추가합니다.
    """
    noise = np.random.normal(0, sigma, image.shape).astype(np.float32)
    noisy = np.clip(image.astype(np.float32) + noise, 0, 255)
    return noisy.astype(np.uint8)


def add_shadow(image: np.ndarray, shadow_type: str = 'vertical', 
               opacity: float = 0.5) -> np.ndarray:
    """
    그림자 시뮬레이션
    
    이미지의 일부 영역을 어둡게 만들어 그림자 효과를 시뮬레이션합니다.
    실제 환경에서 창문 빛, 형광등 위치 등으로 인한 그림자에 강건해집니다.
    
    Args:
        image: 입력 이미지
        shadow_type: 'vertical', 'horizontal', 'random'
        opacity: 그림자 강도 (0=투명, 1=완전 검정)
    """
    h, w = image.shape[:2]
    result = image.copy().astype(np.float32)
    
    mask = np.ones((h, w), dtype=np.float32)
    
    if shadow_type == 'vertical':
        start = random.randint(0, w // 2)
        end = random.randint(start + w // 4, w)
        mask[:, start:end] = 1 - opacity
        
    elif shadow_type == 'horizontal':
        start = random.randint(0, h // 2)
        end = random.randint(start + h // 4, h)
        mask[start:end, :] = 1 - opacity
        
    elif shadow_type == 'random':
        x1 = random.randint(0, w // 2)
        y1 = random.randint(0, h // 2)
        x2 = random.randint(x1 + w // 4, w)
        y2 = random.randint(y1 + h // 4, h)
        mask[y1:y2, x1:x2] = 1 - opacity
    
    for c in range(3):
        result[:, :, c] = result[:, :, c] * mask
    
    return np.clip(result, 0, 255).astype(np.uint8)


def gamma_correction(image: np.ndarray, gamma: float) -> np.ndarray:
    """
    감마 보정
    
    비선형 밝기 변화를 적용합니다.
    gamma < 1: 이미지가 밝아짐 (어두운 영역이 더 밝아짐)
    gamma > 1: 이미지가 어두워짐 (밝은 영역이 더 어두워짐)
    
    조명 조건의 다양한 변화를 시뮬레이션합니다.
    
    Args:
        image: 입력 이미지
        gamma: 감마 값 (0.5~2.0 권장)
    """
    inv_gamma = 1.0 / gamma
    table = np.array([
        ((i / 255.0) ** inv_gamma) * 255 
        for i in range(256)
    ]).astype(np.uint8)
    
    return cv2.LUT(image, table)


def add_gradient_lighting(image: np.ndarray, direction: str = 'left',
                          intensity: float = 0.4) -> np.ndarray:
    """
    그라데이션 조명 효과
    
    한쪽에서 빛이 들어오는 효과를 시뮬레이션합니다.
    창문이나 조명 위치에 따른 밝기 차이에 강건해집니다.
    
    Args:
        image: 입력 이미지
        direction: 'left', 'right', 'top', 'bottom'
        intensity: 그라데이션 강도
    """
    h, w = image.shape[:2]
    result = image.copy().astype(np.float32)
    
    if direction == 'left':
        gradient = np.linspace(1 + intensity, 1 - intensity, w)
        gradient = np.tile(gradient, (h, 1))
    elif direction == 'right':
        gradient = np.linspace(1 - intensity, 1 + intensity, w)
        gradient = np.tile(gradient, (h, 1))
    elif direction == 'top':
        gradient = np.linspace(1 + intensity, 1 - intensity, h)
        gradient = np.tile(gradient.reshape(-1, 1), (1, w))
    elif direction == 'bottom':
        gradient = np.linspace(1 - intensity, 1 + intensity, h)
        gradient = np.tile(gradient.reshape(-1, 1), (1, w))
    else:
        return image
    
    for c in range(3):
        result[:, :, c] = result[:, :, c] * gradient
    
    return np.clip(result, 0, 255).astype(np.uint8)


def augment_image(image: np.ndarray) -> List[Tuple[np.ndarray, str]]:
    """
    하나의 이미지에 대해 모든 증강 기법 적용
    
    Returns:
        [(증강된 이미지, 접미사), ...]
    """
    augmented = []
    
    augmented.append((rotate_image(image, -10), "rot_n10"))
    augmented.append((rotate_image(image, 10), "rot_p10"))
    
    augmented.append((flip_horizontal(image), "flip"))
    
    augmented.append((adjust_brightness(image, 0.7), "dark"))
    augmented.append((adjust_brightness(image, 1.3), "bright"))
    
    augmented.append((adjust_contrast(image, 0.8), "lowcon"))
    augmented.append((adjust_contrast(image, 1.2), "highcon"))
    
    augmented.append((add_gaussian_noise(image, 15), "noise"))
    
    augmented.append((add_shadow(image, 'vertical', 0.4), "shadow_v"))
    augmented.append((add_shadow(image, 'horizontal', 0.4), "shadow_h"))
    augmented.append((add_shadow(image, 'random', 0.5), "shadow_r"))
    
    augmented.append((gamma_correction(image, 0.6), "gamma_bright"))
    augmented.append((gamma_correction(image, 1.5), "gamma_dark"))
    augmented.append((gamma_correction(image, 2.0), "gamma_vdark"))
    
    augmented.append((add_gradient_lighting(image, 'left', 0.3), "grad_left"))
    augmented.append((add_gradient_lighting(image, 'right', 0.3), "grad_right"))
    augmented.append((add_gradient_lighting(image, 'top', 0.3), "grad_top"))
    
    rotated = rotate_image(image, 5)
    augmented.append((adjust_brightness(rotated, 0.85), "combo1"))
    
    flipped = flip_horizontal(image)
    augmented.append((adjust_contrast(flipped, 1.1), "combo2"))
    
    shadow_img = add_shadow(image, 'vertical', 0.3)
    augmented.append((gamma_correction(shadow_img, 1.3), "combo3"))
    
    rotated2 = rotate_image(image, -5)
    augmented.append((add_gradient_lighting(rotated2, 'left', 0.25), "combo4"))
    
    return augmented


def process_directory(input_dir: Path, output_dir: Path):
    """디렉토리 내 모든 이미지 증강"""
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    image_files = []
    for ext in IMAGE_EXTENSIONS:
        image_files.extend(input_dir.glob(f"*{ext}"))
        image_files.extend(input_dir.glob(f"*{ext.upper()}"))
    
    print(f"Found {len(image_files)} images in {input_dir}")
    
    for img_path in image_files:
        image = cv2.imread(str(img_path))
        if image is None:
            print(f"Cannot read: {img_path}")
            continue
        
        original_output = output_dir / img_path.name
        cv2.imwrite(str(original_output), image)
        
        augmented_images = augment_image(image)
        
        for aug_img, suffix in augmented_images:
            stem = img_path.stem
            ext = img_path.suffix
            aug_path = output_dir / f"{stem}_{suffix}{ext}"
            cv2.imwrite(str(aug_path), aug_img)
    
    result_count = sum(1 for _ in output_dir.glob("*.*") 
                       if _.suffix.lower() in IMAGE_EXTENSIONS)
    print(f"Generated {result_count} images in {output_dir}")


def main():
    print("=" * 60)
    print("Data Augmentation Script")
    print("=" * 60)
    
    classes = ['empty', 'invalid', 'occupied']
    
    for cls in classes:
        input_path = Path(INPUT_DIR) / cls
        output_path = Path(OUTPUT_DIR) / cls
        
        if not input_path.exists():
            print(f"\nDirectory not found: {input_path}")
            continue
        
        print(f"\nProcessing: {cls}")
        process_directory(input_path, output_path)
    
    print("\n" + "=" * 60)
    print("Augmentation complete!")
    print(f"Output directory: {OUTPUT_DIR}")
    print("=" * 60)
    
    print("\nSummary:")
    for cls in classes:
        original = Path(INPUT_DIR) / cls
        augmented = Path(OUTPUT_DIR) / cls
        
        if original.exists():
            orig_count = sum(1 for _ in original.glob("*.*") 
                           if _.suffix.lower() in IMAGE_EXTENSIONS)
            aug_count = sum(1 for _ in augmented.glob("*.*") 
                          if _.suffix.lower() in IMAGE_EXTENSIONS) if augmented.exists() else 0
            print(f"  {cls}: {orig_count} → {aug_count} images ({aug_count/max(orig_count,1):.1f}x)")


if __name__ == "__main__":
    main()
