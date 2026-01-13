# yt-dlp-plugins

yt-dlp 플러그인 및 다운로더 도구 모음

## 플러그인 목록

| 플러그인 | 설명 | 대상 사이트 |
|---------|------|------------|
| `nvpcon.py` | 네이버 프리미엄 콘텐츠 다운로더 | `contents.premium.naver.com` |

## 도구

| 파일 | 설명 |
|------|------|
| `naver-dl.py` | 네이버 프리미엄 콘텐츠 대화형 다운로더 |

---

## 설치

### yt-dlp 플러그인 설치

**macOS/Linux:**
```bash
mkdir -p ~/.config/yt-dlp/plugins/custom/yt_dlp_plugins/extractor/
cp <plugin>.py ~/.config/yt-dlp/plugins/custom/yt_dlp_plugins/extractor/
```

**Windows:**
```cmd
mkdir %APPDATA%\yt-dlp\plugins\custom\yt_dlp_plugins\extractor\
copy <plugin>.py %APPDATA%\yt-dlp\plugins\custom\yt_dlp_plugins\extractor\
```

---

## 네이버 프리미엄 콘텐츠 (nvpcon.py + naver-dl.py)

### 설치

1. **플러그인 설치:**
```bash
# macOS/Linux
mkdir -p ~/.config/yt-dlp/plugins/naver_fix/yt_dlp_plugins/extractor/
cp nvpcon.py ~/.config/yt-dlp/plugins/naver_fix/yt_dlp_plugins/extractor/

# Windows
mkdir %APPDATA%\yt-dlp\plugins\naver_fix\yt_dlp_plugins\extractor\
copy nvpcon.py %APPDATA%\yt-dlp\plugins\naver_fix\yt_dlp_plugins\extractor\
```

2. **다운로더 스크립트 설치 (선택):**
```bash
# macOS/Linux
cp naver-dl.py ~/naver-dl
chmod +x ~/naver-dl
ln -s ~/naver-dl /usr/local/bin/naver-dl

# Windows
copy naver-dl.py %USERPROFILE%\naver-dl.py
```

### 사용법

**대화형 다운로더:**
```bash
naver-dl
```

**쿠키 관련 옵션:**
```bash
naver-dl --export-cookies     # Firefox에서 쿠키 추출
naver-dl --show-cookies       # 저장된 쿠키 보기 (다른 머신에 복사용)
naver-dl --cookies <file>     # 쿠키 파일로 다운로드
```

### 동작 원리

`nvpcon.py`는 네이버 VOD 서버(`b01-kr-naver-vod.pstatic.net`)의 m3u8 URL을 감지하여:
1. 매니페스트 다운로드
2. 세그먼트 URL에 인증 토큰(`_lsu_sa_`) 추가
3. 패치된 매니페스트로 다운로드 진행

---

## 의존성

- Python 3.x
- yt-dlp
- ffmpeg / ffprobe

## 라이선스

MIT
