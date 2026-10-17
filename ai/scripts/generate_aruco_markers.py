"""
ArUco 마커 생성 스크립트
1번부터 350번까지의 ArUco 마커를 생성합니다.
"""

import cv2
import numpy as np
import os
from pathlib import Path


def generate_aruco_markers(
    start_id: int = 1,
    end_id: int = 350,
    marker_size: int = 200,
    output_dir: str = "aruco_markers",
    dictionary_type: int = cv2.aruco.DICT_4X4_1000
):
    """
    ArUco 마커를 생성하고 이미지 파일로 저장합니다.
    
    Args:
        start_id: 시작 마커 ID (기본값: 1)
        end_id: 종료 마커 ID (기본값: 350)
        marker_size: 마커 이미지 크기 (픽셀, 기본값: 200)
        output_dir: 출력 디렉토리 경로
        dictionary_type: ArUco 사전 타입 (기본값: DICT_4X4_1000)
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    aruco_dict = cv2.aruco.getPredefinedDictionary(dictionary_type)
    
    print(f"ArUco 마커 생성 시작: {start_id}번 ~ {end_id}번")
    print(f"마커 크기: {marker_size}x{marker_size} 픽셀")
    print(f"출력 디렉토리: {output_path.absolute()}")
    print("-" * 50)
    
    generated_count = 0
    
    for marker_id in range(start_id, end_id + 1):
        marker_image = cv2.aruco.generateImageMarker(aruco_dict, marker_id, marker_size)
        
        border_size = 20
        marker_with_border = cv2.copyMakeBorder(
            marker_image,
            border_size, border_size, border_size, border_size,
            cv2.BORDER_CONSTANT,
            value=255
        )
        
        filename = f"aruco_{marker_id:03d}.png"
        filepath = output_path / filename
        
        cv2.imwrite(str(filepath), marker_with_border)
        generated_count += 1
        
        if marker_id % 50 == 0:
            print(f"진행 중... {marker_id}번 마커 생성 완료")
    
    print("-" * 50)
    print(f"생성 완료! 총 {generated_count}개의 마커가 생성되었습니다.")
    print(f"저장 위치: {output_path.absolute()}")


def generate_marker_sheet(
    start_id: int = 1,
    end_id: int = 350,
    markers_per_row: int = 5,
    marker_size: int = 150,
    output_file: str = "aruco_marker_sheet.png",
    dictionary_type: int = cv2.aruco.DICT_4X4_1000
):
    """
    여러 마커를 하나의 시트에 배열하여 저장합니다.
    
    Args:
        start_id: 시작 마커 ID
        end_id: 종료 마커 ID
        markers_per_row: 한 행당 마커 수
        marker_size: 각 마커 크기 (픽셀)
        output_file: 출력 파일명
        dictionary_type: ArUco 사전 타입
    """
    aruco_dict = cv2.aruco.getPredefinedDictionary(dictionary_type)
    
    total_markers = end_id - start_id + 1
    rows = (total_markers + markers_per_row - 1) // markers_per_row
    
    border = 10
    cell_size = marker_size + border * 2
    label_height = 25
    
    sheet_width = cell_size * markers_per_row
    sheet_height = (cell_size + label_height) * rows
    
    sheet = np.ones((sheet_height, sheet_width), dtype=np.uint8) * 255
    
    for idx, marker_id in enumerate(range(start_id, end_id + 1)):
        row = idx // markers_per_row
        col = idx % markers_per_row
        
        x = col * cell_size + border
        y = row * (cell_size + label_height) + border
        
        marker_image = cv2.aruco.generateImageMarker(aruco_dict, marker_id, marker_size)
        
        sheet[y:y + marker_size, x:x + marker_size] = marker_image
        
        label_y = y + marker_size + 18
        cv2.putText(
            sheet, 
            f"ID: {marker_id}", 
            (x + 5, label_y), 
            cv2.FONT_HERSHEY_SIMPLEX, 
            0.5, 
            0, 
            1
        )
    
    cv2.imwrite(output_file, sheet)
    print(f"마커 시트 생성 완료: {output_file}")
    print(f"시트 크기: {sheet_width}x{sheet_height} 픽셀")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="ArUco 마커 생성기")
    parser.add_argument("--start", type=int, default=1, help="시작 마커 ID (기본값: 1)")
    parser.add_argument("--end", type=int, default=350, help="종료 마커 ID (기본값: 350)")
    parser.add_argument("--size", type=int, default=200, help="마커 크기 (픽셀, 기본값: 200)")
    parser.add_argument("--output", type=str, default="aruco_markers", help="출력 디렉토리")
    parser.add_argument("--sheet", action="store_true", help="마커 시트 생성 모드")
    parser.add_argument("--sheet-file", type=str, default="aruco_marker_sheet.png", help="시트 파일명")
    parser.add_argument("--per-row", type=int, default=5, help="시트 모드: 한 행당 마커 수")
    
    args = parser.parse_args()
    
    if args.sheet:
        generate_marker_sheet(
            start_id=args.start,
            end_id=args.end,
            markers_per_row=args.per_row,
            marker_size=args.size,
            output_file=args.sheet_file
        )
    else:
        generate_aruco_markers(
            start_id=args.start,
            end_id=args.end,
            marker_size=args.size,
            output_dir=args.output
        )
