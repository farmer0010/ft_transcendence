# 배포 가이드 (DevOps)

Locker Checker AI 서비스를 프로덕션 환경에 배포하기 위한 가이드입니다.

> AI로 작성된 문서입니다. 부정확한 정보가 포함되어 있을 수 있으나 참고하시기 바랍니다.

## 목차

1. [시스템 요구사항](#시스템-요구사항)
2. [배포 아키텍처](#배포-아키텍처)
3. [FastAPI 서버 배포](#fastapi-서버-배포)
4. [헬스체크 및 모니터링](#헬스체크-및-모니터링)
5. [트러블슈팅](#트러블슈팅)

---

## 시스템 요구사항

### FastAPI 서버 (AI 추론)

| 항목 | 최소 사양 | 권장 사양 |
|------|----------|----------|
| **CPU** | 2 cores | 4+ cores |
| **RAM** | 4GB | 8GB+ |
| **GPU** | 없음 (CPU 추론) | CUDA 지원 GPU (선택) |
| **디스크** | 2GB | 5GB+ |
| **Python** | 3.10+ | 3.11 |


---

## 배포 아키텍처

```
┌──────────────────────────────────────────────────────────┐
│                      Load Balancer                        │
│                    (nginx / traefik)                      │
└──────────────────────────┬───────────────────────────────┘
                           │
                           ▼
             ┌───────────────────────────┐
             │   FastAPI 서버            │
             │   (AI 추론)               │
             │   Port: 8000              │
             └─────────────┬─────────────┘
                           │
                           ▼
             ┌───────────────────────────┐
             │   모델 파일                │
             │   /models/*.pt           │
             └───────────────────────────┘
```

---

## FastAPI 서버 배포

### 방법 1: systemd 서비스 (권장)

**1. 프로젝트 배포**

```bash
# 프로젝트 clone (Git LFS 필수)
git lfs install
git clone git@github.com:42-Gy/ft_cabinet_AI.git /opt/locker_checker
cd /opt/locker_checker

# 가상환경 생성
python3.11 -m venv venv
source venv/bin/activate

# 의존성 설치
pip install --upgrade pip
pip install -r requirements.txt
```

**2. systemd 서비스 파일 생성**

```bash
sudo nano /etc/systemd/system/locker-checker.service
```

```ini
[Unit]
Description=Locker Checker FastAPI Service
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/locker_checker
Environment="PATH=/opt/locker_checker/venv/bin"
ExecStart=/opt/locker_checker/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always
RestartSec=10

# 리소스 제한 (선택)
MemoryLimit=4G
CPUQuota=200%

[Install]
WantedBy=multi-user.target
```

**3. 서비스 시작**

```bash
sudo systemctl daemon-reload
sudo systemctl enable locker-checker
sudo systemctl start locker-checker
sudo systemctl status locker-checker
```

**4. 로그 확인**

```bash
# 실시간 로그
sudo journalctl -u locker-checker -f

# 최근 100줄
sudo journalctl -u locker-checker -n 100
```

---

### 방법 2: Docker 배포

**Dockerfile 생성**

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 시스템 의존성
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드
COPY app/ ./app/
COPY config.py .
COPY models/ ./models/

# 포트 노출
EXPOSE 8000

# 실행
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

**Docker Compose**

```yaml
# docker-compose.yml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./models:/app/models:ro
    environment:
      - MODEL_PATH=/app/models/efficientnetv2s_3class_traced.pt
    restart: always
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          memory: 4G
```

**실행**

```bash
docker-compose up -d
docker-compose logs -f
```

---



## 헬스체크 및 모니터링

### 엔드포인트

| 엔드포인트 | 예상 응답 |
|-----------|----------|
| `GET /health` | `{"status": "healthy"}` |
| `GET /` | `{"message": "Locker Checker API..."}` |

### 헬스체크 스크립트

```bash
#!/bin/bash
# /opt/locker_checker/healthcheck.sh

API_URL="http://localhost:8000"

if curl -sf "$API_URL/health" > /dev/null; then
    echo "[OK] FastAPI is healthy"
else
    echo "[FAIL] FastAPI is down"
    exit 1
fi
```

### 모니터링 지표

**권장 수집 항목:**

- 응답 시간 (latency): `/predict` 엔드포인트
- 요청 수 (request count): 분당 요청 수
- 에러율 (error rate): 4xx, 5xx 응답 비율
- 메모리 사용량: 모델 로딩 후 안정적인지 확인
- CPU 사용량: 이미지 추론 시 스파이크

---

## 환경 변수

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `MODEL_PATH` | 모델 파일 경로 | `models/efficientnetv2s_3class_traced.pt` |

---

## Nginx 리버스 프록시 설정

```nginx
# /etc/nginx/sites-available/locker-checker

upstream fastapi {
    server 127.0.0.1:8000;
    keepalive 32;
}

server {
    listen 80;
    server_name api.example.com;

    # 파일 업로드 제한
    client_max_body_size 50M;

    location / {
        proxy_pass http://fastapi;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 타임아웃 (추론 시간 고려)
        proxy_connect_timeout 60s;
        proxy_read_timeout 120s;
    }

    location /health {
        proxy_pass http://fastapi/health;
        access_log off;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/locker-checker /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## 트러블슈팅

### 모델 파일 누락

**증상**: 서버 시작 시 `Model file not found` 에러

**해결**:
```bash
# Git LFS 파일 다운로드
git lfs pull

# 파일 크기 확인 (80MB+ 여야 정상)
ls -lh models/*.pt
```

### 메모리 부족

**증상**: `Killed` 또는 `OOM` 에러

**해결**:
- 최소 4GB RAM 확보
- `--workers 1`로 워커 수 감소
- swap 메모리 추가

```bash
# swap 4GB 추가
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### 느린 첫 추론

**증상**: 첫 번째 API 호출이 10초 이상 걸림

**원인**: 모델 lazy loading

**해결**: 정상 동작입니다. 이후 요청은 0.1~0.5초 내 응답합니다.

### GPU 사용 안됨

**증상**: CPU만 사용되어 추론이 느림

**해결**:
```bash
# CUDA 설치 확인
nvidia-smi

# PyTorch 설치 (CPU 전용)
pip install --extra-index-url https://download.pytorch.org/whl/cpu torch torchvision

# PyTorch 버전 확인
python -c "import torch; print(torch.__version__)"
```

---

## 배포 체크리스트

- [ ] Git LFS 설치 완료
- [ ] 저장소 clone 및 LFS 파일 pull
- [ ] Python 가상환경 생성
- [ ] 의존성 설치 (`pip install -r requirements.txt`)
- [ ] 모델 파일 존재 확인 (80MB+)
- [ ] FastAPI 서버 실행 테스트
- [ ] 헬스체크 응답 확인
- [ ] systemd 서비스 등록 (또는 Docker)
- [ ] 리버스 프록시 설정 (선택)
- [ ] 방화벽 포트 개방 (8000)

---

## 연락처

배포 관련 문의는 AI 팀에 문의해 주세요.
