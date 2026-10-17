"""설정 모듈 - EfficientNetV2 전용"""
import os

MODEL_PATH = os.getenv("MODEL_PATH", "models/efficientnetv2s_3class_traced_v2.0.0.pt")

IMAGE_SIZE = (384, 384)

DEFAULT_CONFIG = {
    'use_center_crop': True,
    'center_crop_ratio': 0.8,
    
    'use_clahe': False,
    'clahe_clip_limit': 3.0,
    
    'threshold': 0.6,
    
    'unknown_threshold': 0.2,
    'invalid_threshold': 0.5,

    'torch_num_threads': 4,
}

CLASS_NAMES = ["empty", "invalid", "occupied"]
