#!/usr/bin/env python3
"""
Agent 1: Generiert humorvolle Stereotypen-Stories via Claude API.

Verwendung:
  python generate_stories.py              # Nächste ausstehende Story
  python generate_stories.py --story 5   # Story Nr. 5
  python generate_stories.py --all       # Alle ausstehenden Stories
  python generate_stories.py --story 5 --auto-title  # Claude erfindet Titel
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
from datetime import datetime

import yaml
from dotenv import load_dotenv
import anthropic

import input_reader as ir

load_dotenv()

SYSTEM_PROMPT = """Handle als humoristischer Kulturanthropologe mit einem scharfen Auge \
für deutsche Eigenheiten und moderne Internet-Phänomene. Dein Ziel: Stereotype so \
präzise und übertrieben beschreiben, dass Deutsche entweder laut lachen oder stumm \
nicken müssen. Zieh die Leute durch den Kakao – aber mit Liebe."""

STORY_PROMPT_TEMPLATE = """Erstelle eine humorvolle, potenziell virale Story zum deutschen Stereotyp: "{stereotyp}"

Die Story soll exakt diese Struktur haben (130–140 Wörter gesamt):

Starte mit: "Aufgepasst - " (genau so, mit Bindestrich und Leerzeichen danach).

1. **Der Aufreißer**: Ein kurzer, provokanter Satz, der das Klischee in eine konkrete Alltagssituation einbettet.

2. **Der Mythos**: Beschreibe das Verhalten so, als wäre es eine heilige Zeremonie oder ein ungeschriebenes Gesetz der Physik (2–3 Sätze).

3. **Die „deutsche Logik"**: Erkläre in 2–3 Bulletpoints (mit •) die völlig übertriebene, aber irgendwie nachvollziehbare Rechtfertigung hinter diesem Verhalten.

4. **Der soziale Endgegner**: Beschreibe in 1–2 Sätzen die Reaktion der Gesellschaft auf jemanden, der diese ungeschriebene Regel bricht.

5. **Der virale Twist**: Beende mit einem kurzen Pro-Tipp oder einem trockenen Vergleich (1 Satz).

Tonalität: Trocken, leicht sarkastisch, beobachtend – aber nie bösartig. Kein Emoji. Kein Hashtag. Nur reiner Text.
Falls du am Ende eine abschließende Floskel verwendest, nutze "Tja," statt "Ah ja,"."""

AUTO_TITLE_PROMPT = """Erfinde einen knackigen, viralen Titel für einen deutschen Stereotypen-Post.
Der Titel soll:
- 3–5 Wörter lang sein
- Den Charakter oder das Verhalten auf den Punkt bringen
- Sich wie ein Internet-Meme anfühlen
- Auf Deutsch sein

Antworte NUR mit dem Titel, ohne Anführungszeichen, ohne Erklärung."""


def setup_logging(log_file: str = "./logs/workflow.log") -> logging.Logger:
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    return logging.getLogger(__name__)


def load_config(config_path: str = "config.yaml") -> dict:
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def count_words(text: str) -> int:
    return len(text.split())


def generate_story(client: anthropic.Anthropic, stereotyp: str, model: str) -> str:
    """Generiere Story-Text via Claude."""
    prompt = STORY_PROMPT_TEMPLATE.format(stereotyp=stereotyp)
    message = client.messages.create(
        model=model,
        max_tokens=600,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


def generate_auto_title(client: anthropic.Anthropic, model: str) -> str:
    """Lass Claude einen Titel erfinden."""
    message = client.messages.create(
        model=model,
        max_tokens=50,
        messages=[{"role": "user", "content": AUTO_TITLE_PROMPT}],
    )
    return message.content[0].text.strip()


def save_story(nr: int, stereotyp: str, story_text: str, stories_dir: str = "./1_input"):
    """Speichere Story als .txt in 1_input/."""
    safe = ir.safe_name(stereotyp)
    nr_str = f"{int(nr):04d}"

    txt_path = Path(stories_dir) / f"{nr_str}_{safe}.txt"
    if not txt_path.exists():
        txt_path.write_text(story_text, encoding="utf-8")

    return txt_path


def process_story(row: dict, client: anthropic.Anthropic, config: dict, logger: logging.Logger, auto_title: bool = False):
    """Verarbeite eine einzelne Story-Zeile."""
    nr = int(row["nr"])
    stereotyp = row["stereotyp"].strip()
    input_file = config["output"]["input_file"]
    output_dir = config["output"]["output_dir"]
    stories_dir = config["output"]["stories_dir"]

    logger.info("=" * 60)
    logger.info(f"Story #{nr}: {stereotyp}")
    logger.info("=" * 60)

    # Überspringe wenn bereits fertig
    if row.get("status_story") == "X":
        logger.info(f"[O] Bereits fertig – überspringe")
        return False

    # Auto-Titel-Modus
    if auto_title:
        logger.info("[*] Generiere Titel automatisch via Claude...")
        stereotyp = generate_auto_title(client, config["story_generation"]["model"])
        logger.info(f"[+] Auto-Titel: {stereotyp}")

    # Story generieren
    logger.info(f"[*] Generiere Story via Claude ({config['story_generation']['model']})...")
    story_text = generate_story(client, stereotyp, config["story_generation"]["model"])
    word_count = count_words(story_text)
    logger.info(f"[+] Story generiert ({word_count} Wörter)")

    if word_count < 120 or word_count > 150:
        logger.warning(f"[!] Wortzahl außerhalb Zielbereich: {word_count} (Ziel: 130–140)")

    # Speichern
    txt_path = save_story(nr, stereotyp, story_text, stories_dir)
    logger.info(f"[+] Text gespeichert: {txt_path.name}")

    # CSV aktualisieren
    ir.update_field(nr, "status_story", "X", input_file)
    logger.info(f"[+] CSV aktualisiert: status_story=X")

    # Story-Preview
    logger.info("\n" + "-" * 60)
    logger.info(story_text)
    logger.info("-" * 60)

    return True


def main():
    parser = argparse.ArgumentParser(description="Generiere Stereotypen-Stories")
    parser.add_argument("--story", type=int, help="Story-Nummer (z.B. 1)")
    parser.add_argument("--all", action="store_true", help="Alle ausstehenden Stories")
    parser.add_argument("--auto-title", action="store_true", help="Titel von Claude generieren lassen")
    parser.add_argument("--config", default="config.yaml")
    args = parser.parse_args()

    config = load_config(args.config)
    logger = setup_logging(config["output"]["log_file"])

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("[-] ANTHROPIC_API_KEY fehlt in .env")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    input_file = config["output"]["input_file"]

    if args.story:
        row = ir.find_row(args.story, input_file)
        if not row:
            logger.error(f"[-] Story #{args.story} nicht gefunden")
            sys.exit(1)
        process_story(row, client, config, logger, auto_title=args.auto_title)

    elif args.all:
        rows = ir.read_rows(input_file)
        pending = [r for r in rows if not r.get("status_story", "").strip()]
        logger.info(f"[*] {len(pending)} ausstehende Stories")
        for row in pending:
            try:
                process_story(row, client, config, logger, auto_title=args.auto_title)
            except Exception as e:
                logger.error(f"[-] Fehler bei Story #{row['nr']}: {e}")

    else:
        row = ir.get_next_pending("status_story", input_file)
        if not row:
            logger.info("[+] Keine ausstehenden Stories")
            return
        process_story(row, client, config, logger, auto_title=args.auto_title)


if __name__ == "__main__":
    main()
