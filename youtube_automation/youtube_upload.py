"""
YouTube Data API v3 업로드 모듈
사전 준비:
  1. Google Cloud Console에서 프로젝트 생성
  2. YouTube Data API v3 활성화
  3. OAuth 2.0 클라이언트 ID 생성 → client_secrets.json 다운로드
  4. pip install google-api-python-client google-auth-oauthlib
"""

import os
import json
from pathlib import Path

try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    GOOGLE_LIBS_AVAILABLE = True
except ImportError:
    GOOGLE_LIBS_AVAILABLE = False


SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TOKEN_FILE = "youtube_token.json"
CLIENT_SECRETS = "client_secrets.json"


def get_youtube_service(client_secrets_path: str = CLIENT_SECRETS):
    """OAuth2 인증 후 YouTube 서비스 객체 반환"""
    if not GOOGLE_LIBS_AVAILABLE:
        raise ImportError(
            "Google 라이브러리 설치 필요:\n"
            "pip install google-api-python-client google-auth-oauthlib"
        )

    creds = None
    if Path(TOKEN_FILE).exists():
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(client_secrets_path, SCOPES)
            creds = flow.run_local_server(port=0)
        Path(TOKEN_FILE).write_text(creds.to_json(), encoding="utf-8")

    return build("youtube", "v3", credentials=creds)


def upload_video(
    video_path: str,
    title: str,
    description: str,
    tags: list[str] = None,
    category_id: str = "22",      # 22 = People & Blogs
    privacy: str = "private",     # private / unlisted / public
    thumbnail_path: str = None,
    client_secrets_path: str = CLIENT_SECRETS,
) -> str:
    """
    영상 업로드 후 YouTube video_id 반환
    privacy: 처음엔 'private'으로 올리고 확인 후 공개 권장
    """
    yt = get_youtube_service(client_secrets_path)

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags or [],
            "categoryId": category_id,
            "defaultLanguage": "ko",
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(
        video_path,
        mimetype="video/mp4",
        resumable=True,
        chunksize=10 * 1024 * 1024,  # 10MB 청크
    )

    print(f"[YouTube] 업로드 시작: {Path(video_path).name}")
    request = yt.videos().insert(
        part=",".join(body.keys()),
        body=body,
        media_body=media,
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            pct = int(status.progress() * 100)
            print(f"[YouTube] 업로드 중... {pct}%", end="\r")

    video_id = response["id"]
    print(f"\n[YouTube] 업로드 완료: https://youtube.com/watch?v={video_id}")

    # 썸네일 업로드 (별도 API 호출)
    if thumbnail_path and Path(thumbnail_path).exists():
        yt.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(thumbnail_path),
        ).execute()
        print(f"[YouTube] 썸네일 업로드 완료")

    return video_id


def save_upload_info(video_id: str, metadata: dict, output_dir: str = "output"):
    """업로드 결과를 JSON으로 저장"""
    info = {"video_id": video_id, "url": f"https://youtube.com/watch?v={video_id}", **metadata}
    path = Path(output_dir) / "upload_result.json"
    path.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[YouTube] 업로드 정보 저장: {path}")
    return info


# ── CLI ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="YouTube 영상 업로드")
    parser.add_argument("--video", required=True, help="영상 파일 경로 (mp4)")
    parser.add_argument("--title", required=True, help="영상 제목")
    parser.add_argument("--desc", default="", help="영상 설명")
    parser.add_argument("--tags", nargs="*", default=[], help="태그들")
    parser.add_argument("--thumbnail", default=None, help="썸네일 이미지")
    parser.add_argument("--privacy", default="private", choices=["private", "unlisted", "public"])
    parser.add_argument("--secrets", default=CLIENT_SECRETS, help="client_secrets.json 경로")
    args = parser.parse_args()

    vid = upload_video(
        video_path=args.video,
        title=args.title,
        description=args.desc,
        tags=args.tags,
        thumbnail_path=args.thumbnail,
        privacy=args.privacy,
        client_secrets_path=args.secrets,
    )
    print(f"완료: https://youtube.com/watch?v={vid}")
