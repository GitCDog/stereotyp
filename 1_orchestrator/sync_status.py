#!/usr/bin/env python3
"""
Scannt vorhandene Dateien und aktualisiert die CSV entsprechend.
Wird vom Server beim Refresh aufgerufen.
"""

import json
import os
import re
import shutil
from pathlib import Path
try:
    from pydub import AudioSegment
    PYDUB_OK = True
except ImportError:
    PYDUB_OK = False

try:
    import cloudinary
    import cloudinary.api
    from dotenv import load_dotenv
    load_dotenv()
    cloudinary.config(
        cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
        api_key=os.getenv("CLOUDINARY_API_KEY"),
        api_secret=os.getenv("CLOUDINARY_API_SECRET"),
        secure=True,
    )
    import ssl, urllib3
    urllib3.disable_warnings()
    ssl._create_default_https_context = ssl._create_unverified_context
    CLOUDINARY_OK = bool(os.getenv("CLOUDINARY_CLOUD_NAME"))
except Exception:
    CLOUDINARY_OK = False

import input_reader as ir

INPUT_FILE = "1_input/1_input_file.txt"
OUTPUT_DIR = Path("output")
USED_DIR = OUTPUT_DIR / "0_used"
STORIES_DIR = Path("1_input")
SAMMELSURIUM = STORIES_DIR / "00_sammelsurium.txt"
CAPTIONS_FILE = OUTPUT_DIR / "captions.json"


def _nr_str(nr_val: str) -> str:
    return f"{int(str(nr_val).strip()):04d}"


def _ensure_paragraph(text: str) -> str:
    """Fügt Absatz bei ~50% nach einem Satzende ein, falls noch keiner vorhanden."""
    text = re.sub(r'\s*\n\s*', ' ', text).strip()
    if '\n\n' in text:
        return text
    target = len(text) // 2
    ends = [m.start() + 1 for m in re.finditer(r'[.!?]\s+(?=[A-ZÄÖÜ])', text)]
    if not ends:
        return text
    best = min(ends, key=lambda p: abs(p - target))
    insert_at = text.index(' ', best)
    return text[:insert_at] + '\n\n' + text[insert_at + 1:]


def delete_cloudinary_video(ns: str):
    """Löscht Video mit Prefix stereotypen/{ns} von Cloudinary, falls vorhanden."""
    if not CLOUDINARY_OK:
        return
    try:
        resources = cloudinary.api.resources(
            type="upload", resource_type="video",
            prefix=f"stereotypen/{ns}", max_results=10,
        )
        for item in resources.get("resources", []):
            cloudinary.api.delete_resources([item["public_id"]], resource_type="video")
            print(f"[+] Cloudinary gelöscht: {item['public_id']}")
    except Exception as e:
        print(f"[!] Cloudinary Löschung fehlgeschlagen für {ns}: {e}")


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
                    try:
                        shutil.move(str(src), str(USED_DIR / filename))
                        print(f"[>] Archiviert: {filename}")
                        moved += 1
                    except Exception as e:
                        print(f"[!] Konnte {filename} nicht verschieben: {e}")

        # Video erst archivieren wenn gepostet + Cloudinary löschen
        if row.get("insta_post") == "X":
            for mp4 in OUTPUT_DIR.glob(f"{ns}_*.mp4"):
                try:
                    shutil.move(str(mp4), str(USED_DIR / mp4.name))
                    print(f"[>] Archiviert: {mp4.name}")
                    moved += 1
                except Exception as e:
                    print(f"[!] Konnte {mp4.name} nicht verschieben: {e}")
            delete_cloudinary_video(ns)

    return moved


def _clean_story_text(raw: str) -> str:
    """Bereinigt Markdown-Formatierung aus Sammelsurium-Text."""
    # Alles ab dem ersten --- Trenner abschneiden
    raw = re.split(r'\n\s*---+', raw)[0]
    # Markdown Bold **text** → text
    raw = re.sub(r'\*\*(.+?)\*\*', r'\1', raw)
    # Markdown Italic *text* → text
    raw = re.sub(r'\*(.+?)\*', r'\1', raw)
    # Markdown Header ### entfernen
    raw = re.sub(r'^#{1,6}\s*', '', raw, flags=re.MULTILINE)
    return raw.strip()


def check_sammelsurium() -> int:
    """Neue Einträge aus 00_sammelsurium.txt in CSV + Story-TXT übernehmen.
    Unterstützt Format: '### 124: Titel' oder '124: Titel'.
    Erfolgreich extrahierte Einträge werden aus dem Sammelsurium gelöscht."""
    if not SAMMELSURIUM.exists():
        return 0

    text = SAMMELSURIUM.read_text(encoding="utf-8")
    # Erkennt: "124: Titel" oder "### 124: Titel"
    matches = list(re.finditer(r'^#{0,3}\s*(\d{1,4}):\s*(.+)$', text, re.MULTILINE))
    if not matches:
        return 0

    entries = []
    for i, m in enumerate(matches):
        nr = f"{int(m.group(1)):04d}"
        name = m.group(2).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        story_text = _clean_story_text(text[start:end])
        entries.append((nr, name, story_text, m.start(), end))

    existing_nrs = {int(row["nr"].strip()) for row in ir.read_rows(INPUT_FILE)}
    added = 0
    processed_ranges = []

    for nr, name, story_text, entry_start, entry_end in entries:
        safe = ir.safe_name(name)
        txt_path = STORIES_DIR / f"{nr}_{safe}.txt"

        if not txt_path.exists() and story_text:
            txt_path.write_text(_ensure_paragraph(story_text), encoding="utf-8")
            print(f"[+] Story gespeichert: {txt_path.name}")

        if not txt_path.exists():
            # Kein Text → im Sammelsurium lassen
            continue

        if int(nr) in existing_nrs:
            row = ir.find_row(nr, INPUT_FILE)
            if row and row.get("status_story") != "X":
                ir.update_field(nr, "status_story", "X", INPUT_FILE)
                print(f"[+] status_story=X gesetzt für {nr}")
        else:
            new_row = {
                "nr": nr, "stereotyp": name,
                "status_story": "X",
                "status_audio": "", "seconds": "", "status_pic": "",
                "status_video": "", "status_caption": "", "insta_post": "",
            }
            if ir.add_row(new_row, INPUT_FILE):
                print(f"[+] CSV: {nr} '{name}' hinzugefügt")
                added += 1

        processed_ranges.append((entry_start, entry_end))

    # Verarbeitete Einträge aus Sammelsurium entfernen
    if processed_ranges:
        remaining = text
        for start, end in sorted(processed_ranges, reverse=True):
            remaining = remaining[:start] + remaining[end:]
        remaining = re.sub(r'\n{3,}', '\n\n', remaining).strip()
        SAMMELSURIUM.write_text(remaining + ("\n" if remaining else ""), encoding="utf-8")
        print(f"[+] {len(processed_ranges)} Einträge aus Sammelsurium entfernt")

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

        # Video – auch in 0_used suchen; Status korrigieren wenn Datei fehlt
        mp4_files = list(OUTPUT_DIR.glob(f"{ns}_*.mp4")) + list(USED_DIR.glob(f"{ns}_*.mp4"))
        if mp4_files and row.get("status_video") != "X":
            ir.update_field(nr_val, "status_video", "X", INPUT_FILE)
            changes += 1
        elif not mp4_files and row.get("status_video") == "X" and row.get("insta_post") != "X":
            ir.update_field(nr_val, "status_video", "", INPUT_FILE)
            print(f"[!] status_video zurückgesetzt für #{nr_val} (kein MP4 gefunden)")
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
