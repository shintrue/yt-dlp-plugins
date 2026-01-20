#!/usr/bin/env python3
# yt-dl: YouTube 다운로더 (Firefox 쿠키 사용)

import subprocess
import os
import sys
import re

def get_urls_from_input():
    """URL 입력받기"""
    print("\n=== YouTube 다운로더 ===")
    print("YouTube URL을 입력하세요 (여러 개는 줄바꿈으로 구분)")
    print("입력 완료 후 빈 줄에서 Enter:\n")

    lines = []
    while True:
        try:
            line = input()
            if line.strip() == "":
                break
            lines.append(line.strip())
        except EOFError:
            break

    # URL 추출
    urls = []
    for line in lines:
        # YouTube URL 패턴
        if 'youtube.com' in line or 'youtu.be' in line:
            urls.append(line)

    return urls

def download_video(url, index, total):
    """단일 영상 다운로드"""
    print(f"\n[{index}/{total}] 다운로드 중...")
    print(f"  URL: {url[:60]}...")

    cmd = [
        "yt-dlp",
        "--cookies-from-browser", "firefox",
        "-f", "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
        "--merge-output-format", "mp4",
        "--no-part",
        "--restrict-filenames",
        "-o", "%(title)s.%(ext)s",
        url
    ]

    result = subprocess.run(cmd)

    if result.returncode != 0:
        print(f"  [오류] 다운로드 실패")
        return False

    print(f"  완료!")
    return True

def main():
    if len(sys.argv) > 1:
        # 명령줄 인자로 URL 전달
        urls = sys.argv[1:]
    else:
        # 대화형 입력
        urls = get_urls_from_input()

    if not urls:
        print("URL이 입력되지 않았습니다.")
        sys.exit(1)

    print(f"\n{len(urls)}개의 URL을 다운로드합니다.")

    success = 0
    for i, url in enumerate(urls, 1):
        if download_video(url, i, len(urls)):
            success += 1

    print(f"\n완료: {success}/{len(urls)} 성공")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n중단되었습니다.")
        sys.exit(0)
