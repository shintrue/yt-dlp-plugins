#!/usr/bin/env python3
# naver-dl: 네이버 프리미엄 콘텐츠 m3u8 다운로더

import subprocess
import os
import sys
import json
import re
import argparse
from pathlib import Path

DEFAULT_COOKIE_FILE = os.path.expanduser("~/.naver_cookies.txt")

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
        print(f"\n이 파일을 다른 머신에 복사하여 사용할 수 있습니다:")
        print(f"  naver-dl --cookies {DEFAULT_COOKIE_FILE}")
        return True
    else:
        print("쿠키 추출 실패")
        return False

def import_cookies():
    """쿠키 텍스트를 붙여넣어 파일로 저장"""
    print("=== 쿠키 가져오기 ===")
    print("다른 머신에서 'naver-dl --show-cookies'로 출력한 내용을 붙여넣으세요.")
    print("입력 완료 후 빈 줄에서 Enter를 누르세요:\n")

    lines = []
    while True:
        try:
            line = input()
            if line.strip() == "":
                # 빈 줄이 연속 2번이면 종료
                if lines and lines[-1] == "":
                    lines.pop()
                    break
                lines.append(line)
            else:
                lines.append(line)
        except EOFError:
            break

    if not lines:
        print("입력된 내용이 없습니다.")
        return False

    content = "\n".join(lines)

    # Netscape 쿠키 형식 검증
    if not content.strip().startswith("# Netscape HTTP Cookie File"):
        print("\n경고: Netscape 쿠키 형식이 아닌 것 같습니다.")
        print("계속 저장하시겠습니까? (y/N):", end=" ")
        answer = input().strip().lower()
        if answer != 'y':
            print("취소되었습니다.")
            return False

    # 파일로 저장
    try:
        with open(DEFAULT_COOKIE_FILE, 'w', encoding='utf-8') as f:
            f.write(content)
            if not content.endswith('\n'):
                f.write('\n')

        size = os.path.getsize(DEFAULT_COOKIE_FILE)
        print(f"\n쿠키 파일 저장됨: {DEFAULT_COOKIE_FILE} ({size} bytes)")
        print("이제 'naver-dl'을 실행하면 이 쿠키를 자동으로 사용합니다.")
        return True
    except Exception as e:
        print(f"저장 실패: {e}")
        return False

def get_urls_from_input():
    """대화형으로 URL 입력받기"""
    print("\n=== 네이버 프리미엄 m3u8 다운로더 ===")
    print("m3u8 URL을 입력하세요 (여러 개는 줄바꿈 또는 | 로 구분)")
    print("입력 완료 후 빈 줄에서 Enter를 누르세요:\n")

    lines = []
    while True:
        try:
            line = input()
            if line.strip() == "":
                break
            lines.append(line)
        except EOFError:
            break

    # 모든 입력을 합쳐서 파싱
    full_input = "\n".join(lines)

    # | 또는 줄바꿈으로 분리
    urls = re.split(r'[\|\n]+', full_input)
    urls = [u.strip() for u in urls if u.strip() and u.strip().startswith('http')]

    return urls

def get_referer():
    """리퍼러 URL 입력받기"""
    print("\n리퍼러 URL을 입력하세요 (선택사항, Enter로 건너뛰기):")
    referer = input().strip()
    return referer if referer else "https://contents.premium.naver.com/"

def get_output_dir():
    """출력 디렉토리 입력받기"""
    print(f"\n저장 디렉토리 (Enter = 현재 디렉토리: {os.getcwd()}):")
    output_dir = input().strip()
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        return output_dir
    return os.getcwd()

def download_url(url, index, total, referer, output_dir, cookie_file=None):
    """단일 URL 다운로드"""
    # URL에서 파일명 추출
    from urllib.parse import urlparse
    parsed = urlparse(url)
    base_name = os.path.splitext(os.path.basename(parsed.path))[0]
    output_file = os.path.join(output_dir, f"download_{index:02d}_{base_name[:8]}.mp4")

    print(f"\n[{index}/{total}] 다운로드 중: {base_name[:30]}...")

    cmd = [
        "yt-dlp",
        "-v",
        "--enable-file-urls",
    ]

    # 쿠키 옵션
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
        if "ERROR" in result.stderr:
            error_lines = [l for l in result.stderr.split('\n') if 'ERROR' in l]
            for e in error_lines[:3]:
                print(f"    {e}")
        return None

    # 실제 생성된 파일 찾기
    if os.path.exists(output_file):
        return output_file

    # yt-dlp가 다른 이름으로 저장했을 수 있음
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
    if file_size < 10000:  # 10KB 미만
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

    # ffprobe로 분석
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
        return {
            'type': 'unknown',
            'size': file_size,
            'filepath': filepath
        }

    try:
        data = json.loads(result.stdout)
    except:
        return {
            'type': 'unknown',
            'size': file_size,
            'filepath': filepath
        }

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

    # 스트림 분석
    streams = data.get('streams', [])
    for stream in streams:
        codec_type = stream.get('codec_type')
        if codec_type == 'video':
            info['width'] = stream.get('width')
            info['height'] = stream.get('height')
            info['video_codec'] = stream.get('codec_name')
        elif codec_type == 'audio':
            info['has_audio'] = True
            info['audio_codec'] = stream.get('codec_name')

    # 포맷 정보
    fmt = data.get('format', {})
    duration = fmt.get('duration')
    if duration:
        info['duration'] = float(duration)

    # 비디오 스트림이 없으면 타입 변경
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

def print_results(results):
    """분석 결과 출력"""
    print("\n" + "=" * 60)
    print("다운로드 결과 분석")
    print("=" * 60)

    deletable = []
    videos = []

    for i, info in enumerate(results, 1):
        if info is None:
            print(f"\n[{i}] 다운로드 실패")
            continue

        filepath = info['filepath']
        filename = os.path.basename(filepath)

        print(f"\n[{i}] {filename}")
        print(f"    경로: {filepath}")
        print(f"    용량: {format_size(info['size'])}")

        if info['type'] == 'text' and info.get('is_playlist'):
            print(f"    타입: 텍스트 (m3u8 플레이리스트)")
            print(f"    상태: 삭제 가능")
            deletable.append(filepath)
        elif info['type'] == 'video':
            resolution = f"{info['width']}x{info['height']}" if info['width'] else "N/A"
            audio_status = "있음" if info['has_audio'] else "없음"
            print(f"    타입: 영상")
            print(f"    해상도: {resolution}")
            print(f"    길이: {format_duration(info['duration'])}")
            print(f"    소리: {audio_status}")
            print(f"    코덱: {info['video_codec'] or 'N/A'}" + (f" / {info['audio_codec']}" if info['audio_codec'] else ""))
            videos.append(info)
        elif info['type'] == 'audio':
            print(f"    타입: 오디오")
            print(f"    길이: {format_duration(info['duration'])}")
            print(f"    코덱: {info['audio_codec'] or 'N/A'}")
        else:
            print(f"    타입: 알 수 없음")

    # 삭제 가능한 파일 처리
    if deletable:
        print("\n" + "-" * 60)
        print(f"삭제 가능한 파일 {len(deletable)}개 발견")
        print("삭제하시겠습니까? (y/N):", end=" ")
        answer = input().strip().lower()
        if answer == 'y':
            for f in deletable:
                try:
                    os.remove(f)
                    print(f"  삭제됨: {os.path.basename(f)}")
                except Exception as e:
                    print(f"  삭제 실패: {os.path.basename(f)} - {e}")

    # 요약
    print("\n" + "=" * 60)
    print("요약")
    print("=" * 60)
    print(f"총 {len(results)}개 URL 처리")
    print(f"  - 영상: {len(videos)}개")
    print(f"  - 삭제 가능: {len(deletable)}개")

    if videos:
        total_size = sum(v['size'] for v in videos)
        print(f"  - 총 영상 용량: {format_size(total_size)}")

def main():
    parser = argparse.ArgumentParser(
        description='네이버 프리미엄 m3u8 다운로더',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  naver-dl                      # 대화형 모드 (Firefox 쿠키 사용)
  naver-dl --cookies cookie.txt # 쿠키 파일 사용
  naver-dl --export-cookies     # Firefox에서 쿠키 추출하여 저장
  naver-dl --show-cookies       # 저장된 쿠키 파일 내용 출력 (복사용)
  naver-dl --import-cookies     # 다른 머신의 쿠키를 붙여넣어 저장
        """
    )
    parser.add_argument('--cookies', '-c', metavar='FILE',
                        help='쿠키 파일 경로 (Netscape 형식)')
    parser.add_argument('--export-cookies', '-e', action='store_true',
                        help=f'Firefox에서 쿠키를 추출하여 {DEFAULT_COOKIE_FILE}에 저장')
    parser.add_argument('--import-cookies', '-i', action='store_true',
                        help='다른 머신의 쿠키를 붙여넣어 저장')
    parser.add_argument('--show-cookies', '-s', action='store_true',
                        help='저장된 쿠키 파일 내용을 출력 (다른 머신에 복사용)')

    args = parser.parse_args()

    # 쿠키 내보내기 모드
    if args.export_cookies:
        export_cookies()
        return

    # 쿠키 가져오기 모드
    if args.import_cookies:
        import_cookies()
        return

    # 쿠키 보기 모드
    if args.show_cookies:
        cookie_file = args.cookies or DEFAULT_COOKIE_FILE
        if os.path.exists(cookie_file):
            print(f"=== 쿠키 파일: {cookie_file} ===")
            print("아래 내용을 복사하여 다른 머신의 같은 경로에 저장하세요:\n")
            with open(cookie_file, 'r') as f:
                print(f.read())
        else:
            print(f"쿠키 파일이 없습니다: {cookie_file}")
            print(f"먼저 'naver-dl --export-cookies'로 쿠키를 추출하세요.")
        return

    # URL 입력
    urls = get_urls_from_input()

    if not urls:
        print("URL이 입력되지 않았습니다.")
        sys.exit(1)

    print(f"\n{len(urls)}개의 URL을 발견했습니다:")
    for i, url in enumerate(urls, 1):
        # URL 미리보기 (긴 경우 축약)
        display_url = url[:80] + "..." if len(url) > 80 else url
        print(f"  {i}. {display_url}")

    # 리퍼러 입력
    referer = get_referer()

    # 출력 디렉토리
    output_dir = get_output_dir()

    # 쿠키 설정 (우선순위: 명령줄 옵션 > 기본 쿠키 파일 > Firefox)
    cookie_file = args.cookies
    if not cookie_file and os.path.exists(DEFAULT_COOKIE_FILE):
        cookie_file = DEFAULT_COOKIE_FILE
    cookie_source = f"파일: {cookie_file}" if cookie_file else "Firefox 브라우저"

    print(f"\n설정:")
    print(f"  - 리퍼러: {referer}")
    print(f"  - 저장 위치: {output_dir}")
    print(f"  - 쿠키: {cookie_source}")
    print(f"\n다운로드를 시작합니다...")

    # 다운로드 실행
    downloaded_files = []
    for i, url in enumerate(urls, 1):
        filepath = download_url(url, i, len(urls), referer, output_dir, cookie_file)
        downloaded_files.append(filepath)

    # 파일 분석
    print("\n파일 분석 중...")
    results = []
    for filepath in downloaded_files:
        info = analyze_file(filepath)
        results.append(info)

    # 결과 출력
    print_results(results)

    # patched m3u8 파일 정리
    patched_files = list(Path(output_dir).glob("patched_*.m3u8"))
    if patched_files:
        print(f"\n임시 패치 파일 {len(patched_files)}개 삭제 중...")
        for f in patched_files:
            try:
                os.remove(f)
            except:
                pass

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n중단되었습니다.")
        sys.exit(0)
