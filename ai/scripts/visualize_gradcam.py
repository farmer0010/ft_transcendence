#!/usr/bin/env python3
"""
Grad-CAM 시각화 스크립트 (PyTorch)

EfficientNetV2-S 모델이 어떤 영역을 보고 판단했는지 시각화합니다.

사용법:
    python scripts/visualize_gradcam.py <image_path>
    python scripts/visualize_gradcam.py <image1> <image2> ...
"""
import os
import sys
import json
import argparse
import cv2
import numpy as np
from pathlib import Path

import torch
import torch.nn as nn
import matplotlib.pyplot as plt
from torchvision.models import efficientnet_v2_s

# 프로젝트 루트
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import MODEL_PATH, IMAGE_SIZE, DEFAULT_CONFIG
from app.classifier import get_classifier
from app.preprocess import preprocess_image

# 설정
OUTPUT_DIR = "data/visualizations/gradcam"
THRESHOLD = DEFAULT_CONFIG.get('threshold', 0.6)


def find_last_conv_layer(model: nn.Module) -> nn.Module:
    """마지막 Conv2d 레이어 찾기"""
    last_conv = None
    for module in model.modules():
        if isinstance(module, nn.Conv2d):
            last_conv = module
    if last_conv is None:
        raise ValueError("No Conv2d layer found in model")
    return last_conv


def make_gradcam_heatmap(model: nn.Module, image: torch.Tensor, pred_index: int | None = None) -> np.ndarray:
    """Grad-CAM 히트맵 생성"""
    activations = {}
    gradients = {}

    def forward_hook(_, __, output):
        activations["value"] = output

    def backward_hook(_, __, grad_output):
        gradients["value"] = grad_output[0]

    last_conv = find_last_conv_layer(model)
    handle_fwd = last_conv.register_forward_hook(forward_hook)
    handle_bwd = last_conv.register_full_backward_hook(backward_hook)

    model.zero_grad(set_to_none=True)
    output = model(image)

    if pred_index is None:
        pred_index = int(torch.argmax(output, dim=1).item())

    target = output[:, pred_index]
    target.backward()

    handle_fwd.remove()
    handle_bwd.remove()

    if "value" not in activations or "value" not in gradients:
        raise RuntimeError("Failed to capture activations/gradients for Grad-CAM")

    grads = gradients["value"]
    conv_out = activations["value"]

    weights = torch.mean(grads, dim=(2, 3), keepdim=True)
    cam = torch.sum(weights * conv_out, dim=1).squeeze(0)
    cam = torch.relu(cam)

    cam = cam - cam.min()
    if cam.max() > 0:
        cam = cam / cam.max()

    return cam.detach().cpu().numpy()


def overlay_gradcam(image, heatmap, alpha=0.4):
    """히트맵을 원본 이미지에 오버레이"""
    heatmap_resized = cv2.resize(heatmap, (image.shape[1], image.shape[0]))
    heatmap_colored = np.uint8(255 * heatmap_resized)
    heatmap_colored = cv2.applyColorMap(heatmap_colored, cv2.COLORMAP_JET)
    heatmap_colored = cv2.cvtColor(heatmap_colored, cv2.COLOR_BGR2RGB)
    superimposed = cv2.addWeighted(image, 1 - alpha, heatmap_colored, alpha, 0)
    return superimposed


def _load_torch_model(weights_path: str) -> nn.Module:
    """PyTorch 모델 로드 (Grad-CAM용, .pth)"""
    model = efficientnet_v2_s(weights=None)
    in_features = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(in_features, 3)

    state = torch.load(weights_path, map_location="cpu")
    model.load_state_dict(state, strict=True)
    model.eval()
    return model


def _resolve_weights_path() -> str:
    env_path = os.getenv("TORCH_WEIGHTS_PATH")
    if env_path:
        return env_path
    model_path = Path(MODEL_PATH)
    if model_path.suffix == ".pt":
        metadata_path = model_path.with_name(model_path.stem + "_metadata.json")

        version = None
        if metadata_path.exists():
            try:
                with open(metadata_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                version = meta.get("version")
            except Exception:
                version = None

        if version:
            candidate = model_path.parent / f"efficientnetv2s_3class_v{version}.pth"
            if candidate.exists():
                return str(candidate)

        # 기본 규칙
        if model_path.name.endswith("_traced.pt"):
            candidate = model_path.with_name(model_path.name.replace("_traced.pt", ".pth"))
            if candidate.exists():
                return str(candidate)
        candidate = model_path.with_suffix(".pth")
        if candidate.exists():
            return str(candidate)

        # 최후: models 디렉토리에서 가장 최신 .pth 선택
        models_dir = model_path.parent if model_path.parent.exists() else Path("models")
        if models_dir.exists():
            pths = sorted(models_dir.glob("*.pth"), key=lambda p: p.stat().st_mtime, reverse=True)
            if pths:
                return str(pths[0])

    return MODEL_PATH.replace(".pt", ".pth")


def visualize_gradcam(image_path: str, save: bool = True):
    """이미지에 대한 Grad-CAM 시각화"""
    print(f"Model: {MODEL_PATH}")
    print(f"Image size: {IMAGE_SIZE}")
    print(f"Threshold: {THRESHOLD}")

    weights_path = _resolve_weights_path()
    if not os.path.exists(weights_path):
        print(f"Torch weights not found: {weights_path}")
        print("Grad-CAM은 .pth 체크포인트가 필요합니다.")
        return

    print("Loading torch model for Grad-CAM...")
    model = _load_torch_model(weights_path)

    img = cv2.imread(image_path)
    if img is None:
        print(f"Cannot read image: {image_path}")
        return

    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    # 예측 (TorchScript classifier 사용)
    classifier = get_classifier()
    classifier.load_model()
    status, confidence, proba = classifier.predict(img_rgb)

    print(f"\nPrediction: {status} ({confidence:.2%})")
    prob_str = ", ".join([f"{k}={v:.2%}" for k, v in proba.items()])
    print(f"Probabilities: {prob_str}")

    input_tensor = preprocess_image(img_rgb).requires_grad_(True)
    try:
        heatmap = make_gradcam_heatmap(model, input_tensor, None)
    except Exception as e:
        print(f"Grad-CAM error: {e}")
        return

    img_resized = cv2.resize(img_rgb, IMAGE_SIZE)
    superimposed = overlay_gradcam(img_resized, heatmap)
    
    # 시각화
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    
    axes[0].imshow(img_resized)
    axes[0].set_title('Original', fontsize=14)
    axes[0].axis('off')
    
    axes[1].imshow(heatmap, cmap='jet')
    axes[1].set_title('Grad-CAM Heatmap', fontsize=14)
    axes[1].axis('off')
    
    axes[2].imshow(superimposed)
    axes[2].set_title('Overlay', fontsize=14)
    axes[2].axis('off')
    
    # 상태별 색상
    colors = {
        'EMPTY': 'green',
        'OCCUPIED': 'red',
        'UNKNOWN': 'orange',
        'INVALID': 'gray'
    }
    color = colors.get(status, 'black')
    fig.suptitle(f'{status} ({confidence:.2%})', fontsize=16, color=color, fontweight='bold')
    
    plt.tight_layout()
    
    if save:
        Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
        output_path = Path(OUTPUT_DIR) / f"gradcam_{Path(image_path).stem}.png"
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"Saved: {output_path}")
    
    plt.show()


def compare_gradcam(image_paths: list, save: bool = True):
    """여러 이미지 Grad-CAM 비교"""
    print(f"Model: {MODEL_PATH}")
    print(f"Image size: {IMAGE_SIZE}")

    weights_path = _resolve_weights_path()
    if not os.path.exists(weights_path):
        print(f"Torch weights not found: {weights_path}")
        print("Grad-CAM은 .pth 체크포인트가 필요합니다.")
        return

    model = _load_torch_model(weights_path)
    n = len(image_paths)
    fig, axes = plt.subplots(2, n, figsize=(5 * n, 10))

    for i, image_path in enumerate(image_paths):
        img = cv2.imread(image_path)
        if img is None:
            continue

        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        # 예측 (classifier 사용)
        classifier = get_classifier()
        status, confidence, _ = classifier.predict(img_rgb)

        input_tensor = preprocess_image(img_rgb).requires_grad_(True)
        img_resized = cv2.resize(img_rgb, IMAGE_SIZE)

        try:
            heatmap = make_gradcam_heatmap(model, input_tensor, None)
            superimposed = overlay_gradcam(img_resized, heatmap)
        except Exception:
            superimposed = img_resized
        
        # 상태별 색상
        colors = {
            'EMPTY': 'green',
            'OCCUPIED': 'red', 
            'UNKNOWN': 'orange',
            'INVALID': 'gray'
        }
        color = colors.get(status, 'black')
        
        ax_img = axes[0, i] if n > 1 else axes[0]
        ax_img.imshow(img_resized)
        ax_img.set_title(f'{status} ({confidence:.2%})', color=color, fontweight='bold')
        ax_img.axis('off')
        
        ax_cam = axes[1, i] if n > 1 else axes[1]
        ax_cam.imshow(superimposed)
        ax_cam.set_title(Path(image_path).name, fontsize=10)
        ax_cam.axis('off')
    
    plt.suptitle('Grad-CAM Comparison', fontsize=16, fontweight='bold')
    plt.tight_layout()
    
    if save:
        Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
        output_path = Path(OUTPUT_DIR) / "gradcam_comparison.png"
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"Saved: {output_path}")
    
    plt.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='EfficientNetV2 Grad-CAM visualization',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/visualize_gradcam.py data/train/empty/001.jpg
  python scripts/visualize_gradcam.py img1.jpg img2.jpg
"""
    )
    parser.add_argument('images', nargs='+', help='Image path(s)')
    parser.add_argument('--no-save', action='store_true', help='Do not save output')
    
    args = parser.parse_args()
    
    if len(args.images) == 1:
        visualize_gradcam(args.images[0], save=not args.no_save)
    else:
        compare_gradcam(args.images, save=not args.no_save)
