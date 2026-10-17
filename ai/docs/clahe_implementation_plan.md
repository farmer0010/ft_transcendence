# CLAHE 적용 계획

## 현재 상태 (2025-12-22)

### 실험 결과

- **v1.1.0** (CLAHE 없음): 85.7% 정확도
- **v1.1.1** (CLAHE 적용): 85.7% 정확도 (동일)
- **결론**: 현재 데이터셋에서는 CLAHE가 성능 향상에 기여하지 못함

### 문제 분석

저대비 이미지(paper001, paper002 등)가 전체 학습 데이터의 **3.9%**밖에 되지 않아, CLAHE의 효과가 나타나지 않음.

| 항목 | 현재 개수 |
|------|----------|
| 저대비 원본 이미지 | 3개 (paper001, paper002, paper003) |
| 증강된 저대비 이미지 | 66개 |
| 전체 occupied 이미지 | 1,694개 |
| **저대비 비율** | **3.9%** ← 너무 낮음 |

### 현재 설정

- 모델: `efficientnetv2s_3class_traced.pt` (CLAHE 없이 학습)
- `use_clahe: False` - CLAHE 비활성화

---

## CLAHE란?

### 개념

**CLAHE (Contrast Limited Adaptive Histogram Equalization)**는 이미지의 명도 대비를 향상시키는 기법입니다.

- 일반 히스토그램 균등화: 전체 이미지에 동일하게 적용 → 과도한 대비
- **CLAHE**: 작은 타일 단위로 적용 + 대비 제한 → 자연스러운 향상

### 동작 방식

1. 이미지를 **LAB 색공간**으로 변환 (L = 밝기, A/B = 색상)
2. **L(밝기) 채널**에만 대비 향상 적용 (색상 보존)
3. 작은 **타일(8×8)** 단위로 지역적 대비 균등화
4. **clip_limit**로 과도한 대비 증가 방지

### 효과적인 경우

| 효과적 | 비효과적/역효과 |
|----------|-------------------|
| 저조도/어두운 이미지 | 이미 대비가 좋은 이미지 |
| 물체와 배경 색이 비슷할 때 | 노이즈가 많은 이미지 (노이즈 증폭) |
| 의료 영상 (X-ray, MRI) | 고대비 이미지 |

---

## 향후 계획

### 1단계: 저대비 데이터 수집 (진행 예정)

**목표**: 저대비 원본 이미지 **10~20개** 추가

수집할 이미지 유형:
- 흰색/밝은 색 종이
- 조명이 강한 환경
- 사물함 색과 유사한 물체

**체크리스트**
- [ ] `config.py`에서 `use_clahe: True`로 변경 후 학습 여부 확인
- [ ] `scripts/train_torch.py` 전처리 흐름이 `config.py` 설정을 따르는지 확인

**예상 효과**:
```
새 원본: 13개 (기존 3 + 신규 10)
→ 증강: 13 × 22 = 286개
→ 비율: 286/1,900 ≈ 15% 
```

### 2단계: CLAHE로 재학습 (데이터 수집 후)

#### 학습 명령어

```bash
# 저대비 데이터가 10~15% 이상일 때 실행
python scripts/train_torch.py \
  --version 2.1.0 \
  --epochs 15 \
  --empty-weight 1.5

# TorchScript 내보내기 (384x384 고정 입력)
python scripts/export_torchscript.py \
  --weights models/efficientnetv2s_3class_v2.1.0.pth \
  --metadata models/efficientnetv2s_3class_v2.1.0_metadata.json
```

#### 예상 개선

- 저대비 비율 15% → CLAHE의 효과가 나타날 것으로 예상
- paper001, paper002 같은 케이스 개선 가능
- 전체 정확도 향상 기대

### 3단계: 적용 (재학습 후)

학습 완료 후 다음 파일 수정:

#### `config.py`

```python
MODEL_PATH = "models/efficientnetv2s_3class_traced.pt"
'use_clahe': True  # CLAHE 활성화
```

#### `scripts/visualize_gradcam.py`

- `TORCH_WEIGHTS_PATH`가 새 `.pth`를 가리키는지 확인

---

## 실행 체크리스트

### 재학습 전 확인사항

- [ ] 저대비 원본 이미지 10개 이상 추가 완료
- [ ] 데이터 증강 실행 완료
- [ ] 저대비 이미지 비율 10% 이상 확인
- [ ] `train_torch.py`에서 CLAHE 전처리가 활성화되었는지 확인

### 재학습 후 확인사항

- [ ] 학습 완료 및 v1.2.0 모델 생성 확인
- [ ] paper001, paper002 테스트 (OCCUPIED로 예측되어야 함)
- [ ] 전체 테스트 세트 정확도 확인 (85.7% 이상)
- [ ] `config.py` 모델 경로 및 `use_clahe` 업데이트
- [ ] `TORCH_WEIGHTS_PATH` 업데이트 (Grad-CAM용 .pth)
- [ ] FastAPI 서버 재시작 및 테스트

---

## 관련 파일

### 코드

- `config.py` - CLAHE 설정
- `app/torch_preprocess.py` - CLAHE 함수 구현
- `scripts/train_torch.py` - 학습 스크립트 (CLAHE 포함)
- `scripts/export_torchscript.py` - TorchScript 내보내기
- `scripts/visualize_gradcam.py` - Grad-CAM 시각화

### 데이터

- `data/train/occupied/paper*.jpg` - 현재 저대비 원본 (3개)
- `data/train_augmented/occupied/paper*.jpg` - 증강 데이터 (66개)

---

## 히스토리

### 2025-12-22: CLAHE 실험 및 롤백

- v1.1.1 학습 (CLAHE 적용, epochs=15, empty-weight=1.5)
- 결과: 85.7% (v1.1.0과 동일)
- 원인: 저대비 데이터 부족 (3.9%)
- 조치: v1.1.0으로 롤백, `use_clahe: False`
- 계획 수립: 저대비 데이터 수집 후 재시도
