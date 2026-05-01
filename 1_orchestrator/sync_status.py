#!/usr/bin/env python3
"""
Scannt vorhandene Dateien und aktualisiert die CSV entsprechend.
Wird vom Server beim Refresh aufgerufen.
"""

import json
import re
import shutil
from pathlib import Path
try:
    from pydub import AudioSegment
    PYDUB_OK = True
except ImportError:
    PYDUB_OK = False

import input_reader as ir

INPUT_FILE = "1_input/1_input_file.txt"
OUTPUT_DIR = Path("output")
USED_DIR = OUTPUT_DIR / "0_used"
STORIES_DIR = Path("1_input")
SAMMELSURIUM = STORIES_DIR / "00_sammelsurium.txt"
CAPTIONS_FILE = OUTPUT_DIR / "captions.json"


def _nr_str(nr_val: str) -> str:
    """Gibt den Datei-Prefix zurück: '100_01' bleibt '100_01', '5' wird '005'."""
    nr_val = nr_val.strip()
    if "_" in nr_val:
        return nr_val
    return f"{int(nr_val):03d}"


def archive_used_files(rows: list) -> int:
    """Verschiebt verwendete Dateien nach output/0_used/.
    Bild/MP3: wenn Video erstellt (status_video=X).
    MP4: erst wenn auf Instagram gepostet (insta_post=X).
    """
    USED_DIR.mkdir(exist_ok=True)
    moved = 0

    for row in rows:
        ns = _nr_str(row["nr"])

        # Bild, MP3 archivieren sobald Video erstellt
        if row.get("status_video") == "X":
            for filename in [f"{ns}_pic.png", f"{ns}_mp3.mp3"]:
                src = OUTPUT_DIR / filename
                if src.exists():
                    shutil.move(str(src), str(USED_DIR / filename))
                    print(f"[>] Archiviert: {filename}")
                    moved += 1

        # Video erst archivieren wenn gepostet
        if row.get("insta_post") == "X":
            for mp4 in OUTPUT_DIR.glob(f"{ns}_*.mp4"):
                shutil.move(str(mp4), str(USED_DIR / mp4.name))
                print(f"[>] Archiviert: {mp4.name}")
                moved += 1

    return moved


def check_sammelsurium() -> int:
    """Neue Einträge aus 00_sammelsurium.txt in CSV + Story-TXT übernehmen."""
    if not SAMMELSURIUM.exists():
        return 0

    text = SAMMELSURIUM.read_text(encoding="utf-8")
    matches = list(re.finditer(r'^(100_\d+):\s*(.+)$', text, re.MULTILINE))
    if not matches:
        return 0

    entries = []
    for i, m in enumerate(matches):
        nr = m.group(1).strip()
        name = m.group(2).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        story_text = text[start:end].strip()
        entries.append((nr, name, story_text))

    existing_nrs = {row["nr"].strip() for row in ir.read_rows(INPUT_FILE)}
    added = 0

    for nr, name, story_text in entries:
        safe = ir.safe_name(name)
        txt_path = STORIES_DIR / f"{nr}_{safe}.txt"

        # TXT-Datei anlegen falls fehlend (auch wenn bereits in CSV)
        if not txt_path.exists() and story_text:
            txt_path.write_text(story_text, encoding="utf-8")
            print(f"[+] Story gespeichert: {txt_path.name}")

        if nr in existing_nrs:
            # CSV-Eintrag existiert – nur status_story sicherstellen
            row = ir.find_row(nr, INPUT_FILE)
            if row and row.get("status_story") != "X" and txt_path.exists():
                ir.update_field(nr, "status_story", "X", INPUT_FILE)
                print(f"[+] status_story=X gesetzt für {nr}")
            continue

        # Komplett neuer Eintrag → CSV-Zeile hinzufügen
        new_row = {
            "nr": nr, "stereotyp": name,
            "status_story": "X" if txt_path.exists() else "",
            "status_audio": "", "seconds": "", "status_pic": "",
            "status_video": "", "status_caption": "", "insta_post": "",
        }
        if ir.add_row(new_row, INPUT_FILE):
            print(f"[+] CSV: {nr} '{name}' hinzugefügt")
            added += 1

    return added


def sync():
    new_from_sammelsurium = check_sammelsurium()
    if new_from_sammelsurium:
        print(f"[+] Sammelsurium: {new_from_sammelsurium} neue Stories übernommen")

    rows = ir.read_rows(INPUT_FILE)
    changes = 0
    new_entries = [r for r in rows if not r.get("status_story", "").strip()]
    if new_entries:
        print(f"[*] {len(new_entries)} Stereotyp(en) ohne Story: "
              + ", ".join(r["stereotyp"] for r in new_entries))

    captions = {}
    if CAPTIONS_FILE.exists():
        try:
            with open(CAPTIONS_FILE, encoding="utf-8") as f:
                captions = json.load(f)
        except json.JSONDecodeError as e:
            print(f"[!] captions.json ungültig (JSON-Fehler): {e}")

    for row in rows:
        nr_val = row["nr"].strip()
        ns = _nr_str(nr_val)

        # Story-Text (00_sammelsurium.txt ausschließen)
        txt_files = [p for p in STORIES_DIR.glob(f"{ns}_*.txt")
                     if p.name != "00_sammelsurium.txt"]
        if txt_files and row.get("status_story") != "X":
            ir.update_field(nr_val, "status_story", "X", INPUT_FILE)
            changes += 1

        # Audio – auch in 0_used suchen
        mp3_path = OUTPUT_DIR / f"{ns}_mp3.mp3"
        mp3_used = USED_DIR / f"{ns}_mp3.mp3"
        mp3_file = mp3_path if mp3_path.exists() else (mp3_used if mp3_used.exists() else None)
        if mp3_file and row.get("status_audio") != "X":
            ir.update_field(nr_val, "status_audio", "X", INPUT_FILE)
            if PYDUB_OK and not row.get("seconds", "").strip():
                dur = int(len(AudioSegment.from_mp3(str(mp3_file))) / 1000)
                ir.update_field(nr_val, "seconds", str(dur), INPUT_FILE)
            changes += 1
        elif mp3_file and PYDUB_OK and not row.get("seconds", "").strip():
            dur = int(len(AudioSegment.from_mp3(str(mp3_file))) / 1000)
            ir.update_field(nr_val, "seconds", str(dur), INPUT_FILE)
            changes += 1

        # Bild – auch in 0_used suchen
        pic_path = OUTPUT_DIR / f"{ns}_pic.png"
        pic_used = USED_DIR / f"{ns}_pic.png"
        if (pic_path.exists() or pic_used.exists()) and row.get("status_pic") != "X":
            ir.update_field(nr_val, "status_pic", "X", INPUT_FILE)
            changes += 1

        # Video
        mp4_files = list(OUTPUT_DIR.glob(f"{ns}_*.mp4"))
        if mp4_files and row.get("status_video") != "X":
            ir.update_field(nr_val, "status_video", "X", INPUT_FILE)
            changes += 1

        # Caption – in captions.json nachschlagen
        if nr_val in captions and row.get("status_caption") != "X":
            ir.update_field(nr_val, "status_caption", "X", INPUT_FILE)
            changes += 1

    # Verwendete Dateien archivieren
    rows = ir.read_rows(INPUT_FILE)
    moved = archive_used_files(rows)
    if moved:
        print(f"[>] {moved} Dateien nach 0_used/ verschoben")

    print(f"[+] Sync abgeschlossen: {changes} Änderungen")
    return changes


if __name__ == "__main__":
    sync()
