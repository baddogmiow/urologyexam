"""Upload a finished video to YouTube via the official Data API v3.

Setup (one-time, per Google account):
1. https://console.cloud.google.com/ -> create a project -> enable "YouTube Data API v3".
2. Create an OAuth 2.0 Client ID (type: Desktop app) -> download the JSON as
   client_secret.json, put it in ai-content-tool/ (or point
   YOUTUBE_CLIENT_SECRET_FILE at it).
3. First run will open a browser for you to log in and grant upload
   permission; a token is cached in ai-content-tool/.youtube_token.json so
   you only do this once.

Note: newly created OAuth clients are limited to 'testing' mode with a
small quota until you submit the project for Google's verification, which
is a real review process, not something this script can bypass.
"""
from __future__ import annotations

from pathlib import Path

from ..config import ROOT_DIR, settings
from .base import PublishResult, Publisher

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TOKEN_FILE = ROOT_DIR / ".youtube_token.json"


class YouTubePublisher(Publisher):
    name = "youtube"

    def __init__(self) -> None:
        self._service = None

    def _get_service(self):
        if self._service is not None:
            return self._service

        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build

        creds = None
        if TOKEN_FILE.exists():
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                secret_file = Path(settings.youtube_client_secret_file)
                if not secret_file.is_absolute():
                    secret_file = ROOT_DIR / secret_file
                if not secret_file.exists():
                    raise FileNotFoundError(
                        f"找不到 OAuth 用戶端金鑰檔案: {secret_file}\n"
                        "請依 youtube.py 檔頭註解的步驟到 Google Cloud Console 建立並下載。"
                    )
                flow = InstalledAppFlow.from_client_secrets_file(str(secret_file), SCOPES)
                creds = flow.run_local_server(port=0)
            TOKEN_FILE.write_text(creds.to_json())

        self._service = build("youtube", "v3", credentials=creds)
        return self._service

    def upload(
        self,
        video_path: Path,
        title: str,
        description: str,
        tags: list[str],
        thumbnail_path: Path | None = None,
    ) -> PublishResult:
        from googleapiclient.http import MediaFileUpload

        service = self._get_service()

        body = {
            "snippet": {
                "title": title[:100],
                "description": description[:5000],
                "tags": tags[:500],
                "categoryId": "27",  # Education
            },
            "status": {
                "privacyStatus": settings.youtube_default_privacy,
                "selfDeclaredMadeForKids": False,
            },
        }

        media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True, mimetype="video/mp4")
        request = service.videos().insert(part="snippet,status", body=body, media_body=media)

        response = None
        while response is None:
            status, response = request.next_chunk()

        video_id = response["id"]

        if thumbnail_path and thumbnail_path.exists():
            from googleapiclient.errors import HttpError

            try:
                service.thumbnails().set(
                    videoId=video_id,
                    media_body=MediaFileUpload(str(thumbnail_path)),
                ).execute()
            except HttpError as exc:
                # Most common cause: the channel isn't phone-verified yet -
                # https://www.youtube.com/verify. The video itself already
                # uploaded successfully at this point, so don't let a
                # thumbnail failure hide that from the caller.
                print(
                    f"警告: 影片已上傳成功,但縮圖設定失敗 ({exc.status_code if hasattr(exc, 'status_code') else exc})。"
                    "常見原因是頻道尚未完成手機驗證,請到 https://www.youtube.com/verify 驗證後"
                    "自行到 YouTube Studio 補上縮圖。"
                )

        return PublishResult(
            platform=self.name,
            remote_id=video_id,
            url=f"https://youtu.be/{video_id}",
        )
