"""YouTube publishing via the free YouTube Data API v3 quota.

Setup (once, free):
  1. https://console.cloud.google.com -> new project -> enable "YouTube Data API v3"
  2. Credentials -> OAuth client ID (Desktop app) -> download as client_secrets.json
  3. pip install google-api-python-client google-auth-oauthlib
Then `openreel publish` opens a browser once; the token is cached after that.
"""
from __future__ import annotations

import os
import pickle

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def get_service(client_secrets: str = "client_secrets.json",
                token_path: str = "token.pickle"):
    try:
        from googleapiclient.discovery import build
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
    except ImportError as exc:
        raise RuntimeError(
            "pip install google-api-python-client google-auth-oauthlib") from exc

    creds = None
    if os.path.exists(token_path):
        with open(token_path, "rb") as fh:
            creds = pickle.load(fh)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(client_secrets):
                raise RuntimeError(
                    f"{client_secrets} not found — create a free OAuth client in "
                    "Google Cloud Console (see module docstring)")
            flow = InstalledAppFlow.from_client_secrets_file(client_secrets, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "wb") as fh:
            pickle.dump(creds, fh)
    return build("youtube", "v3", credentials=creds)


def upload_video(service, video_path: str, title: str, description: str,
                 tags: list[str] | None = None, privacy: str = "private",
                 category_id: str = "22",  # People & Blogs
                 thumbnail_path: str | None = None) -> str:
    """Upload; returns the YouTube video ID."""
    from googleapiclient.http import MediaFileUpload

    body = {"snippet": {"title": title[:100], "description": description[:5000],
                        "tags": (tags or [])[:500], "categoryId": category_id},
            "status": {"privacyStatus": privacy,
                       "selfDeclaredMadeForKids": False}}
    media = MediaFileUpload(video_path, chunksize=8 * 1024 * 1024, resumable=True)
    request = service.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        status, response = request.next_chunk()
    video_id = response["id"]
    if thumbnail_path and os.path.exists(thumbnail_path):
        service.thumbnails().set(videoId=video_id,
                                 media_body=MediaFileUpload(thumbnail_path)).execute()
    return video_id
