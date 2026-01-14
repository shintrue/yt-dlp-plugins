#!/usr/bin/env python3
# naver-dl: 네이버 프리미엄 콘텐츠 m3u8 다운로더

import subprocess
import os
import sys
import json
import re
import argparse
import platform
from pathlib import Path

DEFAULT_COOKIE_FILE = os.path.expanduser("~/.naver_cookies.txt")

def get_clipboard():
    """클립보드 내용 읽기"""
    if platform.system() == "Darwin":
        result = subprocess.run(["pbpaste"], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout
    elif platform.system() == "Windows":
        result = subprocess.run(["powershell", "-command", "Get-Clipboard"],
                                capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout
    return None

def export_cookies():
    """Firefox에서 쿠키를 추출하여 파일로 저장"""
    print(f"Firefox에서 쿠키를 추출합니다...")
    cmd = [
        "yt-dlp",
        "--cookies-from-browser", "firefox",
        "--cookies", DEFAULT_COOKIE_FILE,
        "--skip-download",
        "https://naver.com/"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if os.path.exists(DEFAULT_COOKIE_FILE):
        size = os.path.getsize(DEFAULT_COOKIE_FILE)
        print(f"쿠키 파일 저장됨: {DEFAULT_COOKIE_FILE} ({size} bytes)")
        return True
    else:
        print("쿠키 추출 실패")
        return False

def import_cookies():
    """쿠키를 클립보드에서 읽어 저장"""
    print("=== 쿠키 가져오기 ===")
    print("쿠키를 클립보드에 복사한 후 Enter를 누르세요...")
    input()

    content = get_clipboard()
    if not content:
        print("클립보드를 읽을 수 없습니다.")
        return False

    print(f"클립보드에서 {len(content)} 바이트를 읽었습니다.")

    # Netscape 쿠키 형식 검증
    if not content.strip().startswith("# Netscape HTTP Cookie File"):
        print("\n경고: Netscape 쿠키 형식이 아닌 것 같습니다.")
        print("계속 저장하시겠습니까? (y/N):", end=" ")
        if input().strip().lower() != 'y':
            return False

    with open(DEFAULT_COOKIE_FILE, 'w', encoding='utf-8') as f:
        f.write(content)
        if not content.endswith('\n'):
            f.write('\n')

    print(f"\n쿠키 파일 저장됨: {DEFAULT_COOKIE_FILE}")
    return True

def download_url(url, index, total, referer, output_dir, cookie_file=None):
    """단일 URL 다운로드"""
    from urllib.parse import urlparse
    parsed = urlparse(url)
    base_name = os.path.splitext(os.path.basename(parsed.path))[0]
    output_file = os.path.join(output_dir, f"download_{index:02d}_{base_name[:8]}.mp4")

    print(f"\n[{index}/{total}] 다운로드 중...")

    cmd = [
        "yt-dlp",
        "--enable-file-urls",
    ]

    if cookie_file and os.path.exists(cookie_file):
        cmd.extend(["--cookies", cookie_file])
    else:
        cmd.extend(["--cookies-from-browser", "firefox"])

    cmd.extend([
        "--referer", referer,
        "--user-agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:146.0) Gecko/20100101 Firefox/146.0",
        "--no-part",
        "--restrict-filenames",
        "-N", "4",
        "-o", output_file,
        url
    ])

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"  [오류] 다운로드 실패")
        return None

    if os.path.exists(output_file):
        return output_file

    pattern = f"download_{index:02d}_{base_name[:8]}*"
    matches = list(Path(output_dir).glob(pattern))
    if matches:
        return str(matches[0])

    return None

def analyze_file(filepath):
    """ffprobe로 파일 분석"""
    if not filepath or not os.path.exists(filepath):
        return None

    file_size = os.path.getsize(filepath)

    # 작은 파일은 텍스트일 가능성
    if file_size < 10000:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read(1000)
                if content.startswith('#EXTM3U') or content.startswith('#EXT'):
                    return {
                        'type': 'text',
                        'is_playlist': True,
                        'size': file_size,
                        'filepath': filepath
                    }
        except:
            pass

    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        filepath
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        return {'type': 'unknown', 'size': file_size, 'filepath': filepath}

    try:
        data = json.loads(result.stdout)
    except:
        return {'type': 'unknown', 'size': file_size, 'filepath': filepath}

    info = {
        'type': 'video',
        'size': file_size,
        'filepath': filepath,
        'width': None,
        'height': None,
        'has_audio': False,
        'duration': None,
        'video_codec': None,
        'audio_codec': None
    }

    for stream in data.get('streams', []):
        codec_type = stream.get('codec_type')
        if codec_type == 'video':
            info['width'] = stream.get('width')
            info['height'] = stream.get('height')
            info['video_codec'] = stream.get('codec_name')
        elif codec_type == 'audio':
            info['has_audio'] = True
            info['audio_codec'] = stream.get('codec_name')

    fmt = data.get('format', {})
    duration = fmt.get('duration')
    if duration:
        info['duration'] = float(duration)

    if info['width'] is None:
        info['type'] = 'audio' if info['has_audio'] else 'unknown'

    return info

def format_size(size_bytes):
    """바이트를 읽기 좋은 형식으로"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f}TB"

def format_duration(seconds):
    """초를 시:분:초 형식으로"""
    if not seconds:
        return "N/A"
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"

def sanitize_filename(name):
    """파일명에 사용할 수 없는 문자 제거"""
    # 파일명에 사용할 수 없는 문자 제거
    invalid_chars = r'[<>:"/\\|?*]'
    name = re.sub(invalid_chars, '', name)
    # 연속 공백 제거
    name = re.sub(r'\s+', ' ', name).strip()
    return name[:100]  # 최대 100자

def process_json_input():
    """JSON 형식 입력 처리 (클립보드에서)"""
    print("\n=== 네이버 프리미엄 m3u8 다운로더 ===")
    print("JSON 데이터를 클립보드에 복사한 후 Enter를 누르세요...")
    input()

    content = get_clipboard()
    if not content:
        print("클립보드를 읽을 수 없습니다.")
        return None

    # JSON 파싱 시도
    try:
        data = json.loads(content.strip())
    except json.JSONDecodeError:
        # JSON이 아니면 기존 URL 방식으로 처리
        return None

    # 필수 필드 확인
    if 'm3u8_list' not in data:
        print("JSON에 'm3u8_list' 필드가 없습니다.")
        return None

    return data

def select_best_video(videos, title):
    """여러 영상 중 보관할 파일 선택"""
    if not videos:
        return None

    # 플레이리스트(텍스트) 파일 자동 삭제
    valid_videos = [v for v in videos if v and v.get('type') == 'video']
    text_files = [v for v in videos if v and v.get('type') == 'text']

    # 텍스트 파일 삭제
    for t in text_files:
        try:
            os.remove(t['filepath'])
            print(f"  삭제: {os.path.basename(t['filepath'])} (플레이리스트)")
        except:
            pass

    if not valid_videos:
        print("유효한 영상 파일이 없습니다.")
        return None

    if len(valid_videos) == 1:
        return valid_videos[0]

    # 중복 확인 (duration, size, height가 모두 같으면 중복)
    def get_signature(v):
        return (
            round(v.get('duration') or 0),
            v.get('size'),
            v.get('height')
        )

    signatures = {}
    for v in valid_videos:
        sig = get_signature(v)
        if sig not in signatures:
            signatures[sig] = []
        signatures[sig].append(v)

    # 중복 파일 제거 (같은 시그니처 중 하나만 남김)
    unique_videos = []
    for sig, vlist in signatures.items():
        unique_videos.append(vlist[0])
        # 중복 파일 삭제
        for v in vlist[1:]:
            try:
                os.remove(v['filepath'])
                print(f"  삭제: {os.path.basename(v['filepath'])} (중복)")
            except:
                pass

    if len(unique_videos) == 1:
        return unique_videos[0]

    # 여러 해상도가 있는 경우 선택
    print("\n" + "=" * 60)
    print("다운로드 결과 - 파일 선택")
    print("=" * 60)

    # 해상도 기준 정렬 (700~1000 적정)
    def sort_key(v):
        h = v.get('height') or 0
        # 700~1000 사이면 우선순위 높음
        if 700 <= h <= 1000:
            return (0, -h)  # 적정 범위 내에서는 높을수록 좋음
        elif h > 1000:
            return (1, h)   # 너무 큰 것은 후순위
        else:
            return (2, -h)  # 너무 작은 것도 후순위

    unique_videos.sort(key=sort_key)

    for i, v in enumerate(unique_videos, 1):
        resolution = f"{v['width']}x{v['height']}" if v.get('width') else "N/A"
        duration = format_duration(v.get('duration'))
        size = format_size(v.get('size', 0))
        audio = "O" if v.get('has_audio') else "X"
        recommended = " (권장)" if i == 1 else ""

        print(f"  [{i}] {resolution} | {duration} | {size} | 소리:{audio}{recommended}")

    print(f"  [0] 모두 삭제")
    print(f"  [a] 모두 보관")

    while True:
        print(f"\n보관할 파일 번호 (1-{len(unique_videos)}, 0=삭제, a=모두):", end=" ")
        choice = input().strip().lower()

        if choice == '0':
            # 모두 삭제
            for v in unique_videos:
                try:
                    os.remove(v['filepath'])
                    print(f"  삭제: {os.path.basename(v['filepath'])}")
                except:
                    pass
            return None

        if choice == 'a':
            # 모두 보관 - 첫 번째만 title로 이름 변경
            return unique_videos[0]

        try:
            idx = int(choice)
            if 1 <= idx <= len(unique_videos):
                selected = unique_videos[idx - 1]
                # 선택되지 않은 파일 삭제
                for i, v in enumerate(unique_videos):
                    if i != idx - 1:
                        try:
                            os.remove(v['filepath'])
                            print(f"  삭제: {os.path.basename(v['filepath'])}")
                        except:
                            pass
                return selected
        except ValueError:
            pass

        print("잘못된 입력입니다.")

def main():
    parser = argparse.ArgumentParser(
        description='네이버 프리미엄 m3u8 다운로더',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  naver-dl                      # JSON 데이터로 다운로드 (클립보드)
  naver-dl --export-cookies     # Firefox에서 쿠키 추출
  naver-dl --import-cookies     # 쿠키 가져오기 (클립보드)
  naver-dl --show-cookies       # 저장된 쿠키 출력

JSON 입력 형식:
{
    "title": "영상 제목",
    "referer": "https://...",
    "m3u8_list": ["https://...m3u8", ...],
    "cookies_netscape": "# Netscape HTTP Cookie File\\n..."
}
        """
    )
    parser.add_argument('--cookies', '-c', metavar='FILE',
                        help='쿠키 파일 경로')
    parser.add_argument('--export-cookies', '-e', action='store_true',
                        help='Firefox에서 쿠키 추출')
    parser.add_argument('--import-cookies', '-i', action='store_true',
                        help='쿠키 가져오기 (클립보드)')
    parser.add_argument('--show-cookies', '-s', action='store_true',
                        help='저장된 쿠키 출력')

    args = parser.parse_args()

    if args.export_cookies:
        export_cookies()
        return

    if args.import_cookies:
        import_cookies()
        return

    if args.show_cookies:
        if os.path.exists(DEFAULT_COOKIE_FILE):
            with open(DEFAULT_COOKIE_FILE, 'r') as f:
                print(f.read())
        else:
            print(f"쿠키 파일이 없습니다: {DEFAULT_COOKIE_FILE}")
        return

    # JSON 입력 처리
    data = process_json_input()

    if not data:
        print("JSON 데이터가 없거나 잘못되었습니다.")
        print("클립보드에 JSON을 복사한 후 다시 시도하세요.")
        sys.exit(1)

    title = data.get('title', 'download')
    referer = data.get('referer', 'https://contents.premium.naver.com/')
    m3u8_list = data.get('m3u8_list', [])
    cookies_netscape = data.get('cookies_netscape')

    print(f"\n제목: {title}")
    print(f"리퍼러: {referer[:60]}...")
    print(f"m3u8 URL: {len(m3u8_list)}개")

    # 쿠키 처리
    cookie_file = args.cookies
    if cookies_netscape:
        # JSON에 쿠키가 포함된 경우 임시 파일로 저장
        cookie_file = DEFAULT_COOKIE_FILE
        with open(cookie_file, 'w', encoding='utf-8') as f:
            f.write(cookies_netscape)
        print(f"쿠키: JSON에서 로드됨")
    elif not cookie_file and os.path.exists(DEFAULT_COOKIE_FILE):
        cookie_file = DEFAULT_COOKIE_FILE
        print(f"쿠키: {cookie_file}")
    else:
        print(f"쿠키: Firefox 브라우저")

    output_dir = os.getcwd()
    print(f"저장 위치: {output_dir}")
    print(f"\n다운로드를 시작합니다...")

    # 다운로드 실행
    downloaded_files = []
    for i, url in enumerate(m3u8_list, 1):
        filepath = download_url(url, i, len(m3u8_list), referer, output_dir, cookie_file)
        downloaded_files.append(filepath)

    # 파일 분석
    print("\n파일 분석 중...")
    results = []
    for filepath in downloaded_files:
        info = analyze_file(filepath)
        results.append(info)

    # 최적 파일 선택
    selected = select_best_video(results, title)

    if selected:
        # 파일명 변경
        safe_title = sanitize_filename(title)
        new_filename = f"{safe_title}.mp4"
        new_filepath = os.path.join(output_dir, new_filename)

        # 동일 파일명이 이미 존재하면 번호 추가
        counter = 1
        while os.path.exists(new_filepath):
            new_filename = f"{safe_title}_{counter}.mp4"
            new_filepath = os.path.join(output_dir, new_filename)
            counter += 1

        try:
            os.rename(selected['filepath'], new_filepath)
            print(f"\n최종 파일: {new_filename}")
            print(f"  해상도: {selected.get('width')}x{selected.get('height')}")
            print(f"  길이: {format_duration(selected.get('duration'))}")
            print(f"  용량: {format_size(selected.get('size', 0))}")
        except Exception as e:
            print(f"파일명 변경 실패: {e}")
            print(f"원본 파일: {selected['filepath']}")

    # patched m3u8 파일 정리
    for f in Path(output_dir).glob("patched_*.m3u8"):
        try:
            os.remove(f)
        except:
            pass

    print("\n완료!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n중단되었습니다.")
        sys.exit(0)
