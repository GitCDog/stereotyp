#!/usr/bin/env python3
"""
Agent 3: Vertont Stories via ElevenLabs.

Verwendung:
  python generate_audio.py --story 1     # Audio für Story #1
  python generate_audio.py --all         # Alle ausstehenden Audios
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path

import yaml
import requests
from dotenv import load_dotenv

import input_reader as ir

load_dotenv()


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


def get_audio_duration(audio_path: Path) -> int:
    """Gibt Dauer in Sekunden zurück."""
    try:
        from pydub import AudioSegment
        audio = AudioSegment.from_mp3(str(audio_path))
        return int(len(audio) / 1000)
    except Exception:
        return 0


def get_story_text(nr: int, stereotyp: str, stories_dir: str, output_dir: str) -> str | None:
    """Lese Story-Text aus Textdatei oder JSON."""
    safe = ir.safe_name(stereotyp)
    nr_str = f"{int(nr):03d}"

    nr_str = str(nr).strip() if "_" in str(nr) else f"{int(nr):03d}"
    txt_path = Path(stories_dir) / f"{nr_str}_{safe}.txt"
    if not txt_path.exists():
        for p in Path(stories_dir).glob(f"{nr_str}_*.txt"):
            txt_path = p
            break

    if txt_path.exists():
        return txt_path.read_text(encoding="utf-8").strip()

    return None


def generate_audio_elevenlabs(api_key: str, text: str, voice_id: str, model_id: str,
                               stability: float, similarity_boost: float,
                               style: float = 0.0, speed: float = 1.0) -> bytes | None:
    """Rufe ElevenLabs TTS API auf und gib Audio-Bytes zurück."""
    if not voice_id:
        raise ValueError("voice_id in config.yaml ist leer! Bitte ElevenLabs Voice ID eintragen.")

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    payload = {
        "text": text,
        "model_id": model_id,
        "voice_settings": {
            "stability": stability,
            "similarity_boost": similarity_boost,
            "style": style,
            "speed": speed,
        },
    }

    response = requests.post(url, headers=headers, json=payload, timeout=120)

    if response.status_code != 200:
        raise RuntimeError(f"ElevenLabs Fehler {response.status_code}: {response.text[:300]}")

    return response.content


def process_audio(nr: int, config: dict, logger: logging.Logger, api_key: str) -> bool:
    input_file = config["output"]["input_file"]
    stories_dir = config["output"]["stories_dir"]
    output_dir = config["output"]["output_dir"]
    tts_config = config["text_to_speech"]

    row = ir.find_row(nr, input_file)
    if not row:
        logger.error(f"[-] Story #{nr} nicht gefunden")
        return False

    stereotyp = row["stereotyp"].strip()

    if row.get("status_audio") == "X":
        logger.info(f"[O] Story #{nr} bereits vertont – überspringe")
        return True

    if row.get("status_story") != "X":
        logger.error(f"[-] Story #{nr} hat noch keinen Text (status_story leer)")
        return False

    logger.info("=" * 60)
    logger.info(f"Audio für Story #{nr}: {stereotyp}")
    logger.info("=" * 60)

    story_text = get_story_text(nr, stereotyp, stories_dir, output_dir)
    if not story_text:
        logger.error(f"[-] Kein Story-Text für #{nr} gefunden")
        return False

    logger.info(f"[*] ElevenLabs TTS, Voice ID: {tts_config['voice_id'] or '(nicht gesetzt)'}")

    try:
        audio_bytes = generate_audio_elevenlabs(
            api_key=api_key,
            text=story_text,
            voice_id=tts_config["voice_id"],
            model_id=tts_config["model_id"],
            stability=tts_config["stability"],
            similarity_boost=tts_config["similarity_boost"],
            style=tts_config.get("style", 0.0),
            speed=tts_config.get("speed", 1.0),
        )
    except Exception as e:
        logger.error(f"[-] ElevenLabs Fehler: {e}")
        return False

    # Speichern
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    nr_str = str(nr).strip() if "_" in str(nr) else f"{int(nr):03d}"
    audio_path = Path(output_dir) / f"{nr_str}_mp3.mp3"
    audio_path.write_bytes(audio_bytes)
    logger.info(f"[+] Audio gespeichert: {audio_path.name} ({len(audio_bytes):,} Bytes)")

    # Dauer ermitteln
    duration = get_audio_duration(audio_path)
    if duration:
        logger.info(f"[+] Dauer: {duration} Sekunden")

    # CSV aktualisieren
    ir.update_field(nr, "status_audio", "X", input_file)
    if duration:
        ir.update_field(nr, "seconds", str(duration), input_file)
    logger.info("[+] CSV aktualisiert: status_audio=X")

    return True


def main():
    parser = argparse.ArgumentParser(description="Vertone Stories via ElevenLabs")
    parser.add_argument("--story", type=str, help="Story-Nummer oder ID (z.B. 8 oder 100_01)")
    parser.add_argument("--all", action="store_true", help="Alle ausstehenden")
    parser.add_argument("--config", default="config.yaml")
    args = parser.parse_args()

    logger = setup_logging()
    config = load_config(args.config)

    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        logger.error("[-] ELEVENLABS_API_KEY fehlt in .env")
        sys.exit(1)

    input_file = config["output"]["input_file"]

    if args.story:
        process_audio(args.story, config, logger, api_key)

    elif args.all:
        rows = ir.read_rows(input_file)
        pending = [r for r in rows if r.get("status_story") == "X" and not r.get("status_audio", "").strip()]
        logger.info(f"[*] {len(pending)} ausstehende Audios")
        for row in pending:
            try:
                process_audio(row["nr"], config, logger, api_key)
            except Exception as e:
                logger.error(f"[-] Fehler bei Story #{row['nr']}: {e}")

    else:
        row = ir.get_next_pending("status_audio", input_file)
        if not row:
            logger.info("[+] Keine ausstehenden Audios")
            return
        if row.get("status_story") != "X":
            logger.error("[-] Nächste Story hat noch keinen Text. Erst generate_stories.py ausführen.")
            return
        process_audio(row["nr"], config, logger, api_key)


if __name__ == "__main__":
    main()
