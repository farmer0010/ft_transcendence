# Locker Checker Web Application

사물함 이미지를 업로드하여 상태(EMPTY/INVALID/OCCUPIED)를 예측하는 Spring Boot 웹 애플리케이션입니다.

## 기능

- 이미지 업로드 (드래그 앤 드롭 지원)
- FastAPI 예측 서버와 연동하여 사물함 상태 판별
- 예측 결과 및 신뢰도 시각화
- 업로드된 이미지를 `download/` 폴더에 자동 저장

## 사전 요구사항

- Java 17 이상
- FastAPI 예측 서버 실행 중 (포트 8000)

## 실행 방법

### 1. FastAPI 예측 서버 실행

```bash
cd /root/Projects/locker_checker
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 2. Spring Boot 웹 서버 실행

```bash
cd /root/Projects/locker_checker/webapp
./gradlew bootRun
```

### 3. 브라우저 접속

`http://localhost:8080` 접속 후 이미지를 업로드하면 예측 결과가 표시됩니다.

## 설정

`src/main/resources/application.properties`에서 설정을 변경할 수 있습니다:

| 설정 | 기본값 | 설명 |
|-----|--------|------|
| `server.port` | 8080 | 웹 서버 포트 |
| `prediction.api.url` | http://localhost:8000/predict | 예측 API URL |
| `upload.dir` | ./download | 이미지 저장 경로 |

## 프로젝트 구조

```
webapp/
├── build.gradle                    # Gradle 빌드 설정
├── src/main/java/com/locker/webapp/
│   ├── WebappApplication.java      # 메인 클래스
│   ├── controller/
│   │   └── UploadController.java   # 업로드 컨트롤러
│   └── service/
│       └── PredictionService.java  # 예측 API 연동 서비스
└── src/main/resources/
    ├── application.properties      # 설정 파일
    └── templates/
        └── index.html              # 업로드 페이지
```

## 빌드

```bash
./gradlew build
```

빌드된 JAR 파일은 `build/libs/webapp-1.0.0.jar`에 생성됩니다.

## JAR 파일로 실행

```bash
java -jar build/libs/webapp-1.0.0.jar
```
