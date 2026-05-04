#!/usr/bin/env python3
"""
Wird bei jedem Claude-Session-Start ausgeführt (via Hook).

Ablauf:
1. OneDrive prüfen
   - Korrekt benannte Bilder (NNNN_pic.png) → sofort automatisch verarbeiten
   - Unbekannte Namen → als direkte Aufgabe an Claude übergeben (sofort ausführen)
2. Videos generieren für alle Stories mit Bild + Audio aber ohne Video
3. systemMessage mit Zusammenfassung / Aufgaben ausgeben
"""

import csv
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except Exception:
    pass

SCRIPT_DIR    = Path(__file__).parent
ONEDRIVE_DIR  = Path(r"C:\Users\slawa\OneDrive\8_stereotypen")
OUTPUT_DIR    = SCRIPT_DIR / "output"
INPUT_FILE    = SCRIPT_DIR / "1_input" / "1_input_file.txt"
NAMED_PATTERN = re.compile(r'^\d{4}_pic\.png$')

sys.path.insert(0, str(SCRIPT_DIR))


def load_csv_rows() -> list[dict]:
    with open(INPUT_FILE, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def process_known_images() -> list[str]:
    """Verarbeitet korrekt benannte Bilder sofort. Gibt Liste der verarbeiteten zurück."""
    if not ONEDRIVE_DIR.exists():
        return []

    try:
        import input_reader as ir
    except ImportError:
        ir = None

    done = []
    for img in sorted(ONEDRIVE_DIR.glob("*.png")):
        if NAMED_PATTERN.match(img.name):
            nr_int = int(img.stem.replace("_pic", ""))
            nr_str = f"{nr_int:04d}"
            dest = OUTPUT_DIR / f"{nr_str}_pic.png"
            shutil.copy2(img, dest)
            img.unlink()
            done.append(nr_str)
            if ir:
                try:
                    ir.update_field(str(nr_int), "status_pic", "X", str(INPUT_FILE))
                except Exception:
                    pass

    if done:
        subprocess.run([sys.executable, "sync_status.py"], cwd=SCRIPT_DIR, capture_output=True)

    return done


def unrecognized_images() -> list[str]:
    if not ONEDRIVE_DIR.exists():
        return []
    return [p.name for p in sorted(ONEDRIVE_DIR.glob("*.png"))
            if not NAMED_PATTERN.match(p.name)]


def pending_videos(rows: list[dict]) -> list[str]:
    return [
        r["nr"].strip() for r in rows
        if r.get("status_pic") == "X"
        and r.get("status_audio") == "X"
        and r.get("status_video", "") != "X"
    ]


def main():
    parts = []

    # 1. Bekannte Bilder sofort verarbeiten
    known_done = process_known_images()
    if known_done:
        parts.append(f"✅ {len(known_done)} Bild(er) automatisch aus OneDrive übernommen: "
                     + ", ".join(known_done))

    # 2. Unbekannte Bilder → direkte Aufgabe für Claude
    unknown = unrecognized_images()
    if unknown:
        files = "\n".join(f"  - {ONEDRIVE_DIR / f}" for f in unknown)
        rows = load_csv_rows()
        story_list = "\n".join(
            f"{r['nr']}: {r['stereotyp']}" for r in rows
            if r.get("status_pic", "") != "X"
        )
        parts.append(
            f"AUFGABE – JETZT SOFORT AUSFÜHREN (vor jeder anderen Antwort):\n"
            f"{len(unknown)} neue Bild(er) in OneDrive warten auf Verarbeitung:\n{files}\n\n"
            f"Für jedes Bild:\n"
            f"1. Bild mit Read-Tool öffnen und visuell prüfen\n"
            f"2. Passende Story aus dieser Liste bestimmen:\n{story_list}\n"
            f"3. Bild kopieren nach {OUTPUT_DIR}\\NNNN_pic.png\n"
            f"4. Original aus {ONEDRIVE_DIR} löschen\n"
            f"5. ir.update_field(nr, 'status_pic', 'X', ...) aufrufen\n"
            f"6. sync_status.py + generate_dashboard.py ausführen\n"
            f"7. generate_videos.py --story NR ausführen falls Audio vorhanden"
        )

    # 3. Videos generieren (für bereits bekannte pending stories)
    rows = load_csv_rows()
    pending = pending_videos(rows)
    if pending:
        subprocess.run(
            [sys.executable, "generate_videos.py", "--all"],
            cwd=SCRIPT_DIR,
            check=False,
        )
        subprocess.run([sys.executable, "sync_status.py"], cwd=SCRIPT_DIR, capture_output=True)
        subprocess.run([sys.executable, "generate_dashboard.py"], cwd=SCRIPT_DIR, capture_output=True)
        parts.append(f"✅ {len(pending)} Video(s) generiert + Cloudinary hochgeladen: "
                     + ", ".join(f"#{n}" for n in pending))

    if parts:
        print(json.dumps({"systemMessage": "\n\n".join(parts)}))


if __name__ == "__main__":
    main()
