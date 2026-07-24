#!/usr/bin/env python3
"""
Generiert Captions für Stories und speichert sie in output/captions.json.

Caption-Format:
  Aufgepasst - <stereotyp>

  #hashtag1 #hashtag2 #hashtag3 #hashtag4

Verwendung:
  python generate_captions.py             # Alle ausstehenden
  python generate_captions.py --story 1   # Einzelne Story
  python generate_captions.py --story 1 --stichworte "Menowin,DSDS,Dieter Bohlen"
  python generate_captions.py --all       # Alle (auch bereits generierte neu)
"""

import os
import sys
import json
import argparse
import logging
import subprocess
from pathlib import Path

import yaml
from dotenv import load_dotenv

import input_reader as ir

load_dotenv()

HASHTAG_PROMPT = """Du erstellst 4 passende deutsche Instagram-Hashtags für einen Post über den deutschen Stereotyp "{stereotyp}".{stichworte_block}

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


def build_caption(stereotyp: str, hashtags: list[str], stichworte: list[str] | None = None) -> str:
    all_tags = list(hashtags)
    if stichworte:
        # Stichworte als zusätzliche Hashtags hinzufügen (ohne Leerzeichen)
        for s in stichworte:
            tag = s.strip().replace(" ", "")
            if tag and f"#{tag}" not in [f"#{t}" for t in all_tags]:
                all_tags.append(tag)
    tags = " ".join(f"#{h.strip()}" for h in all_tags)
    return f"Aufgepasst - {stereotyp}\n\n{tags}"


def generate_hashtags(stereotyp: str, stichworte: list[str] | None = None) -> list[str]:
    if stichworte:
        stichworte_block = f"\n\nDie folgenden Begriffe sollen als Hashtags vorkommen: {', '.join(stichworte)}"
    else:
        stichworte_block = ""
    prompt = HASHTAG_PROMPT.format(stereotyp=stereotyp, stichworte_block=stichworte_block)
    env = {**os.environ, "TERM": "dumb", "NO_COLOR": "1"}
    result = subprocess.run(
        ["claude", "-p", prompt, "--allowedTools", "", "--model", "claude-sonnet-4-6"],
        capture_output=True, text=True, encoding="utf-8", timeout=60,
        stdin=subprocess.DEVNULL, env=env,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Claude CLI Fehler: {result.stderr.strip() or result.stdout.strip()}")
    raw = result.stdout.strip()
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
    return f"{int(str(nr).strip()):04d}"


def process_caption(row: dict, config: dict, captions_data: dict,
                    logger: logging.Logger, force: bool = False,
                    stichworte: list[str] | None = None) -> bool:
    nr = str(row["nr"]).strip()
    stereotyp = row["stereotyp"].strip()
    input_file = config["output"]["input_file"]
    output_dir = config["output"]["output_dir"]

    if row.get("status_caption") == "X" and not force:
        logger.info(f"[O] Story #{nr} Caption bereits vorhanden – überspringe")
        return True

    if row.get("status_story") != "X":
        logger.info(f"[-] Story #{nr} hat noch keinen Text – überspringe")
        return False

    logger.info(f"[*] Caption für #{nr}: {stereotyp}")
    if stichworte:
        logger.info(f"[*] Stichworte: {', '.join(stichworte)}")

    hashtags = generate_hashtags(stereotyp, stichworte)
    caption = build_caption(stereotyp, hashtags, stichworte)

    logger.info(f"[+] {caption}")

    captions_data[nr] = {
        "nr": nr,
        "stereotyp": stereotyp,
        "caption": caption,
        "hashtags": hashtags,
    }

    ir.update_field(nr, "status_caption", "X", input_file)
    logger.info(f"[+] status_caption=X")

    captions_path = Path(output_dir) / "captions.json"
    save_captions_file(captions_path, load_captions_file(captions_path) | captions_data)

    return True


def main():
    parser = argparse.ArgumentParser(description="Generiere Captions für Stories")
    parser.add_argument("--story", type=str, help="Einzelne Story-Nummer")
    parser.add_argument("--all", action="store_true", help="Alle (auch bereits generierte)")
    parser.add_argument("--stichworte", type=str, default="",
                        help="Kommagetrennte Stichworte die als Hashtags erscheinen sollen")
    parser.add_argument("--config", default="config.yaml")
    args = parser.parse_args()

    logger = setup_logging()
    config = load_config(args.config)
    input_file = config["output"]["input_file"]
    output_dir = config["output"]["output_dir"]
    captions_path = Path(output_dir) / "captions.json"
    captions_data = load_captions_file(captions_path)

    stichworte = [s.strip() for s in args.stichworte.split(",") if s.strip()] if args.stichworte else None

    rows = ir.read_rows(input_file)

    if args.story:
        row = ir.find_row(args.story, input_file)
        if not row:
            logger.error(f"[-] Story #{args.story} nicht gefunden")
            sys.exit(1)
        process_caption(row, config, captions_data, logger, force=args.all, stichworte=stichworte)
    else:
        for row in rows:
            if row.get("status_story") != "X":
                continue
            if row.get("status_caption") == "X" and not args.all:
                continue
            try:
                process_caption(row, config, captions_data, logger, force=args.all, stichworte=stichworte)
            except Exception as e:
                logger.error(f"[-] Fehler bei Story #{row['nr']}: {e}")

    save_captions_file(captions_path, captions_data)
    logger.info(f"[+] captions.json gespeichert ({len(captions_data)} Captions)")


if __name__ == "__main__":
    main()
