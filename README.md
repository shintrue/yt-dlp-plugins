# yt-dlp-naver-plugin

네이버 프리미엄 콘텐츠 m3u8 다운로더 및 yt-dlp 플러그인

## 구성 파일

| 파일 | 설명 |
|------|------|
| `nvpcon.py` | yt-dlp 플러그인 (GenericIE 패치) |
| `naver-dl.py` | 대화형 다운로더 스크립트 |

## 설치

### 1. yt-dlp 플러그인 설치

**macOS/Linux:**
```bash
mkdir -p ~/.config/yt-dlp/plugins/naver_fix/yt_dlp_plugins/extractor/
cp nvpcon.py ~/.config/yt-dlp/plugins/naver_fix/yt_dlp_plugins/extractor/
```

**Windows:**
```cmd
mkdir %APPDATA%\yt-dlp\plugins\naver_fix\yt_dlp_plugins\extractor\
copy nvpcon.py %APPDATA%\yt-dlp\plugins\naver_fix\yt_dlp_plugins\extractor\
```

### 2. 다운로더 스크립트 설치

**macOS/Linux:**
```bash
cp naver-dl.py ~/naver-dl
chmod +x ~/naver-dl
ln -s ~/naver-dl /usr/local/bin/naver-dl  # 또는 /opt/homebrew/bin/
```

**Windows:**
```cmd
copy naver-dl.py %USERPROFILE%\naver-dl.py
```

## 사용법

### 기본 사용 (대화형)
```bash
naver-dl
```

### 쿠키 관련 옵션
```bash
# Firefox에서 쿠키 추출
naver-dl --export-cookies

# 저장된 쿠키 보기 (다른 머신에 복사용)
naver-dl --show-cookies

# 쿠키 파일로 다운로드
naver-dl --cookies ~/.naver_cookies.txt
```

## 의존성

- Python 3.x
- yt-dlp
- ffmpeg / ffprobe

## 동작 원리

`nvpcon.py` 플러그인은 네이버 VOD 서버(`b01-kr-naver-vod.pstatic.net`)의 m3u8 URL을 감지하여:
1. 매니페스트 다운로드
2. 세그먼트 URL에 인증 토큰(`_lsu_sa_`) 추가
3. 패치된 매니페스트로 다운로드 진행
