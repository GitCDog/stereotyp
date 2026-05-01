#!/usr/bin/env python3
"""Extrahiere Stories 4-20 aus 00_sammelsurium.txt in einzelne .txt Dateien."""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import input_reader as ir

SAMMELSURIUM = Path("1_input/00_sammelsurium.txt")
STORIES_DIR = Path("1_input")
INPUT_FILE = "1_input/1_input_file.txt"

content = SAMMELSURIUM.read_text(encoding="utf-8")

# Trenne Blöcke anhand der Überschriften
blocks = re.split(r'\n---\n', content)

saved = []
skipped = []

for block in blocks:
    block = block.strip()
    if not block:
        continue

    # Header finden: ### Nr. X: Name
    m = re.match(r'###\s+Nr\.\s+(\d+):\s+(.+)', block)
    if not m:
        continue

    nr = int(m.group(1))
    stereotyp = m.group(2).strip()

    # Story 3 überspringen (existiert bereits)
    if nr < 4:
        skipped.append(nr)
        continue

    # Story-Text: alles nach der Header-Zeile
    lines = block.split('\n', 1)
    if len(lines) < 2:
        continue
    story_text = lines[1].strip()

    # ** entfernen
    story_text = story_text.replace('**', '')

    # Mehrfache Leerzeichen bereinigen
    story_text = re.sub(r'  +', ' ', story_text)

    # Dateiname
    safe = ir.safe_name(stereotyp)
    nr_str = f"{nr:03d}"
    out_path = STORIES_DIR / f"{nr_str}_{safe}.txt"

    if out_path.exists():
        print(f"[O] #{nr} existiert bereits: {out_path.name}")
        skipped.append(nr)
    else:
        out_path.write_text(story_text, encoding="utf-8")
        print(f"[+] #{nr} gespeichert: {out_path.name}")
        saved.append((nr, stereotyp))

    # CSV aktualisieren: status_story=X
    row = ir.find_row(nr, INPUT_FILE)
    if row:
        if row.get("status_story") != "X":
            ir.update_field(nr, "status_story", "X", INPUT_FILE)
            print(f"    CSV: status_story=X")
    else:
        print(f"    [!] Nr. {nr} nicht in CSV gefunden")

print(f"\n[+] Fertig: {len(saved)} gespeichert, {len(skipped)} übersprungen")
