"""
ArUco 마커 이미지들을 PDF로 합치는 스크립트
"""

import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import argparse


def get_marker_id_from_filename(filename: str) -> int:
    """파일명에서 마커 ID 추출 (예: aruco_001.png -> 1)"""
    name = Path(filename).stem
    id_str = name.split('_')[-1]
    return int(id_str)


def merge_images_to_pdf(
    input_dir: str = "aruco_markers",
    output_file: str = "aruco_markers.pdf",
    markers_per_page: int = 4,
    page_size: tuple = (2480, 3508),
    margin: int = 50
):
    """
    여러 PNG 이미지를 하나의 PDF 파일로 합칩니다.
    
    Args:
        input_dir: 입력 이미지 디렉토리
        output_file: 출력 PDF 파일명
        markers_per_page: 페이지당 마커 수 (기본값: 4 = 2 x 2)
        page_size: 페이지 크기 (width, height) 픽셀
        margin: 페이지 여백 (픽셀)
    """
    input_path = Path(input_dir)
    
    png_files = sorted(input_path.glob("aruco_*.png"))
    
    if not png_files:
        print(f"오류: {input_dir}에서 PNG 파일을 찾을 수 없습니다.")
        return
    
    print(f"총 {len(png_files)}개의 마커 이미지 발견")
    
    cols = int(markers_per_page ** 0.5)
    rows = (markers_per_page + cols - 1) // cols
    
    label_height = 80
    
    available_width = page_size[0] - (2 * margin)
    available_height = page_size[1] - (2 * margin)
    
    cell_width = available_width // cols
    cell_height = available_height // rows
    marker_size = min(cell_width, cell_height - label_height) - 20
    
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
    except:
        font = ImageFont.load_default()
    
    pages = []
    current_page = None
    draw = None
    marker_idx = 0
    
    print(f"페이지 설정: {cols}x{rows} 배열, 마커 크기: {marker_size}px")
    print("-" * 50)
    
    for i, png_file in enumerate(png_files):
        if i % markers_per_page == 0:
            if current_page is not None:
                pages.append(current_page)
            current_page = Image.new('RGB', page_size, 'white')
            draw = ImageDraw.Draw(current_page)
            marker_idx = 0
            page_num = len(pages) + 1
            print(f"페이지 {page_num} 생성 중...")
        
        marker = Image.open(png_file).convert('RGB')
        marker = marker.resize((marker_size, marker_size), Image.Resampling.LANCZOS)
        
        marker_id = get_marker_id_from_filename(str(png_file))
        
        row = marker_idx // cols
        col = marker_idx % cols
        
        x = margin + col * cell_width + (cell_width - marker_size) // 2
        y = margin + row * cell_height + (cell_height - marker_size - label_height) // 2
        
        current_page.paste(marker, (x, y))
        
        label_text = f"ID: {marker_id}"
        bbox = draw.textbbox((0, 0), label_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_x = x + (marker_size - text_width) // 2
        text_y = y + marker_size + 15
        draw.text((text_x, text_y), label_text, fill='black', font=font)
        
        marker_idx += 1
    
    if current_page is not None:
        pages.append(current_page)
    
    if pages:
        pages[0].save(
            output_file,
            save_all=True,
            append_images=pages[1:],
            resolution=300
        )
        print("-" * 50)
        print(f"PDF 생성 완료: {output_file}")
        print(f"총 {len(pages)} 페이지")
    else:
        print("오류: 생성할 페이지가 없습니다.")


def merge_single_per_page(
    input_dir: str = "aruco_markers",
    output_file: str = "aruco_markers_single.pdf",
    page_size: tuple = (2480, 3508)
):
    """
    각 마커를 개별 페이지에 크게 배치합니다.
    """
    input_path = Path(input_dir)
    png_files = sorted(input_path.glob("aruco_*.png"))
    
    if not png_files:
        print(f"오류: {input_dir}에서 PNG 파일을 찾을 수 없습니다.")
        return
    
    print(f"총 {len(png_files)}개의 마커를 개별 페이지로 생성")
    
    pages = []
    marker_size = min(page_size) - 400
    
    for i, png_file in enumerate(png_files):
        page = Image.new('RGB', page_size, 'white')
        marker = Image.open(png_file).convert('RGB')
        marker = marker.resize((marker_size, marker_size), Image.Resampling.LANCZOS)
        
        x = (page_size[0] - marker_size) // 2
        y = (page_size[1] - marker_size) // 2
        
        page.paste(marker, (x, y))
        pages.append(page)
        
        if (i + 1) % 50 == 0:
            print(f"진행 중... {i + 1}/{len(png_files)}")
    
    pages[0].save(
        output_file,
        save_all=True,
        append_images=pages[1:],
        resolution=300
    )
    print(f"PDF 생성 완료: {output_file} ({len(pages)} 페이지)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ArUco 마커 PDF 생성기")
    parser.add_argument("--input", type=str, default="aruco_markers", help="입력 디렉토리")
    parser.add_argument("--output", type=str, default="aruco_markers.pdf", help="출력 PDF 파일명")
    parser.add_argument("--per-page", type=int, default=4, help="페이지당 마커 수 (기본값: 4)")
    parser.add_argument("--single", action="store_true", help="마커당 1페이지 모드")
    
    args = parser.parse_args()
    
    if args.single:
        merge_single_per_page(
            input_dir=args.input,
            output_file=args.output
        )
    else:
        merge_images_to_pdf(
            input_dir=args.input,
            output_file=args.output,
            markers_per_page=args.per_page
        )
