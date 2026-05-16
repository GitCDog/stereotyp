#!/usr/bin/env python3
"""
Agent 1: Generiert humorvolle Stereotypen-Stories via Claude CLI (Pro-Account).

Verwendung:
  python generate_stories.py              # Nächste ausstehende Story
  python generate_stories.py --story 5   # Story Nr. 5
  python generate_stories.py --all       # Alle ausstehenden Stories
  python generate_stories.py --story 5 --stichworte "Bier,Wurst,Lederhose"
"""

import os
import sys
import argparse
import logging
import subprocess
from pathlib import Path

import yaml
from dotenv import load_dotenv

import input_reader as ir

load_dotenv()

SYSTEM_PROMPT = """Handle als humoristischer Kulturanthropologe mit einem scharfen Auge \
für deutsche Eigenheiten und moderne Internet-Phänomene. Dein Ziel: Stereotype so \
präzise und übertrieben beschreiben, dass Deutsche entweder laut lachen oder stumm \
nicken müssen. Zieh die Leute durch den Kakao – aber mit Liebe."""

STORY_PROMPT_TEMPLATE = """Erstelle eine humorvolle, potenziell virale Story zum deutschen Stereotyp: "{stereotyp}"

Die Story soll exakt diese Struktur haben (130-140 Woerter gesamt):

Starte mit: "Aufgepasst - " (genau so, mit Bindestrich und Leerzeichen danach).

1. Der Aufreisser: Ein kurzer, provokanter Satz, der das Klischee in eine konkrete Alltagssituation einbettet.

2. Der Mythos: Beschreibe das Verhalten so, als waere es eine heilige Zeremonie oder ein ungeschriebenes Gesetz der Physik (2-3 Saetze).

3. Die deutsche Logik: Erklaere in 2-3 Bulletpoints (mit *) die voellig uebertriebene, aber irgendwie nachvollziehbare Rechtfertigung hinter diesem Verhalten.

4. Der soziale Endgegner: Beschreibe in 1-2 Saetzen die Reaktion der Gesellschaft auf jemanden, der diese ungeschriebene Regel bricht.

5. Der virale Twist: Beende mit einem kurzen Pro-Tipp oder einem trockenen Vergleich (1 Satz).

Tonalitaet: Trocken, leicht sarkastisch, beobachtend - aber nie bösartig. Kein Emoji. Kein Hashtag. Nur reiner Text.
Falls du am Ende eine abschliessende Floskel verwendest, nutze "Tja," statt "Ah ja,".{stichworte_block}"""


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


def build_story_prompt(stereotyp: str, stichworte: list[str] | None = None) -> str:
    if stichworte:
        keywords = ", ".join(stichworte)
        stichworte_block = f"\n\nWichtig: Folgende Stichworte sollen natuerlich und unauffaellig in die Story einfliessen: {keywords}"
    else:
        stichworte_block = ""
    return STORY_PROMPT_TEMPLATE.format(stereotyp=stereotyp, stichworte_block=stichworte_block)


def generate_story(stereotyp: str, stichworte: list[str] | None = None) -> str:
    """Generiere Story-Text via Claude CLI (claude -p)."""
    prompt = SYSTEM_PROMPT + "\n\n" + build_story_prompt(stereotyp, stichworte)
    result = subprocess.run(
        ["claude", "-p", prompt],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Claude CLI Fehler: {result.stderr.strip()}")
    return result.stdout.strip()


def add_paragraph_break(text: str) -> str:
    import re
    text = re.sub(r'\s*\n\s*', ' ', text).strip()
    if '\n\n' in text:
        return text
    target = len(text) // 2
    sentence_ends = [m.start() + 1 for m in re.finditer(r'[.!?]\s+(?=[A-ZÄÖÜ])', text)]
    if not sentence_ends:
        return text
    best = min(sentence_ends, key=lambda pos: abs(pos - target))
    insert_at = text.index(' ', best)
    return text[:insert_at] + '\n\n' + text[insert_at + 1:]


def save_story(nr: int, stereotyp: str, story_text: str, stories_dir: str = "./1_input"):
    safe = ir.safe_name(stereotyp)
    nr_str = f"{int(nr):04d}"
    txt_path = Path(stories_dir) / f"{nr_str}_{safe}.txt"
    if not txt_path.exists():
        txt_path.write_text(add_paragraph_break(story_text), encoding="utf-8")
    return txt_path


def process_story(row: dict, config: dict, logger: logging.Logger,
                  stichworte: list[str] | None = None):
    nr = int(row["nr"])
    stereotyp = row["stereotyp"].strip()
    input_file = config["output"]["input_file"]
    stories_dir = config["output"]["stories_dir"]

    logger.info("=" * 60)
    logger.info(f"Story #{nr}: {stereotyp}")
    logger.info("=" * 60)

    if row.get("status_story") == "X":
        logger.info(f"[O] Bereits fertig – ueberspringe")
        return False

    if stichworte:
        logger.info(f"[*] Stichworte: {', '.join(stichworte)}")

    logger.info(f"[*] Generiere Story via Claude CLI...")
    story_text = generate_story(stereotyp, stichworte)
    word_count = count_words(story_text)
    logger.info(f"[+] Story generiert ({word_count} Woerter)")

    if word_count < 120 or word_count > 150:
        logger.warning(f"[!] Wortzahl ausserhalb Zielbereich: {word_count} (Ziel: 130-140)")

    txt_path = save_story(nr, stereotyp, story_text, stories_dir)
    logger.info(f"[+] Text gespeichert: {txt_path.name}")

    ir.update_field(nr, "status_story", "X", input_file)
    logger.info(f"[+] CSV aktualisiert: status_story=X")

    logger.info("\n" + "-" * 60)
    logger.info(story_text)
    logger.info("-" * 60)

    return True


def main():
    parser = argparse.ArgumentParser(description="Generiere Stereotypen-Stories")
    parser.add_argument("--story", type=int, help="Story-Nummer (z.B. 1)")
    parser.add_argument("--all", action="store_true", help="Alle ausstehenden Stories")
    parser.add_argument("--stichworte", type=str, default="",
                        help="Kommagetrennte Stichworte die in die Story einfliessen sollen")
    parser.add_argument("--config", default="config.yaml")
    args = parser.parse_args()

    config = load_config(args.config)
    logger = setup_logging(config["output"]["log_file"])
    input_file = config["output"]["input_file"]

    stichworte = [s.strip() for s in args.stichworte.split(",") if s.strip()] if args.stichworte else None

    if args.story:
        row = ir.find_row(args.story, input_file)
        if not row:
            logger.error(f"[-] Story #{args.story} nicht gefunden")
            sys.exit(1)
        process_story(row, config, logger, stichworte=stichworte)

    elif args.all:
        rows = ir.read_rows(input_file)
        pending = [r for r in rows if not r.get("status_story", "").strip()]
        logger.info(f"[*] {len(pending)} ausstehende Stories")
        for row in pending:
            try:
                process_story(row, config, logger, stichworte=stichworte)
            except Exception as e:
                logger.error(f"[-] Fehler bei Story #{row['nr']}: {e}")

    else:
        row = ir.get_next_pending("status_story", input_file)
        if not row:
            logger.info("[+] Keine ausstehenden Stories")
            return
        process_story(row, config, logger, stichworte=stichworte)


if __name__ == "__main__":
    main()
