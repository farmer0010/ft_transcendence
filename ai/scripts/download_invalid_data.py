"""
INVALID 클래스용 이미지 다운로드 스크립트

COCO 데이터셋에서 사물함과 관련 없는 다양한 카테고리의 이미지를 다운로드합니다.

사용법:
    python scripts/download_invalid_data.py                    # 기본 150장
    python scripts/download_invalid_data.py --count 200        # 200장 다운로드
    python scripts/download_invalid_data.py --output data/train/invalid
"""
import os
import sys
import argparse
import urllib.request
import json
import random
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

COCO_VAL_INFO_URL = "http://images.cocodataset.org/annotations/annotations_trainval2017.zip"
COCO_IMAGE_BASE_URL = "http://images.cocodataset.org/val2017/"

DIVERSE_CATEGORIES = [
    "dog", "cat", "bird", "horse", "cow", "elephant", "bear", "zebra", "giraffe",
    "banana", "apple", "sandwich", "orange", "broccoli", "carrot", "pizza", "donut", "cake",
    "car", "motorcycle", "airplane", "bus", "train", "truck", "boat",
    "frisbee", "skis", "snowboard", "sports ball", "kite", "baseball bat", "tennis racket",
    "umbrella", "handbag", "suitcase", "bottle", "wine glass", "cup", "fork", "knife",
    "laptop", "mouse", "remote", "keyboard", "cell phone", "tv",
    "book", "clock", "vase", "scissors", "teddy bear", "toothbrush"
]

PICSUM_BASE_URL = "https://picsum.photos"


def download_image(url: str, output_path: str, timeout: int = 30) -> bool:
    """단일 이미지 다운로드"""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            with open(output_path, 'wb') as f:
                f.write(response.read())
        return True
    except Exception as e:
        print(f"  Failed: {url} - {e}")
        return False


def download_from_picsum(output_dir: str, count: int = 150, size: int = 640) -> int:
    """
    Lorem Picsum에서 랜덤 이미지 다운로드
    
    다양한 풍경, 사물, 추상 이미지가 포함됨 - 사물함과 무관한 이미지들
    """
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"\nDownloading {count} random images from Picsum...")
    print(f"Output directory: {output_dir}")
    
    downloaded = 0
    failed = 0
    
    def download_single(i):
        seed = random.randint(1, 10000)
        url = f"{PICSUM_BASE_URL}/seed/{seed}/{size}/{size}"
        output_path = os.path.join(output_dir, f"invalid_{i:03d}.jpg")
        
        if os.path.exists(output_path):
            return True
        
        return download_image(url, output_path)
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(download_single, i): i for i in range(1, count + 1)}
        
        for future in as_completed(futures):
            i = futures[future]
            try:
                if future.result():
                    downloaded += 1
                    if downloaded % 10 == 0:
                        print(f"  Progress: {downloaded}/{count}")
                else:
                    failed += 1
            except Exception as e:
                failed += 1
                print(f"  Error downloading image {i}: {e}")
    
    print(f"\nDownload complete: {downloaded} succeeded, {failed} failed")
    return downloaded


def download_from_coco_samples(output_dir: str, count: int = 150) -> int:
    """
    COCO 데이터셋에서 샘플 이미지 다운로드
    
    미리 선별된 COCO 2017 val set 이미지 ID 사용
    """
    os.makedirs(output_dir, exist_ok=True)
    
    sample_image_ids = [
        "000000000139", "000000000285", "000000000632", "000000000724", "000000000776",
        "000000000785", "000000000802", "000000000872", "000000000885", "000000001000",
        "000000001268", "000000001296", "000000001353", "000000001425", "000000001490",
        "000000001503", "000000001532", "000000001584", "000000001675", "000000001761",
        "000000001818", "000000001993", "000000002006", "000000002149", "000000002153",
        "000000002157", "000000002261", "000000002299", "000000002431", "000000002473",
        "000000002532", "000000002587", "000000002592", "000000002685", "000000002923",
        "000000003156", "000000003255", "000000003501", "000000003553", "000000003661",
        "000000003845", "000000003934", "000000004134", "000000004495", "000000004765",
        "000000004795", "000000005001", "000000005037", "000000005193", "000000005477",
        "000000005529", "000000005586", "000000005802", "000000005992", "000000006040",
        "000000006471", "000000006763", "000000006818", "000000006894", "000000007088",
        "000000007278", "000000007386", "000000007574", "000000007816", "000000007888",
        "000000007977", "000000008021", "000000008211", "000000008277", "000000008532",
        "000000008690", "000000008762", "000000008844", "000000009014", "000000009378",
        "000000009448", "000000009483", "000000009590", "000000009769", "000000009891",
        "000000010092", "000000010123", "000000010434", "000000010583", "000000010707",
        "000000010764", "000000010977", "000000011051", "000000011122", "000000011197",
        "000000011511", "000000011615", "000000011760", "000000011813", "000000011881",
        "000000012062", "000000012120", "000000012576", "000000012639", "000000012667",
        "000000012748", "000000013004", "000000013177", "000000013291", "000000013348",
        "000000013546", "000000013597", "000000013659", "000000013729", "000000013774",
        "000000013923", "000000014007", "000000014038", "000000014226", "000000014380",
        "000000014439", "000000014473", "000000014888", "000000015079", "000000015254",
        "000000015278", "000000015335", "000000015338", "000000015440", "000000015497",
        "000000015517", "000000015597", "000000015746", "000000015956", "000000016010",
        "000000016228", "000000016249", "000000016356", "000000016451", "000000016502",
        "000000016598", "000000016892", "000000016958", "000000017029", "000000017115",
        "000000017178", "000000017182", "000000017207", "000000017379", "000000017436",
        "000000017627", "000000017714", "000000017899", "000000017905", "000000018150",
        "000000018380", "000000018519", "000000018575", "000000018737", "000000018770",
        "000000018833", "000000018837", "000000019042", "000000019109", "000000019221",
        "000000019432", "000000019590", "000000019607", "000000019786", "000000019924",
        "000000020059", "000000020107", "000000020247", "000000020333", "000000020571",
    ]
    
    selected_ids = sample_image_ids[:min(count, len(sample_image_ids))]
    
    print(f"\nDownloading {len(selected_ids)} images from COCO 2017 val set...")
    print(f"Output directory: {output_dir}")
    
    downloaded = 0
    failed = 0
    
    def download_single(img_id):
        url = f"{COCO_IMAGE_BASE_URL}{img_id}.jpg"
        output_path = os.path.join(output_dir, f"coco_{img_id}.jpg")
        
        if os.path.exists(output_path):
            return True
        
        return download_image(url, output_path)
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(download_single, img_id): img_id for img_id in selected_ids}
        
        for future in as_completed(futures):
            img_id = futures[future]
            try:
                if future.result():
                    downloaded += 1
                    if downloaded % 10 == 0:
                        print(f"  Progress: {downloaded}/{len(selected_ids)}")
                else:
                    failed += 1
            except Exception as e:
                failed += 1
                print(f"  Error: {img_id} - {e}")
    
    print(f"\nCOCO download complete: {downloaded} succeeded, {failed} failed")
    return downloaded


def main():
    parser = argparse.ArgumentParser(description='Download INVALID class images')
    parser.add_argument('--output', type=str, default='data/train/invalid',
                        help='Output directory')
    parser.add_argument('--count', type=int, default=150,
                        help='Number of images to download')
    parser.add_argument('--source', type=str, default='both', 
                        choices=['picsum', 'coco', 'both'],
                        help='Image source (picsum=random photos, coco=COCO dataset)')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("INVALID Class Image Downloader")
    print("=" * 60)
    print(f"Target count: {args.count}")
    print(f"Output: {args.output}")
    print(f"Source: {args.source}")
    
    total_downloaded = 0
    
    if args.source in ['picsum', 'both']:
        picsum_count = args.count // 2 if args.source == 'both' else args.count
        total_downloaded += download_from_picsum(args.output, picsum_count)
    
    if args.source in ['coco', 'both']:
        coco_count = args.count // 2 if args.source == 'both' else args.count
        total_downloaded += download_from_coco_samples(args.output, coco_count)
    
    output_path = Path(args.output)
    if output_path.exists():
        files = list(output_path.glob("*.jpg")) + list(output_path.glob("*.png"))
        print(f"\n{'=' * 60}")
        print(f"Total images in {args.output}: {len(files)}")
        print("=" * 60)
    
    print("\nDone! You can now add your own images to this directory.")
    print("Recommended: Add images of non-locker scenes (selfies, documents, etc.)")


if __name__ == "__main__":
    main()
