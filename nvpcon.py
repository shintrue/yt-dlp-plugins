# aaa.py (v3: 세그먼트 경로 처리 강화)

import re
import os
from urllib.parse import urlparse, parse_qs, urljoin

# 기존 GenericIE 추출기를 가져옵니다.
from yt_dlp.extractor.generic import GenericIE
from yt_dlp.utils import ExtractorError

print('[DEBUG] Naver Premium Patcher (v3 - Robust Path) is running!')

_original_real_extract = GenericIE._real_extract

def _new_real_extract(self, url):
    if 'b01-kr-naver-vod.pstatic.net' not in url:
        return _original_real_extract(self, url)

    print(f'[DEBUG] Patching URL: {url}')
    
    parsed_path = urlparse(url).path
    video_id = os.path.splitext(os.path.basename(parsed_path))[0]
    
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    lsu_sa_token = query_params.get('_lsu_sa_', [None])[0]

    if not lsu_sa_token:
        raise ExtractorError('URL에서 _lsu_sa_ 토큰을 찾을 수 없습니다.', expected=True)

    # 1. 원본 매니페스트 다운로드
    manifest_content = self._download_webpage(
        url, video_id, note='Downloading M3U8 manifest')

    # 2. 매니페스트 내용 수정 (urljoin 사용으로 경로 문제 해결)
    def build_full_url(match):
        path = match.group(1).strip()
        
        # 이미 완전한 URL인 경우
        if path.startswith(('http://', 'https://')):
            full_path = path
        else:
            # urljoin을 사용하여 상대 경로를 절대 경로로 안전하게 변환
            # url: 원본 m3u8의 URL (Base URL 역할)
            full_path = urljoin(url, path)
        
        # 쿼리 파라미터(? 또는 &) 처리 및 토큰 추가
        # 이미 토큰이 있는지 확인하여 중복 방지
        if '_lsu_sa_=' in full_path:
            return full_path
            
        separator = '&' if '?' in full_path else '?'
        return f"{full_path}{separator}_lsu_sa_={lsu_sa_token}"

    modified_manifest = re.sub(
        r'^(?!#)(.+\.(ts|key|mp4|m3u8).*)$', build_full_url, manifest_content, flags=re.MULTILINE)

    # 3. 로컬 파일로 저장
    filename = f"patched_{video_id}.m3u8"
    abs_path = os.path.abspath(filename)
    
    with open(abs_path, 'w', encoding='utf-8') as f:
        f.write(modified_manifest)

    print(f'[DEBUG] Saved patched manifest to: {abs_path}')

    # 4. yt-dlp에게 file:// URL 전달
    file_url = f'file://{abs_path}'

    return {
        'id': video_id,
        'title': video_id,
        'formats': [{
            'url': file_url,
            'protocol': 'm3u8_native',
            'ext': 'mp4',
        }],
    }

GenericIE._real_extract = _new_real_extract
