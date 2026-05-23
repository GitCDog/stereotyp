#!/usr/bin/env python3
"""
Lädt ein Video als YouTube Short hoch.

Verwendung:
  python youtube_poster.py --story 42
  python youtube_poster.py --story 42 --video path/to/video.mp4
"""

import argparse
import logging
import os
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def _build_youtube_client():
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    import google.auth.transport.requests

    client_id = os.getenv("YOUTUBE_CLIENT_ID")
    client_secret = os.getenv("YOUTUBE_CLIENT_SECRET")
    refresh_token = os.getenv("YOUTUBE_REFRESH_TOKEN")

    if not all([client_id, client_secret, refresh_token]):
        raise ValueError("YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET oder YOUTUBE_REFRESH_TOKEN fehlen in .env")

    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=["https://www.googleapis.com/auth/youtube.upload"],
    )
    request = google.auth.transport.requests.Request()
    creds.refresh(request)

    return build("youtube", "v3", credentials=creds)


def upload_short(video_path: Path, title: str, description: str, tags: list[str] = None) -> str:
    """Lädt Video als YouTube Short hoch. Gibt video_id zurück."""
    from googleapiclient.http import MediaFileUpload

    youtube = _build_youtube_client()

    short_title = f"{title} #Shorts"
    short_description = f"{description}\n\n#Shorts"

    body = {
        "snippet": {
            "title": short_title[:100],
            "description": short_description[:5000],
            "tags": (tags or []) + ["Shorts", "Deutschland", "Stereotypen", "Humor"],
            "categoryId": "22",
            "defaultLanguage": "de",
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(str(video_path), mimetype="video/mp4", resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            logger.info(f"[*] YouTube Upload: {int(status.progress() * 100)}%")

    video_id = response["id"]
    logger.info(f"[+] YouTube Short live: https://youtube.com/shorts/{video_id}")
    return video_id


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    parser = argparse.ArgumentParser()
    parser.add_argument("--story", required=True, help="Story-Nummer")
    parser.add_argument("--video", default=None, help="Pfad zur MP4-Datei (optional)")
    args = parser.parse_args()

    import input_reader as ir

    input_file = "1_input/1_input_file.txt"
    row = ir.find_row(args.story, input_file)
    if not row:
        print(f"[!] Story #{args.story} nicht gefunden")
        return

    nr = str(int(row["nr"]))
    nr4 = f"{int(nr):04d}"
    stereotyp = row["stereotyp"].strip()

    if args.video:
        video_path = Path(args.video)
    else:
        output = Path("output")
        used = Path("output/0_used")
        candidates = list(output.glob(f"{nr4}*.mp4")) + list(used.glob(f"{nr4}*.mp4"))
        if not candidates:
            print(f"[!] Kein MP4 für #{nr} gefunden")
            return
        video_path = candidates[0]

    txt_files = list(Path("1_input").glob(f"{nr4}_*.txt"))
    description = txt_files[0].read_text(encoding="utf-8").strip() if txt_files else stereotyp

    captions_file = Path("output/captions.json")
    tags = []
    if captions_file.exists():
        import json
        captions = json.loads(captions_file.read_text(encoding="utf-8"))
        cap = captions.get(nr) or captions.get(nr4)
        if cap:
            tags = cap.get("hashtags", [])

    print(f"[*] Upload: #{nr} {stereotyp} → {video_path.name}")
    video_id = upload_short(video_path, title=stereotyp, description=description, tags=tags)

    ir.update_field(nr, "youtube_post", "X", input_file)
    print(f"[+] YouTube: https://youtube.com/shorts/{video_id}")
    print(f"[+] youtube_post=X gesetzt für #{nr}")


if __name__ == "__main__":
    main()
