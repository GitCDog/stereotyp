#!/usr/bin/env python3
"""
Erstellt eine Prompt-Datei für GPT/Bildgenerierung.

Format pro Story:
  {nr}. erstelle ein bild dazu, jedoch nehme nicht so viel text in das bild rein,
  Titel "{stereotyp}". Story: "{story_text}"

Verwendung:
  python generate_gpt_prompt.py              # Alle Stories mit vorhandenem Text
  python generate_gpt_prompt.py --no-pic     # Nur Stories ohne Bild (status_pic != X)
  python generate_gpt_prompt.py --out meine_datei.txt
"""

import argparse
import re
from pathlib import Path

import input_reader as ir

STORIES_DIR = Path("1_input")
INPUT_FILE = "1_input/1_input_file.txt"
DEFAULT_OUT = STORIES_DIR / "gpt_prompts.txt"


def _nr_str(nr: str) -> str:
    return f"{int(str(nr).strip()):04d}"


def find_story_file(nr: str, stereotyp: str) -> Path | None:
    ns = _nr_str(nr)
    # Direkte Suche nach Prefix
    matches = [p for p in STORIES_DIR.glob(f"{ns}_*.txt")
               if p.name != "00_sammelsurium.txt" and p.name != "gpt_prompts.txt"]
    return matches[0] if matches else None


def main():
    parser = argparse.ArgumentParser(description="Erstelle GPT-Bildprompt-Datei")
    parser.add_argument("--no-pic", action="store_true",
                        help="Nur Stories ohne Bild (status_pic leer)")
    parser.add_argument("--out", default=str(DEFAULT_OUT),
                        help=f"Ausgabedatei (Standard: {DEFAULT_OUT})")
    args = parser.parse_args()

    rows = ir.read_rows(INPUT_FILE)

    lines = []
    skipped = 0

    for row in rows:
        nr = row["nr"].strip()
        stereotyp = row["stereotyp"].strip()

        if row.get("status_story") != "X":
            skipped += 1
            continue

        if args.no_pic and row.get("status_pic") == "X":
            skipped += 1
            continue

        story_file = find_story_file(nr, stereotyp)
        if not story_file:
            print(f"[!] Kein Story-Text für #{nr} – überspringe")
            skipped += 1
            continue

        text = story_file.read_text(encoding="utf-8").strip()
        # Zeilenumbrüche innerhalb des Texts entfernen (inline format)
        text = re.sub(r"\s+", " ", text)

        lines.append(
            f'{nr}. erstelle ein bild (1024x1536) dazu, nicht düster und nicht böse und nehme nicht so viel text in das bild rein, '
            f'Titel "{stereotyp}". Story: "{text}"'
        )

    out_path = Path(args.out)
    out_path.write_text("\n\n".join(lines), encoding="utf-8")

    print(f"[+] {len(lines)} Prompts -> {out_path}")
    if skipped:
        print(f"[*] {skipped} übersprungen (kein Text oder bereits Bild vorhanden)")


if __name__ == "__main__":
    main()
