# FastAPI AI Server Dockerfile
# EfficientNetV2-S TorchScript 기반 사물함 점유 분류 서버

FROM python:3.11-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 패키지 설치 (OpenCV 의존성)
RUN apt-get update && apt-get install -y --no-install-recommends \
    # OpenCV 의존성
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY config.py .
COPY app/ ./app/
COPY models/ ./models/

# 환경 변수 설정
ENV PYTHONUNBUFFERED=1
ENV MODEL_PATH=models/efficientnetv2s_3class_traced_v2.0.0.pt

# 포트 노출
EXPOSE 8000

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# 서버 실행
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
