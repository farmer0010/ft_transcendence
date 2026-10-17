#!/usr/bin/env python3
"""
FastAPI ML Inference Server (v4.0) - EfficientNetV2 TorchScript 전용

사물함 점유 상태 판별 API
- EfficientNetV2 CNN 기반 예측
- 384x384 입력 이미지 지원
"""
import time
import uuid
import cv2
import numpy as np
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, File, UploadFile, Query
from pydantic import BaseModel
from typing import Optional

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import MODEL_PATH, DEFAULT_CONFIG
from .classifier import get_classifier, EfficientNetClassifier

# ===== 전역 상태 =====
classifier: EfficientNetClassifier = None

def init_model():
    """모델 초기화"""
    global classifier
    classifier = get_classifier()
    classifier.load_model(MODEL_PATH)
    print(f"Model loaded: EfficientNetV2-S TorchScript ({MODEL_PATH})")


# ===== Lifespan 이벤트 =====
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_model()
    yield
    # Shutdown (필요 시 정리 작업)


# ===== FastAPI 앱 =====
app = FastAPI(
    title="Locker Checker API",
    description="사물함 점유 상태 판별 API (v4.0) - EfficientNetV2 TorchScript 전용",
    version="4.0.0",
    lifespan=lifespan
)


# ===== 응답 스키마 =====
class PredictResponse(BaseModel):
    status: str
    confidence: float
    latencyMs: int
    requestId: str
    probabilities: Optional[dict] = None


class ModelInfoResponse(BaseModel):
    modelType: str
    version: str
    accuracy: Optional[float] = None
    threshold: Optional[float] = None
    inputSize: Optional[list] = None
    emptyRecall: Optional[float] = None


class HealthResponse(BaseModel):
    status: str
    modelLoaded: bool
    modelVersion: Optional[str] = None


# ===== 엔드포인트 =====
@app.get("/health", response_model=HealthResponse)
def health():
    """서버 상태 확인"""
    metadata = classifier.get_metadata() if classifier else {}
    
    return HealthResponse(
        status="ok",
        modelLoaded=classifier is not None and classifier._model is not None,
        modelVersion=metadata.get('version')
    )


@app.get("/model/info", response_model=ModelInfoResponse)
def model_info():
    """모델 정보 조회"""
    if classifier._model is None:
        classifier.load_model()
    
    metadata = classifier.get_metadata()
    
    return ModelInfoResponse(
        modelType="EfficientNetV2-S TorchScript",
        version=metadata.get('version', 'unknown'),
        accuracy=metadata.get('accuracy'),
        threshold=metadata.get('threshold'),
        inputSize=metadata.get('input_size'),
        emptyRecall=metadata.get('empty_recall')
    )


@app.post("/predict", response_model=PredictResponse)
async def predict(
    file: UploadFile = File(...),
    threshold: Optional[float] = Query(
        None,
        description="OCCUPIED 판정 임계값 (0.0~1.0). 높을수록 EMPTY 우선. 기본값: 모델 메타데이터 사용"
    )
):
    """
    이미지에서 사물함 점유 상태 예측
    
    - **file**: 이미지 파일 (jpg, png)
    - **threshold**: OCCUPIED 판정 임계값 (옵션)
    
    Returns:
        - **status**: EMPTY, OCCUPIED, UNKNOWN, 또는 INVALID
        - **confidence**: 예측 확률
        - **probabilities**: 각 클래스별 확률
    """
    start = time.time()
    request_id = str(uuid.uuid4())[:8]
    
    try:
        # 파일 읽기 및 이미지 변환
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        img_np = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img_np is None:
            raise HTTPException(400, "Invalid image file")

        # BGR -> RGB 변환
        image = cv2.cvtColor(img_np, cv2.COLOR_BGR2RGB)
        
        # 예측 (status는 이제 문자열: EMPTY, OCCUPIED, UNKNOWN, INVALID)
        status, confidence, proba = classifier.predict(image, threshold=threshold)
        
        latency_ms = int((time.time() - start) * 1000)
        
        # 로깅
        print(f"[{request_id}] {status} (conf={confidence:.4f}) in {latency_ms}ms")
        
        return PredictResponse(
            status=status,
            confidence=round(confidence, 4),
            latencyMs=latency_ms,
            requestId=request_id,
            probabilities={k: round(v, 4) for k, v in proba.items()}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[{request_id}] Error: {e}")
        raise HTTPException(500, f"Prediction error: {str(e)}")
