#!/usr/bin/env python3
"""
Agent 5a: Postet Stereotypen-Videos auf Instagram via Graph API.

Liest das nächste ungepostete Video aus der CSV,
lädt es über Cloudinary hoch und postet es als Reel.

Für GitHub Actions: liest/schreibt CSV direkt via GitHub API.
Lokal: liest/schreibt lokale Datei.

Verwendung:
  python instagram_poster.py
"""

import os
import sys
import csv
import io
import json
import time
import random
import logging
import requests
from pathlib import Path
from datetime import datetime

import yaml
from dotenv import load_dotenv
import cloudinary
import cloudinary.api
import cloudinary.uploader

try:
    from github import Github
    GITHUB_AVAILABLE = True
except ImportError:
    GITHUB_AVAILABLE = False

try:
    load_dotenv()
except Exception:
    pass

import ssl
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
ssl._create_default_https_context = ssl._create_unverified_context


def _nr_str(nr) -> str:
    return f"{int(str(nr).strip()):04d}"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def load_config(config_path: str = "config.yaml") -> dict:
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


class InstagramPoster:
    """Postet Stereotypen-Reels auf Instagram."""

    def __init__(self, config: dict, dry_run: bool = False):
        self.config = config
        self.dry_run = dry_run
        self.access_token = os.getenv("INSTAGRAM_ACCESS_TOKEN")
        self.recipient_id = os.getenv("INSTAGRAM_RECIPIENT_ID")
        self.cloudinary_cloud = os.getenv("CLOUDINARY_CLOUD_NAME")
        self.cloudinary_key = os.getenv("CLOUDINARY_API_KEY")
        self.cloudinary_secret = os.getenv("CLOUDINARY_API_SECRET")
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.github_repo_name = os.getenv("GITHUB_REPO")
        self.use_github = GITHUB_AVAILABLE and bool(self.github_token) and bool(self.github_repo_name)

        if not self.access_token:
            raise ValueError("INSTAGRAM_ACCESS_TOKEN fehlt in .env")
        if not self.recipient_id:
            raise ValueError("INSTAGRAM_RECIPIENT_ID fehlt in .env")
        if not self.cloudinary_cloud:
            raise ValueError("CLOUDINARY_CLOUD_NAME fehlt in .env")

        cloudinary.config(
            cloud_name=self.cloudinary_cloud,
            api_key=self.cloudinary_key,
            api_secret=self.cloudinary_secret,
            secure=True,
        )

        self.github = None
        if self.use_github:
            try:
                self.github = Github(self.github_token, verify=False)
                self.github.get_repo(self.github_repo_name)
                logger.info(f"[+] GitHub: {self.github_repo_name}")
            except Exception as e:
                logger.warning(f"[!] GitHub nicht verfügbar: {e}")
                self.use_github = False

        logger.info("[+] InstagramPoster initialisiert")

    def read_input_csv(self) -> list[dict]:
        """Lese CSV von GitHub (CI) oder lokal."""
        if self.use_github:
            return self._read_csv_github()
        return self._read_csv_local()

    def _read_csv_github(self) -> list[dict]:
        repo = self.github.get_repo(self.github_repo_name)
        file = repo.get_contents("1_orchestrator/1_input/1_input_file.txt")
        content = file.decoded_content.decode("utf-8")
        reader = csv.DictReader(io.StringIO(content))
        return [r for r in reader if r.get("nr", "").strip()]

    def _read_csv_local(self) -> list[dict]:
        import input_reader as ir
        return ir.read_rows(self.config["output"]["input_file"])

    def find_next_to_post(self, rows: list[dict], story_nr: str | None = None) -> dict | None:
        """Finde die nächste zu postende Story.

        Reihenfolge:
        1. story_nr (CLI / STORY_NR env) – gezielter Aufruf
        2. 0_reihenfolge.txt – manuelle Reihenfolge (erste ungepostete Zeile)
        3. Chronologisch – erste Zeile mit status_video=X und insta_post leer
        """
        row_by_nr = {str(r.get("nr", "")).strip(): r for r in rows}

        if story_nr:
            row = row_by_nr.get(str(story_nr).strip())
            if row and row.get("status_video") == "X" and not row.get("insta_post", "").strip():
                return row
            return None

        # 0_reihenfolge.txt lesen
        reihenfolge_path = Path(__file__).parent / "1_input" / "0_reihenfolge.txt"
        if reihenfolge_path.exists():
            lines = [l.strip() for l in reihenfolge_path.read_text(encoding="utf-8").splitlines()]
            nrs = [l for l in lines if l and l.isdigit()]
            if nrs:
                for nr in nrs:
                    row = row_by_nr.get(nr)
                    if row and row.get("status_video") == "X" and not row.get("insta_post", "").strip():
                        logger.info(f"[+] Reihenfolge-Datei: nächste Story = #{nr}")
                        return row

        # Fallback: chronologisch
        for row in rows:
            if row.get("status_video") == "X" and not row.get("insta_post", "").strip():
                return row
        return None

    def upload_to_cloudinary(self, video_path: Path) -> str:
        """Lade Video zu Cloudinary und gib URL zurück."""
        logger.info(f"[*] Cloudinary Upload: {video_path.name}...")
        result = cloudinary.uploader.upload(
            str(video_path),
            resource_type="video",
            folder="stereotypen",
            public_id=video_path.stem,
            overwrite=True,
        )
        url = result.get("secure_url")
        logger.info(f"[+] Cloudinary URL: {url}")
        return url

    def delete_from_cloudinary(self, public_id: str):
        try:
            cloudinary.api.delete_resources([public_id], resource_type="video")
            logger.info(f"[+] Cloudinary: {public_id} gelöscht")
        except Exception as e:
            logger.warning(f"[!] Cloudinary-Löschung fehlgeschlagen: {e}")

    def build_caption(self, row: dict) -> str:
        """Erstelle Instagram-Caption – aus captions.json oder Fallback-Template."""
        nr = str(row.get("nr", "")).strip()
        stereotyp = row.get("stereotyp", "").strip()

        # Primär: captions.json
        captions_path = Path(self.config["output"]["output_dir"]) / "captions.json"
        if captions_path.exists():
            try:
                with open(captions_path, encoding="utf-8") as f:
                    captions = json.load(f)
                if nr in captions and captions[nr].get("caption"):
                    return captions[nr]["caption"]
            except Exception:
                pass

        # Fallback: Template aus config.yaml
        ns = _nr_str(nr)
        story_intro = ""
        for p in Path(self.config["output"]["stories_dir"]).glob(f"{ns}_*.txt"):
            lines = p.read_text(encoding="utf-8").strip().split("\n")
            if lines:
                story_intro = lines[0][:100]
            break

        hashtags = " ".join(f"#{h}" for h in self.config["instagram"]["hashtags"])
        return self.config["instagram"]["caption_template"].format(
            stereotyp=stereotyp,
            story_intro=story_intro,
            hashtags=hashtags,
        )

    def post_reel(self, video_url: str, caption: str) -> str | None:
        """Zweistufiger Instagram Reel-Upload."""
        # Schritt 1: Container erstellen
        logger.info("[*] Instagram: Container erstellen...")
        container_url = f"https://graph.instagram.com/v18.0/{self.recipient_id}/media"
        container_payload = {
            "access_token": self.access_token,
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
        }
        resp = requests.post(container_url, json=container_payload, timeout=30)
        if resp.status_code != 200:
            logger.error(f"[-] Container-Fehler {resp.status_code}: {resp.text[:300]}")
            return None

        creation_id = resp.json().get("id")
        logger.info(f"[+] Container ID: {creation_id}")

        # Schritt 2: Auf Verarbeitung warten
        logger.info("[*] Warte auf Instagram-Verarbeitung...")
        for attempt in range(12):
            time.sleep(10)
            status_resp = requests.get(
                f"https://graph.instagram.com/v18.0/{creation_id}",
                params={"fields": "status", "access_token": self.access_token},
                timeout=30,
            )
            if status_resp.status_code == 200:
                status = status_resp.json().get("status")
                logger.info(f"[*] Status: {status} ({attempt + 1}/12)")
                if status == "FINISHED":
                    break

        # Schritt 3: Veröffentlichen
        logger.info("[*] Instagram: Veröffentlichen...")
        publish_url = f"https://graph.instagram.com/v18.0/{self.recipient_id}/media_publish"
        publish_resp = requests.post(
            publish_url,
            json={"access_token": self.access_token, "creation_id": creation_id},
            timeout=30,
        )
        if publish_resp.status_code != 200:
            logger.error(f"[-] Publish-Fehler {publish_resp.status_code}: {publish_resp.text[:300]}")
            return None

        post_id = publish_resp.json().get("id")
        logger.info(f"[+] Gepostet! Post-ID: {post_id}")
        return post_id

    def find_on_cloudinary(self, nr) -> tuple[str, str] | tuple[None, None]:
        """Suche nach bereits hochgeladenem Video auf Cloudinary. Gibt (url, public_id) zurück."""
        ns = _nr_str(nr)
        try:
            result = cloudinary.api.resource(f"stereotypen/{ns}", resource_type="video")
            url = result.get("secure_url")
            public_id = result.get("public_id")
            logger.info(f"[+] Cloudinary: Video gefunden: {url}")
            return url, public_id
        except Exception:
            pass
        # Breiteren Scan: alle Videos im Ordner mit Nummer-Prefix
        try:
            resources = cloudinary.api.resources(
                type="upload", resource_type="video",
                prefix=f"stereotypen/{ns}", max_results=10
            )
            items = resources.get("resources", [])
            if items:
                url = items[0]["secure_url"]
                public_id = items[0]["public_id"]
                logger.info(f"[+] Cloudinary Scan: {public_id}")
                return url, public_id
        except Exception as e:
            logger.warning(f"[!] Cloudinary Scan fehlgeschlagen: {e}")
        return None, None

    def mark_posted(self, row: dict, post_id: str, public_id: str):
        """Markiere Story als gepostet in CSV + posted_videos.json."""
        nr = row["nr"].strip()

        if self.use_github:
            self._update_csv_github(row, nr)
        else:
            import input_reader as ir
            ir.update_field(nr, "insta_post", "X", self.config["output"]["input_file"])

        self._log_posted_video(row, post_id)

        if public_id:
            self.delete_from_cloudinary(public_id)

        logger.info(f"[+] Story #{nr} als gepostet markiert | Post-ID: {post_id}")

    def _update_csv_github(self, row: dict, nr: int):
        try:
            repo = self.github.get_repo(self.github_repo_name)
            file_path = "1_orchestrator/1_input/1_input_file.txt"
            file = repo.get_contents(file_path)
            content = file.decoded_content.decode("utf-8")
            rows = list(csv.DictReader(io.StringIO(content)))
            for r in rows:
                if r.get("nr", "").strip() == str(nr):
                    r["insta_post"] = "X"
                    break
            output = io.StringIO()
            fieldnames = list(rows[0].keys())
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
            repo.update_file(
                file_path,
                f"[AUTO] Story #{nr} auf Instagram gepostet",
                output.getvalue(),
                file.sha,
            )
            logger.info(f"[+] GitHub CSV aktualisiert")
        except Exception as e:
            logger.error(f"[-] GitHub CSV-Update fehlgeschlagen: {e}")

    def _log_posted_video(self, row: dict, post_id: str):
        """Schreibt Post-ID + Metadaten in posted_videos.json (lokal) und auf GitHub."""
        entry = {
            "nr": row.get("nr", "").strip(),
            "stereotyp": row.get("stereotyp", "").strip(),
            "post_id": post_id,
            "posted_at": datetime.now().isoformat(),
        }

        # Immer lokal schreiben
        local_path = Path(self.config["output"]["output_dir"]) / "posted_videos.json"
        try:
            data = json.loads(local_path.read_text(encoding="utf-8")) if local_path.exists() else {"videos": []}
            data["videos"].append(entry)
            local_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            logger.info(f"[+] posted_videos.json lokal aktualisiert (Post-ID: {post_id})")
        except Exception as e:
            logger.error(f"[-] posted_videos.json lokal fehlgeschlagen: {e}")

        # Zusätzlich auf GitHub schreiben (GitHub Actions)
        if not self.use_github:
            return
        try:
            repo = self.github.get_repo(self.github_repo_name)
            file_path = "1_orchestrator/posted_videos.json"
            try:
                file = repo.get_contents(file_path)
                gh_data = json.loads(file.decoded_content.decode("utf-8"))
                sha = file.sha
            except Exception:
                gh_data = {"videos": []}
                sha = None

            gh_data["videos"].append(entry)
            content = json.dumps(gh_data, indent=2, ensure_ascii=False)
            if sha:
                repo.update_file(file_path, f"[AUTO] posted_videos.json – #{entry['nr']}", content, sha)
            else:
                repo.create_file(file_path, "[AUTO] posted_videos.json erstellt", content)
            logger.info("[+] posted_videos.json auf GitHub aktualisiert")
        except Exception as e:
            logger.error(f"[-] posted_videos.json GitHub fehlgeschlagen: {e}")

    def run(self):
        logger.info("=" * 60)
        logger.info("STEREOTYPEN – INSTAGRAM POSTER")
        logger.info("=" * 60)

        # Nächste Story finden
        story_nr = os.getenv("STORY_NR", "").strip() or None
        rows = self.read_input_csv()
        row = self.find_next_to_post(rows, story_nr)
        if not row:
            if story_nr:
                logger.error(f"[-] Story #{story_nr} nicht gefunden oder bereits gepostet")
            else:
                logger.info("[+] Keine ungeposteten Videos verfügbar")
            return False

        nr = row["nr"].strip()
        stereotyp = row["stereotyp"].strip()
        logger.info(f"\n[*] Nächste Story: #{nr} – {stereotyp}")

        # Video-Datei lokal suchen
        import input_reader as ir
        safe = ir.safe_name(stereotyp)
        ns = _nr_str(nr)
        output_dir = Path(self.config["output"]["output_dir"])
        video_path = output_dir / f"{ns}_{safe}.mp4"

        if not video_path.exists():
            for p in output_dir.glob(f"{ns}_*.mp4"):
                video_path = p
                break

        public_id = None
        if video_path.exists():
            # Lokal vorhanden → hochladen
            video_url = self.upload_to_cloudinary(video_path)
            public_id = f"stereotypen/{video_path.stem}"
        else:
            # Kein lokales Video → auf Cloudinary suchen (GitHub Actions)
            logger.info(f"[*] Kein lokales Video – suche auf Cloudinary...")
            video_url, public_id = self.find_on_cloudinary(nr)
            if not video_url:
                logger.error(f"[-] Video für #{nr} weder lokal noch auf Cloudinary gefunden")
                return False

        # Caption
        caption = self.build_caption(row)
        logger.info(f"[*] Caption:\n{caption}\n")

        if self.dry_run:
            logger.info("=" * 60)
            logger.info("[DRY-RUN] Würde jetzt posten:")
            logger.info(f"  Story:    #{nr} – {stereotyp}")
            logger.info(f"  Video:    {video_url}")
            logger.info(f"  Caption:  {caption[:80]}...")
            logger.info("[DRY-RUN] Kein Upload. Abgebrochen vor post_reel().")
            logger.info("=" * 60)
            return True

        # Instagram Post
        post_id = self.post_reel(video_url, caption)
        if not post_id:
            logger.error("[-] Posting fehlgeschlagen")
            return False

        # Als gepostet markieren
        self.mark_posted(row, post_id, public_id)

        logger.info("=" * 60)
        logger.info(f"[SUCCESS] '{stereotyp}' auf Instagram gepostet")
        logger.info(f"[SUCCESS] Post-ID: {post_id}")
        logger.info("=" * 60)
        return True


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Nur simulieren, nicht posten")
    args = parser.parse_args()

    try:
        config = load_config()
        poster = InstagramPoster(config, dry_run=args.dry_run)
        success = poster.run()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"[-] Fataler Fehler: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
