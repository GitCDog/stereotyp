#!/usr/bin/env python3
"""
Generiert Captions für alle Stories und speichert sie in:
  - output/captions.json         (globale Datei mit allen Captions)
  - output/00x_<name>.json       (caption-Feld in jedem Story-JSON)
  - CSV: status_caption = X

Caption-Format:
  Aufgepasst - <stereotyp>

  #hashtag1 #hashtag2 #hashtag3 #hashtag4

Verwendung:
  python generate_captions.py             # Alle ausstehenden
  python generate_captions.py --story 1   # Einzelne Story
  python generate_captions.py --all       # Alle (auch bereits generierte neu)
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path

import yaml
from dotenv import load_dotenv
import anthropic

import input_reader as ir

load_dotenv()

HASHTAG_PROMPT = """Du erstellst 4 passende deutsche Instagram-Hashtags für einen Post über den deutschen Stereotyp "{stereotyp}".

Die Hashtags sollen:
- Spezifisch zum Thema passen (nicht generisch)
- Auf Deutsch sein (außer bekannte englische Begriffe)
- Ohne # Symbol (nur das Wort)
- Viral und relevant für die deutsche Instagram-Community sein

Antworte NUR mit den 4 Hashtags, durch Komma getrennt, kein weiterer Text.
Beispiel: Funktionskleidung,Outdoorfreak,DeutscheProbleme,Wanderausrüstung"""


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


def build_caption(stereotyp: str, hashtags: list[str]) -> str:
    tags = " ".join(f"#{h.strip()}" for h in hashtags)
    return f"Aufgepasst - {stereotyp}\n\n{tags}"


def generate_hashtags(client: anthropic.Anthropic, stereotyp: str, model: str) -> list[str]:
    prompt = HASHTAG_PROMPT.format(stereotyp=stereotyp)
    msg = client.messages.create(
        model=model,
        max_tokens=100,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = msg.content[0].text.strip()
    return [h.strip() for h in raw.split(",") if h.strip()][:4]


def load_captions_file(captions_path: Path) -> dict:
    if captions_path.exists():
        with open(captions_path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_captions_file(captions_path: Path, data: dict):
    with open(captions_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _nr_str(nr: str) -> str:
    nr = str(nr).strip()
    return nr if "_" in nr else f"{int(nr):03d}"


def update_story_json(nr: str, stereotyp: str, caption: str, output_dir: str):
    """Füge caption-Feld in das bestehende Story-JSON ein."""
    nr_str = _nr_str(nr)
    # Suche JSON-Datei
    for p in Path(output_dir).glob(f"{nr_str}_*.json"):
        if "captions" not in p.name:
            with open(p, encoding="utf-8") as f:
                data = json.load(f)
            data["caption"] = caption
            with open(p, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
    return False


def process_caption(row: dict, client: anthropic.Anthropic, config: dict,
                    captions_data: dict, logger: logging.Logger, force: bool = False) -> bool:
    nr = str(row["nr"]).strip()
    stereotyp = row["stereotyp"].strip()
    input_file = config["output"]["input_file"]
    output_dir = config["output"]["output_dir"]
    model = config["story_generation"]["model"]

    if row.get("status_caption") == "X" and not force:
        logger.info(f"[O] Story #{nr} Caption bereits vorhanden – überspringe")
        return True

    if row.get("status_story") != "X":
        logger.info(f"[-] Story #{nr} hat noch keinen Text – überspringe")
        return False

    logger.info(f"[*] Caption für #{nr}: {stereotyp}")

    hashtags = generate_hashtags(client, stereotyp, model)
    caption = build_caption(stereotyp, hashtags)

    logger.info(f"[+] {caption}")

    # Globale captions.json aktualisieren
    captions_data[nr] = {
        "nr": nr,
        "stereotyp": stereotyp,
        "caption": caption,
        "hashtags": hashtags,
    }

    # Story-JSON aktualisieren
    found = update_story_json(nr, stereotyp, caption, output_dir)
    if not found:
        logger.warning(f"[!] Kein Story-JSON für #{nr} gefunden")

    # CSV aktualisieren
    ir.update_field(nr, "status_caption", "X", input_file)
    logger.info(f"[+] status_caption=X")

    return True


def main():
    parser = argparse.ArgumentParser(description="Generiere Captions für alle Stories")
    parser.add_argument("--story", type=str, help="Einzelne Story-Nummer")
    parser.add_argument("--all", action="store_true", help="Alle (auch bereits generierte)")
    parser.add_argument("--model", default=None, help="Modell-Override (z.B. claude-haiku-4-5-20251001)")
    parser.add_argument("--config", default="config.yaml")
    args = parser.parse_args()

    logger = setup_logging()
    config = load_config(args.config)

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("[-] ANTHROPIC_API_KEY fehlt in .env")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    if args.model:
        config["story_generation"]["model"] = args.model
    input_file = config["output"]["input_file"]
    output_dir = config["output"]["output_dir"]
    captions_path = Path(output_dir) / "captions.json"
    captions_data = load_captions_file(captions_path)

    rows = ir.read_rows(input_file)

    if args.story:
        row = ir.find_row(args.story, input_file)
        if not row:
            logger.error(f"[-] Story #{args.story} nicht gefunden")
            sys.exit(1)
        process_caption(row, client, config, captions_data, logger, force=args.all)
    else:
        for row in rows:
            if row.get("status_story") != "X":
                continue
            if row.get("status_caption") == "X" and not args.all:
                continue
            try:
                process_caption(row, client, config, captions_data, logger, force=args.all)
            except Exception as e:
                logger.error(f"[-] Fehler bei Story #{row['nr']}: {e}")

    save_captions_file(captions_path, captions_data)
    logger.info(f"\n[+] captions.json gespeichert ({len(captions_data)} Captions)")


if __name__ == "__main__":
    main()
