#!/usr/bin/env python3
"""
Agent 4: Erstellt MP4-Videos aus Bild + Audio via ffmpeg.

Verwendung:
  python generate_videos.py --story 1     # Video für Story #1
  python generate_videos.py --all         # Alle bereitstehenden Videos
"""

import sys
import os
import argparse
import logging
import subprocess
import shutil
import tempfile
from pathlib import Path

import yaml
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader

import input_reader as ir

load_dotenv()

import ssl
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
ssl._create_default_https_context = ssl._create_unverified_context


def _nr_str(nr) -> str:
    return f"{int(str(nr).strip()):04d}"


def setup_logging() -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )
    return logging.getLogger(__name__)


def load_config(config_path: str = "config.yaml") -> dict:
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def setup_cloudinary():
    import os
    cloud = os.getenv("CLOUDINARY_CLOUD_NAME")
    key = os.getenv("CLOUDINARY_API_KEY")
    secret = os.getenv("CLOUDINARY_API_SECRET")
    if cloud and key and secret:
        cloudinary.config(cloud_name=cloud, api_key=key, api_secret=secret, secure=True)
        return True
    return False


def upload_to_cloudinary(video_path: Path, logger: logging.Logger):
    try:
        result = cloudinary.uploader.upload(
            str(video_path),
            resource_type="video",
            folder="stereotypen",
            public_id=video_path.stem,
            overwrite=True,
        )
        logger.info(f"[+] Cloudinary Upload: {result['secure_url']}")
    except Exception as e:
        logger.warning(f"[!] Cloudinary Upload fehlgeschlagen: {e}")


def find_image(nr, images_dir: str) -> Path | None:
    ns = _nr_str(nr)
    for ext in ("png", "jpg", "jpeg"):
        p = Path(images_dir) / f"{ns}_pic.{ext}"
        if p.exists():
            return p
    return None


def ensure_rgb_image(image_path: Path, logger: logging.Logger) -> Path:
    """Konvertiert RGBA/Palette-Bilder zu RGB PNG und halbiert die Auflösung."""
    try:
        from PIL import Image
        img = Image.open(image_path)
        if img.mode in ("RGBA", "P", "LA"):
            rgb = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "P":
                img = img.convert("RGBA")
            rgb.paste(img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None)
            img = rgb
        else:
            img = img.convert("RGB")
        new_size = (img.width // 2, img.height // 2)
        img = img.resize(new_size, Image.LANCZOS)
        temp_path = image_path.with_stem(image_path.stem + "_rgb")
        img.save(temp_path, "PNG")
        logger.info(f"[*] Bild → RGB, {new_size[0]}x{new_size[1]}: {temp_path.name}")
        return temp_path
    except Exception as e:
        logger.warning(f"[!] Bild-Verarbeitung fehlgeschlagen: {e}")
    return image_path


def find_audio(nr, output_dir: str) -> Path | None:
    p = Path(output_dir) / f"{_nr_str(nr)}_mp3.mp3"
    return p if p.exists() else None


def _seconds_to_ass(s: float) -> str:
    h = int(s // 3600)
    m = int((s % 3600) // 60)
    sec = s % 60
    return f"{h}:{m:02d}:{sec:05.2f}"


def generate_subtitles(audio_path: Path, ass_path: Path, model_size: str = "small",
                       chunk_size: int = 5, logger: logging.Logger = None) -> bool:
    """Transkribiert Audio mit Whisper und erstellt ASS-Untertiteldatei."""
    try:
        import whisper
    except ImportError:
        if logger:
            logger.error("[-] openai-whisper nicht installiert: pip install openai-whisper")
        return False

    try:
        if logger:
            logger.info(f"[*] Whisper ({model_size}) transkribiert Audio...")
        model = whisper.load_model(model_size)
        result = model.transcribe(str(audio_path), language="de", word_timestamps=True)

        # Wörter aus allen Segmenten sammeln
        words = []
        for seg in result["segments"]:
            for w in seg.get("words", []):
                text = w["word"].strip()
                if text:
                    words.append({"word": text, "start": w["start"], "end": w["end"]})

        # Wörter in Gruppen aufteilen (Karaoke: \k-Tags für Word-Highlight)
        # PrimaryColour = weiß (aktuell gesprochen), SecondaryColour = gelb (noch nicht)
        ass_content = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Trebuchet MS,46,&H00FFFFFF,&H0000FFFF,&H00000000,&H00000000,-1,0,0,0,100,100,2,0,1,3,2,2,30,30,280,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        lines = [ass_content.strip()]
        for i in range(0, len(words), chunk_size):
            group = words[i:i + chunk_size]
            start = _seconds_to_ass(group[0]["start"])
            end = _seconds_to_ass(group[-1]["end"])
            parts = []
            for j, w in enumerate(group):
                if j < len(group) - 1:
                    duration_cs = max(1, int((group[j + 1]["start"] - w["start"]) * 100))
                else:
                    duration_cs = max(1, int((w["end"] - w["start"]) * 100))
                parts.append(f"{{\\k{duration_cs}}}{w['word'].upper()} ")
            text = "".join(parts).rstrip()
            lines.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}")

        ass_path.write_text("\n".join(lines), encoding="utf-8")
        if logger:
            n_chunks = (len(words) + chunk_size - 1) // chunk_size
            logger.info(f"[+] Untertitel: {n_chunks} Blöcke → {ass_path.name}")
        return True

    except Exception as e:
        if logger:
            logger.warning(f"[!] Whisper fehlgeschlagen: {e}")
        return False


def create_video(nr: int, stereotyp: str, config: dict, logger: logging.Logger,
                 subtitles: bool = False, subtitle_words: int = 5) -> bool:
    """Erstelle MP4 aus Bild + Audio via ffmpeg."""
    input_file = config["output"]["input_file"]
    images_dir = config["output"]["images_dir"]
    output_dir = config["output"]["output_dir"]
    video_config = config["video_creation"]
    ffmpeg = video_config.get("ffmpeg_path", "ffmpeg")

    row = ir.find_row(nr, input_file)
    if not row:
        logger.error(f"[-] Story #{nr} nicht gefunden")
        return False

    if row.get("status_video") == "X":
        logger.info(f"[O] Story #{nr} hat bereits Video – überspringe")
        return True

    if row.get("status_audio") != "X":
        logger.error(f"[-] Story #{nr}: Audio fehlt noch (status_audio leer)")
        return False

    logger.info("=" * 60)
    logger.info(f"Video für Story #{nr}: {stereotyp}")
    logger.info("=" * 60)

    # Bild und Audio finden
    image_path = find_image(nr, images_dir)
    audio_path = find_audio(nr, output_dir)

    if not image_path:
        logger.error(f"[-] Kein Bild für Story #{nr} in {images_dir}/")
        logger.error(f"    Erwartet: {images_dir}/{nr}.png")
        return False

    if not audio_path:
        logger.error(f"[-] Kein Audio für Story #{nr} in {output_dir}/")
        return False

    logger.info(f"[*] Bild:  {image_path.name}")
    logger.info(f"[*] Audio: {audio_path.name}")

    # RGBA → RGB konvertieren falls nötig
    rgb_image_path = ensure_rgb_image(image_path, logger)

    # Output-Pfad
    safe = ir.safe_name(stereotyp)
    output_path = Path(output_dir) / f"{_nr_str(nr)}_{safe}.mp4"

    # Untertitel generieren (optional)
    ass_path = None
    if subtitles:
        ass_path = Path(tempfile.mktemp(suffix=".ass"))
        model_size = video_config.get("whisper_model", "small")
        if not generate_subtitles(audio_path, ass_path, model_size=model_size,
                                  chunk_size=subtitle_words, logger=logger):
            ass_path = None

    # ffmpeg: Bild in Schleife + Audio, bis Audio endet
    vf_filter = f"scale={video_config['width']}:{video_config['height']}"
    if ass_path and ass_path.exists():
        # Windows: Pfad für ffmpeg-Filter aufbereiten (Backslashes + Doppelpunkt escapen)
        ass_str = str(ass_path).replace("\\", "/").replace(":", "\\:")
        vf_filter += f",subtitles='{ass_str}'"

    cmd = [
        ffmpeg,
        "-loop", "1",
        "-i", str(rgb_image_path),
        "-i", str(audio_path),
        "-c:v", "libx264",
        "-c:a", "aac",
        "-b:v", video_config["bitrate"],
        "-pix_fmt", "yuv420p",
        "-vf", vf_filter,
        "-r", str(video_config["fps"]),
        "-shortest",
        "-y",
        str(output_path),
    ]

    logger.info(f"[*] ffmpeg: {video_config['width']}x{video_config['height']}, {video_config['fps']}fps, {video_config['bitrate']}{', Untertitel' if ass_path else ''}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            logger.error(f"[-] ffmpeg Fehler:\n{result.stderr[-500:]}")
            return False
    except FileNotFoundError:
        logger.error(f"[-] ffmpeg nicht gefunden: {ffmpeg}")
        logger.error("    Windows: https://ffmpeg.org/download.html → C:\\ffmpeg\\bin\\ffmpeg.exe")
        return False
    except subprocess.TimeoutExpired:
        logger.error("[-] ffmpeg Timeout (10 Min.)")
        return False

    logger.info(f"[+] Video erstellt: {output_path.name} ({output_path.stat().st_size / 1024 / 1024:.1f} MB)")

    # Temp-Dateien aufräumen
    if rgb_image_path != image_path and rgb_image_path.exists():
        rgb_image_path.unlink()
    if ass_path and ass_path.exists():
        ass_path.unlink()

    # Cloudinary Upload
    upload_to_cloudinary(output_path, logger)

    # Bild, Audio, Video → output/0_used/
    used_dir = Path(output_dir) / "0_used"
    used_dir.mkdir(exist_ok=True)
    for src in [image_path, audio_path, output_path]:
        if src and src.exists():
            try:
                shutil.move(str(src), str(used_dir / src.name))
                logger.info(f"[+] → 0_used/{src.name}")
            except Exception as e:
                logger.warning(f"[!] Verschieben fehlgeschlagen ({src.name}): {e}")

    # CSV aktualisieren
    ir.update_field(nr, "status_video", "X", input_file)
    logger.info("[+] CSV aktualisiert: status_video=X")

    return True


def git_push_csv(input_file: str, logger: logging.Logger):
    """Commit und push CSV-Änderungen auf GitHub."""
    repo_root = Path(__file__).parent.parent
    rel_path = os.path.relpath(input_file, repo_root)
    try:
        diff = subprocess.run(
            ["git", "diff", "--quiet", rel_path],
            cwd=str(repo_root), capture_output=True
        )
        if diff.returncode == 0:
            logger.info("[*] Keine CSV-Änderungen – kein Push nötig")
            return
        subprocess.run(["git", "add", rel_path], cwd=str(repo_root), check=True)
        subprocess.run(
            ["git", "commit", "-m", "fix: status_video aktualisiert nach Videogenerierung"],
            cwd=str(repo_root), check=True
        )
        subprocess.run(["git", "push"], cwd=str(repo_root), check=True)
        logger.info("[+] CSV-Änderungen auf GitHub gepusht")
    except subprocess.CalledProcessError as e:
        logger.warning(f"[!] Git Push fehlgeschlagen: {e}")


def main():
    parser = argparse.ArgumentParser(description="Erstelle Videos aus Bild + Audio")
    parser.add_argument("--story", type=str, help="Story-Nummer")
    parser.add_argument("--all", action="store_true", help="Alle bereitstehenden Videos")
    parser.add_argument("--subtitles", action="store_true", help="Burned-in Untertitel via Whisper")
    parser.add_argument("--subtitle-words", type=int, default=5, help="Wörter pro Untertitel-Block (default: 5)")
    parser.add_argument("--no-push", action="store_true", help="Kein automatischer Git Push")
    parser.add_argument("--config", default="config.yaml")
    args = parser.parse_args()

    logger = setup_logging()
    config = load_config(args.config)
    input_file = config["output"]["input_file"]
    setup_cloudinary()

    created = 0

    if args.story:
        row = ir.find_row(args.story, input_file)
        if not row:
            logger.error(f"[-] Story #{args.story} nicht gefunden")
            sys.exit(1)
        if create_video(args.story, row["stereotyp"].strip(), config, logger, subtitles=args.subtitles, subtitle_words=args.subtitle_words):
            created += 1

    elif args.all:
        rows = ir.read_rows(input_file)
        candidates = [
            r for r in rows
            if r.get("status_audio") == "X"
            and r.get("status_pic") == "X"
            and r.get("status_video", "") != "X"
        ]
        logger.info(f"[*] {len(candidates)} Videos zu erstellen")
        for row in candidates:
            try:
                if create_video(row["nr"].strip(), row["stereotyp"].strip(), config, logger, subtitles=args.subtitles, subtitle_words=args.subtitle_words):
                    created += 1
            except Exception as e:
                logger.error(f"[-] Fehler bei Story #{row['nr']}: {e}")

    else:
        # Nächste bereitstehende Story
        rows = ir.read_rows(input_file)
        for row in rows:
            if (row.get("status_audio") == "X"
                    and row.get("status_pic") == "X"
                    and row.get("status_video", "") != "X"):
                if create_video(row["nr"].strip(), row["stereotyp"].strip(), config, logger, subtitles=args.subtitles, subtitle_words=args.subtitle_words):
                    created += 1
                break
        else:
            logger.info("[+] Keine Videos ausstehend")

    if created > 0 and not args.no_push:
        git_push_csv(input_file, logger)


if __name__ == "__main__":
    main()
