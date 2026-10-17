# EfficientNetV2 모델 성능 평가 리포트

**생성일시**: 2026-01-22 19:31:27  
**모델 버전**: 2.0.0  
**모델 파일**: `models/efficientnetv2s_3class_traced_v2.0.0.pt`  
**결정 임계값**: 0.6

---

## 요약

| 데이터셋 | 정확도 |
|:--------:|:------:|
| **Train** | 100.0% |
| **Test** | 100.0% |

---

## Train 데이터셋 결과

### Confusion Matrix

```
                 Predicted
                 EMPTY  INVALID  OCCUPIED
Actual EMPTY       80        0        0
Actual INVALID      0      148        0
Actual OCCUPIED     0        0       77
```

### 성능 지표

| 지표 | EMPTY | INVALID | OCCUPIED |
|------|:-----:|:------:|:--------:|
| **Recall** | 100.0% | 100.0% | 100.0% |
| **Precision** | 100.0% | 100.0% | 100.0% |


---

## Test 데이터셋 결과

### Confusion Matrix

```
                 Predicted
                 EMPTY  INVALID  OCCUPIED
Actual EMPTY       24        0        0
Actual INVALID      0        0        0
Actual OCCUPIED     0        0       18
```

### 성능 지표

| 지표 | EMPTY | INVALID | OCCUPIED |
|------|:-----:|:------:|:--------:|
| **Recall** | 100.0% | 0.0% | 100.0% |
| **Precision** | 100.0% | 0.0% | 100.0% |


---

## 모델 정보

| 항목 | 값 |
|------|:--:|
| **모델 타입** | EfficientNetV2-S |
| **입력 크기** | 384×384 |
| **모델 크기** | 78.8 MB |
| **Empty Weight** | 2.0 |
| **학습 정확도** | 0.9992548435171386 |

