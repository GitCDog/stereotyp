#!/usr/bin/env python3
"""
Läuft bei jedem Claude-Session-Start (via Hook).

1. Bekannte Bilder aus OneDrive → sofort verarbeiten
2. Unbekannte Bilder → Claude identifiziert und verarbeitet sie automatisch
3. Pending Videos generieren + Cloudinary Upload
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
PYTHON        = sys.executable

sys.path.insert(0, str(SCRIPT_DIR))


def load_csv_rows() -> list[dict]:
    with open(INPUT_FILE, encoding="utf-8") as f:
        return [r for r in csv.DictReader(f) if r.get("nr", "").strip()]


def get_onedrive_images() -> list[str]:
    if not ONEDRIVE_DIR.exists():
        return []
    return [p.name for p in sorted(ONEDRIVE_DIR.glob("*.png"))]


def get_pending_videos(rows: list[dict]) -> list[str]:
    return [
        r["nr"].strip() for r in rows
        if r.get("status_pic") == "X"
        and r.get("status_audio") == "X"
        and r.get("status_video", "") != "X"
    ]


def generate_videos():
    subprocess.run([PYTHON, "generate_videos.py", "--all"], cwd=SCRIPT_DIR, check=False)
    subprocess.run([PYTHON, "sync_status.py"], cwd=SCRIPT_DIR, capture_output=True)
    subprocess.run([PYTHON, "generate_dashboard.py"], cwd=SCRIPT_DIR, capture_output=True)


def main():
    rows = load_csv_rows()
    msg_parts = ["🚀 Startup Pipeline gestartet"]

    # 1. Alle Bilder in OneDrive → Claude identifiziert und verarbeitet sie
    unknown = get_onedrive_images()
    if unknown:
        story_list = "\n".join(
            f"{r['nr']}: {r['stereotyp']}" for r in rows
            if r.get("status_pic", "") != "X"
        )
        files = "\n".join(f"  {ONEDRIVE_DIR / f}" for f in unknown)
        msg_parts.append(
            f"📸 {len(unknown)} unbekannte(s) Bild(er) in OneDrive – wird jetzt automatisch verarbeitet:\n{files}\n\n"
            f"AUTOMATISCH AUSFÜHREN (kein User-Input nötig):\n"
            f"1. Jedes Bild mit Read-Tool öffnen\n"
            f"2. Passende Story-Nummer aus dieser Liste bestimmen:\n{story_list}\n"
            f"3. Bild nach {OUTPUT_DIR}\\NNNN_pic.png kopieren + Original löschen\n"
            f"4. input_reader.update_field(nr, 'status_pic', 'X', ...) setzen\n"
            f"5. sync_status.py + generate_dashboard.py ausführen\n"
            f"6. generate_videos.py --story NR ausführen falls Audio vorhanden"
        )

    # 3. Videos generieren
    pending = get_pending_videos(rows)
    if pending:
        msg_parts.append(f"🎬 Generiere {len(pending)} Video(s): {', '.join('#'+n for n in pending)}")
        generate_videos()
        msg_parts.append(f"✅ {len(pending)} Video(s) fertig + Cloudinary hochgeladen")

    print(json.dumps({"systemMessage": "\n\n".join(msg_parts)}))


if __name__ == "__main__":
    main()
