#!/usr/bin/env python3
"""설정 모듈 - EfficientNetV2 전용"""
import os

# EfficientNetV2 TorchScript 모델 경로
MODEL_PATH = os.getenv("MODEL_PATH", "models/efficientnetv2s_3class_traced_v2.0.0.pt")

# 이미지 설정
IMAGE_SIZE = (384, 384)  # EfficientNetV2-S 입력 크기

# 기본 설정
DEFAULT_CONFIG = {
    # 중앙 크롭 설정
    'use_center_crop': True,
    'center_crop_ratio': 0.8,  # 중앙 80% 사용
    
    # CLAHE 설정 (색상 대비 향상)
    # 현재 상태: False - v1.1.1 실험 결과 성능 향상 없음 (저대비 데이터 3.9%만 존재)
    # TODO: 저대비 원본 이미지 10~20개 추가 후 v1.2.0 재학습 시 True로 변경 예정
    #       목표 저대비 비율: 10~15% 이상
    #       자세한 내용: docs/clahe_implementation_plan.md
    'use_clahe': False,
    'clahe_clip_limit': 3.0,  # 대비 제한값 (높을수록 대비 증가)
    
    # 예측 임계값
    'threshold': 0.6,  # Empty 우선: 0.6 이상이어야 OCCUPIED
    
    # UNKNOWN/INVALID 판정 (3-class 모델용)
    'unknown_threshold': 0.2,  # empty/occupied 확률 차이가 이 값 미만이면 UNKNOWN
    'invalid_threshold': 0.5,  # invalid 확률이 이 값 이상이면 INVALID

    # Torch CPU 설정
    'torch_num_threads': 4,
}

# 클래스 순서 (알파벳)
CLASS_NAMES = ["empty", "invalid", "occupied"]
