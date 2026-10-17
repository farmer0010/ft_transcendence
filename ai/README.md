# Locker Checker

이 디렉터리는 42-Gy/ft_cabinet_AI 저장소의 코드를 기반으로 한다.

사물함 점유 상태를 판별하는 딥러닝 기반 이미지 분류 시스템입니다

## 개요

EfficientNetV2-S 모델을 사용하여 사물함 이미지를 분석하고, EMPTY / INVALID / OCCUPIED 3가지 상태를 판별합니다.

## 기술 스택

| 구분 | 기술 |
|-----|------|
| **ML 모델** | EfficientNetV2-S (PyTorch + TorchScript) |
| **API 서버** | FastAPI + Uvicorn |
| **테스트 UI** | Spring Boot 3.4.1 (Thymeleaf) - 개발/테스트용 |
| **시각화** | Grad-CAM (PyTorch) |
| **전처리** | OpenCV, Center Crop (80%) |

---

## 디렉토리 구조

```
locker_checker/
├── config.py                     # 프로젝트 설정 (모델 경로, 임계값 등)
├── app/                          # FastAPI 서버
│   ├── main.py                   # API 엔드포인트
│   ├── classifier.py             # TorchScript 분류기
│   └── preprocess.py             # 전처리 유틸리티 (크롭, CLAHE)
├── webapp/                       # Spring Boot 웹앱 (테스트/개발 도구)
│   ├── src/main/java/com/locker/webapp/
│   │   ├── controller/           # 업로드 컨트롤러
│   │   └── service/              # FastAPI 호출 서비스
│   └── src/main/resources/
│       └── templates/            # Thymeleaf UI
├── models/                       # 학습된 모델
│   ├── efficientnetv2s_3class_traced.pt
│   └── efficientnetv2s_3class_traced_metadata.json
├── scripts/                      # 학습/분석 스크립트
│   ├── train_torch.py            # 모델 학습
│   ├── export_torchscript.py     # TorchScript 내보내기
│   ├── evaluate_model.py         # 모델 성능 평가
│   ├── predict.py                # 이미지 예측
│   ├── visualize_gradcam.py      # Grad-CAM 시각화
│   └── augment_data.py           # 데이터 증강
├── docs/                         # 프로젝트 문서
│   └── clahe_implementation_plan.md  # CLAHE 적용 계획
├── data/                         # 학습/테스트 데이터 (git 제외)
│   ├── train/
│   │   ├── empty/                # 빈 사물함
│   │   ├── invalid/              # 무효 이미지
│   │   └── occupied/             # 물건 있는 사물함
│   ├── train_augmented/          # 증강 데이터 (22배)
│   ├── test/                     # 테스트 데이터
│   └── visualizations/gradcam/   # Grad-CAM 결과
├── requirements.txt
└── README.md
```

---

## 빠른 시작

### 1. FastAPI 서버 실행

```bash
# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# (선택) NVIDIA RTX 50 시리즈(Blackwell) 사용 시
# pip install --pre --index-url https://download.pytorch.org/whl/nightly/cu128 torch torchvision

# 서버 실행
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 2. Spring Boot 웹앱 실행

```bash
cd webapp
./gradlew bootRun  # Windows: gradlew.bat bootRun
```

웹 브라우저에서 `http://localhost:8080` 접속

### 3. 헬스체크

```bash
# FastAPI 서버
curl http://localhost:8000/health
# {"status": "healthy"}

# Spring Boot 웹앱
curl http://localhost:8080/actuator/health
# {"status": "UP"}
```

---

## API 사용법

### POST /predict

이미지 파일을 업로드하여 사물함 점유 상태 예측

**Request:**
```bash
curl -X POST http://localhost:8000/predict \
  -F "file=@data/test/occupied/not_empty100.jpeg"
```

**Query Parameters (Optional):**
- `threshold`: `float` (0.0~1.0). `OCCUPIED`로 판정할 임계값. 높을수록 빈 사물함으로 더 보수적으로 판정함. (기본값: `0.6`)

**Response Schema:**

| 필드명 | 타입 | 설명 |
|-------|------|------|
| `status` | `string` | 판별 결과 상태 (`EMPTY`, `OCCUPIED`, `INVALID`, `UNKNOWN`) |
| `confidence` | `float` | 결과에 대한 신뢰도 (0.0 ~ 1.0) |
| `latencyMs` | `int` | 서버측 처리 시간 (ms) |
| `requestId` | `string` | 개별 요청 추적을 위한 고유 ID |
| `probabilities` | `object` | 각 클래스별 세부 확률 (empty, invalid, occupied) |

**Response Example:**
```json
{
  "status": "OCCUPIED",
  "confidence": 0.8997,
  "latencyMs": 15,
  "requestId": "a1b2c3d4",
  "probabilities": {
    "empty": 0.02,
    "invalid": 0.08,
    "occupied": 0.90
  }
}
```

**Response Status Cases:**

1. **`EMPTY` (정상)**: 빈 사물함으로 판정됨
   - `occupied` 확률이 임계값(0.6) 이하이며, `empty` 확률이 높은 경우
2. **`OCCUPIED` (정상)**: 사물함 내 물건 존재함
   - `occupied` 확률이 임계값(0.6)을 초과하는 경우
3. **`INVALID` (무효)**: 분석 불가능한 이미지
   - 이미지가 너무 어둡거나, 흔들렸거나, 사물함 형태가 아닌 경우 (`invalid` 확률 > 0.5)
4. **`UNKNOWN` (불확실)**: 판별 결과가 모호함
   - `empty`와 `occupied` 확률 차이가 작아(0.2 미만) 확신할 수 없는 경우

**Error Responses:**

- **400 Bad Request**: 유효하지 않은 이미지 파일이 업로드된 경우
- **422 Unprocessable Entity**: 필수 파라미터(`file`)가 누락된 경우
- **500 Internal Server Error**: 서버 내부 오류 또는 모델 처리 중 예외 발생

---

## 현재 모델 (v2.1.0)

### 성능

| 항목 | 값 |
|------|---|
| **모델** | EfficientNetV2-S (PyTorch) |
| **전체 정확도** | 98.7% |
| **EMPTY 정확도** | 100% |
| **INVALID 정확도** | 97.4% |
| **OCCUPIED 정확도** | 98.8% |
| **이미지 크기** | 384×384 |
| **학습 데이터** | 2,140개 (증강 후) |

### 전처리 파이프라인

```
원본 이미지 → 중앙 80% 크롭 → 384×384 리사이즈 → EfficientNetV2 정규화 → 예측
```

### 임계값 (Threshold)

- **기본**: 0.6 (EMPTY 우선 - 빈 사물함을 잘 감지)
- 설정 파일: `config.py`

```python
DEFAULT_CONFIG = {
    'threshold': 0.6,  # 0.6 이상이어야 OCCUPIED
    'use_center_crop': True,
    'center_crop_ratio': 0.8,
    'use_clahe': False  # 현재 미사용
}
```

---

## 스크립트 사용법

### 모델 학습

```bash
# 기본 학습 (10 epochs, empty-weight 2.0)
python scripts/train_torch.py --version 2.0.0 --epochs 10 --empty-weight 2.0

# TorchScript 내보내기
python scripts/export_torchscript.py --weights models/efficientnetv2s_3class_v2.0.0.pth --metadata models/efficientnetv2s_3class_v2.0.0_metadata.json
```

### Grad-CAM 시각화

모델이 이미지의 어느 부분을 보고 판단했는지 시각화

```bash
# 단일 이미지
python scripts/visualize_gradcam.py data/test/occupied/not_empty100.jpeg

# 여러 이미지 비교
python scripts/visualize_gradcam.py img1.jpg img2.jpg img3.jpg

```

**출력 위치:** `data/visualizations/gradcam/`

### 데이터 증강

```bash
python scripts/augment_data.py
# 입력: data/train/
# 출력: data/train_augmented/ (원본의 22배)
```

**증강 기법 (22종):**
- 회전 (±10°)
- 좌우 반전
- 밝기/대비/감마 조정
- 그림자 효과 (수직/수평/랜덤)
- 그라데이션 (좌/우/상단)
- 노이즈 추가
- 복합 증강 (4종)

---

## 알려진 제한사항

### 저대비 이미지 문제

| 이미지 | 정답 | 예측 | 원인 |
|--------|------|------|------|
| paper001.jpg | OCCUPIED | EMPTY ❌ | 흰 종이 ↔ 흰 사물함 구분 실패 |
| paper002.jpg | OCCUPIED | EMPTY ❌ | 저대비 (3.9% 학습 데이터 부족) |

**해결 계획:**
1. 저대비 원본 이미지 10~20개 추가 수집
2. 목표 저대비 비율: 10~15% 이상
3. v1.2.0 재학습 (CLAHE 적용)
4. **자세한 내용**: [`docs/clahe_implementation_plan.md`](docs/clahe_implementation_plan.md)

---

## 웹앱 (Spring Boot) - 테스트/개발 도구

> **주의**: 이 웹앱은 **프로덕션용이 아닌** 테스트 및 개발 도구입니다.  
> FastAPI 서버에 이미지를 쉽게 전달하고 테스트하기 위한 간단한 인터페이스입니다.

### 목적

1. **개발 편의성**: 브라우저에서 직접 이미지 업로드 및 테스트
2. **데이터 수집**: 업로드된 이미지를 `download/`에 자동 저장
3. **API 통합 예시**: 다른 시스템에서 FastAPI를 호출하는 방법 참고용
4. **팀원 테스트**: AI 모델을 직접 코딩 없이 테스트 가능

### 주요 기능

```
사용자 → 이미지 업로드 (웹 UI)
      → Spring Boot 서버
      → FastAPI /predict 호출
      → 결과 표시 (EMPTY/OCCUPIED)
      → 이미지 저장 (download/)
```

### 빠른 실행

```bash
cd webapp
./gradlew bootRun
```

웹 브라우저: `http://localhost:8080`

### 설정

`webapp/src/main/resources/application.properties`:
```properties
# FastAPI 서버 주소 (로컬/원격 변경 가능)
prediction.api.url=http://localhost:8000/predict

# 업로드 이미지 저장 위치 (서버 실행 위치 기준)
upload.dir=./download
```

### ngrok으로 외부 공유

로컬 환경에서 실행 중인 웹앱을 외부에서 접근 가능하도록 공유할 수 있습니다:

```bash
# ngrok 설치 (Ubuntu)
curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list
sudo apt update && sudo apt install ngrok

# 웹앱 포트 공개 (8080)
ngrok http 8080
```

ngrok 실행 후 제공되는 `https://xxxx.ngrok.io` URL을 팀원들과 공유하면 원격에서도 테스트 가능합니다.

**주의**: FastAPI 서버(8000)도 함께 실행되어야 합니다.

### API 통합 예시

실제 서비스에서 이미지를 FastAPI로 전달하려면:

**Java/Spring 예시** (이 웹앱과 동일):
```java
// 1. MultipartFile을 RestTemplate으로 전송
MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
body.add("file", new FileSystemResource(imageFile));

ResponseEntity<PredictionResponse> response = restTemplate.postForEntity(
    "http://fastapi-server:8000/predict",
    new HttpEntity<>(body, headers),
    PredictionResponse.class
);
```

**Python 예시**:
```python
import requests

with open('image.jpg', 'rb') as f:
    files = {'file': f}
    response = requests.post('http://localhost:8000/predict', files=files)
    result = response.json()
    print(result['status'])  # EMPTY / INVALID / OCCUPIED / UNKNOWN
```

**cURL 예시**:
```bash
curl -X POST http://localhost:8000/predict \
  -F "file=@image.jpg"
```

---

## 환경 변수

| 변수명 | 설명 | 기본값 |
|-------|------|--------|
| `MODEL_PATH` | 모델 파일 경로 | `models/efficientnetv2s_3class_traced.pt` |

```bash
# 다른 모델 사용
MODEL_PATH=models/efficientnetv2s_3class_traced.pt uvicorn app.main:app
```

---

## Requirements

### Python (FastAPI)

```
fastapi==0.115.6
uvicorn[standard]==0.34.0
python-multipart==0.0.20
torch==2.2.2
torchvision==0.17.2
opencv-python-headless==4.10.0.84
numpy==1.26.4
Pillow==11.0.0
```

### Java (Spring Boot)

```
Spring Boot 3.4.1
Java 17+
Gradle 8.x
```

---

## 데이터셋 관리

### Git 제외 항목

```gitignore
# 학습 데이터 (Git 제외, Google Drive로 공유)
data/train/
data/train_augmented/

# 테스트 데이터 (현재는 Git 포함)
# data/test/

# 모델 파일은 일반 파일로 추적 (gitignore 제외하지 않음)

# 기타
venv/
```

### 모델 파일 관리

`.pt` 모델 파일은 일반 Git 파일로 버전 관리됩니다(Git LFS 미사용):

- **포함**: `models/*.pt`, `models/*_metadata.json`

**새 모델 추가 방법:**
```bash
git add models/newmodel.pt
git commit -m "Add new model v1.3.0"
git push
```

### Google Drive 공유 (학습 데이터)

대용량 학습 데이터는 Git이 아닌 Google Drive로 공유:

1. 관리자가 `data/train/` 압축 후 업로드
2. 팀원이 다운로드 스크립트 실행:
   ```bash
   ./scripts/download_data.sh [GOOGLE_DRIVE_FILE_ID]
   ```

---

## 개발 히스토리

### v2.1.0 (현재)

- **INVALID 클래스 분류 추가**: EMPTY, OCCUPIED 외에 식별 불가능한 이미지를 위한 INVALID 클래스 추가 (총 3개 클래스)
- **NVIDIA Blackwell(5000번대) 지원**: 최신 GPU 환경에서의 학습 및 추론 호환성을 위해 PyTorch 2.x 기반으로 엔진 전환
- **성능**: 
  - **정확도**: 98.7% (검증 데이터셋 기준)
  - **추론 속도**: 약 15ms (Intel i7 CPU 기준)
- **모델 정보**: 
  - 경로: `models/efficientnetv2s_3class_v2.1.0.pth`
  - 아키텍처: EfficientNetV2-S (3-class)
- **학습 환경**: CUDA 12.1, cuDNN 8.x 상위 호환 지원
- **향후 계획**: v2.2.0에서 저대비(Low-Contrast) 이미지 데이터셋 보강 및 CLAHE 최적화 적용 예정

### v1.1.1 (2025-12-22) - CLAHE 실험 및 롤백

- **실험**: CLAHE 전처리 추가하여 저대비 이미지 개선 시도
- **결과**: 정확도 변화 없음 (85.7% → 85.7%)
- **원인**: 저대비 데이터 비율 3.9%로 부족
- **조치**: v1.1.0으로 롤백, 향후 재학습 계획 수립

### v1.1.0

- EfficientNetV2-S 기반
- 정확도: 95.84%
- 중앙 크롭 80% 전처리
- Empty-weight: 1.5x (빈 사물함 우선 감지)

---

## 라이선스

MIT License

---

## 기여

이슈 및 PR은 언제든 환영합니다!

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request
