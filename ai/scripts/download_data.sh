#!/bin/bash

# Google Drive 파일 다운로드 스크립트
# 사용법: ./scripts/download_data.sh [FILE_ID]

# .env 파일이 있으면 로드
if [ -f .env ]; then
    # 주석 제외하고 export
    export $(grep -v '^#' .env | xargs)
fi

DEFAULT_FILE_ID="YOUR_FILE_ID_HERE_OR_IN_ENV"
OUTPUT_FILE="dataset.zip"
DEST_DIR="data"

# 1. 커맨드라인 인자 -> 2. 환경변수 -> 3. 기본값 순으로 설정
FILE_ID=${1:-${GOOGLE_DRIVE_FILE_ID:-$DEFAULT_FILE_ID}}

if [ "$FILE_ID" = "YOUR_FILE_ID_HERE_OR_IN_ENV" ]; then
    echo "Error: FILE_ID가 설정되지 않았습니다."
    echo "사용법: $0 <GOOGLE_DRIVE_FILE_ID>"
    echo "또는 .env 파일에 GOOGLE_DRIVE_FILE_ID를 설정하세요."
    exit 1
fi


echo "Downloading dataset (ID: $FILE_ID)..."

# gdown 설치 확인 및 자동 설치
if ! command -v gdown &> /dev/null; then
    echo "gdown이 설치되어 있지 않습니다. 지금 설치합니다..."
    pip install gdown
fi

# gdown을 사용하여 다운로드
# 기존 파일이 있으면 덮어쓰지 않고, 다운로드 실패 시 에러 처리
if [ -f "$OUTPUT_FILE" ]; then
    rm "$OUTPUT_FILE"
fi

# gdown으로 다운로드 (fuzzy 옵션으로 추출 문제 해결)
gdown --id "$FILE_ID" -O "$OUTPUT_FILE"

# 다운로드 성공 여부 확인
if [ ! -f "$OUTPUT_FILE" ]; then
    echo "Error: 파일 다운로드에 실패했습니다."
    exit 1
fi

# 파일 크기가 너무 작으면(예: 에러 메시지 HTML 등) 경고
FILE_SIZE=$(stat -c%s "$OUTPUT_FILE")
if [ "$FILE_SIZE" -lt 10000 ]; then
    echo "Warning: 다운로드된 파일이 너무 작습니다 ($FILE_SIZE bytes). 올바른 파일이 아닐 수 있습니다."
    head -n 5 "$OUTPUT_FILE"
fi

echo "Unzipping..."
mkdir -p $DEST_DIR

# zip 파일 압축 해제
unzip -o "$OUTPUT_FILE"

echo "Cleaning up..."
rm "$OUTPUT_FILE"

echo "Done! Data is ready in $DEST_DIR"
