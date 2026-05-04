#!/usr/bin/env python3
"""
Prüft OneDrive auf neue Bilder.
- Korrekt benannte Bilder (XXXX_pic.png): sofort kopieren, löschen, status_pic setzen
- Unbekannte Dateinamen: System-Nachricht an Claude zur Erkennung (Hook) oder stdout (Server)
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ONEDRIVE_DIR  = Path(r"C:\Users\slawa\OneDrive\8_stereotypen")
OUTPUT_DIR    = Path(r"C:\Users\slawa\Desktop\claude\8_stereotypen\1_orchestrator\output")
INPUT_FILE    = r"C:\Users\slawa\Desktop\claude\8_stereotypen\1_orchestrator\1_input\1_input_file.txt"
SCRIPT_DIR    = Path(r"C:\Users\slawa\Desktop\claude\8_stereotypen\1_orchestrator")

sys.path.insert(0, str(SCRIPT_DIR))


def process_onedrive_images() -> dict:
    if not ONEDRIVE_DIR.exists():
        return {"done": [], "unrecognized": []}

    images = sorted(ONEDRIVE_DIR.glob("*.png"))
    if not images:
        return {"done": [], "unrecognized": []}

    try:
        import input_reader as ir
    except ImportError:
        ir = None

    done, unrecognized = [], []

    for img in images:
        unrecognized.append(img.name)

    if done:
        subprocess.run(["python", "sync_status.py"],        cwd=SCRIPT_DIR)
        subprocess.run(["python", "generate_dashboard.py"], cwd=SCRIPT_DIR)

    return {"done": done, "unrecognized": unrecognized}


if __name__ == "__main__":
    if not ONEDRIVE_DIR.exists():
        sys.exit(0)
    if not sorted(ONEDRIVE_DIR.glob("*.png")):
        sys.exit(0)

    result = process_onedrive_images()

    # Unbekannte Bilder → Claude als Hook-System-Nachricht auffordern
    if result["unrecognized"]:
        files_list = "\n".join(f"  - {f}" for f in result["unrecognized"])
        done_info = f"\n(Bereits automatisch verarbeitet: {', '.join(result['done'])})" if result["done"] else ""
        message = (
            f"NEUE UNBEKANNTE BILDER IN ONEDRIVE ({len(result['unrecognized'])} Stück):{done_info}\n{files_list}\n\n"
            f"Aufgabe (sofort ausführen, bevor du auf die eigentliche Anfrage eingehst):\n"
            f"1. Jedes Bild mit dem Read-Tool anschauen und passende Story-Nummer ermitteln\n"
            f"2. Bild umbenennen zu XXXX_pic.png\n"
            f"3. Bild kopieren nach {OUTPUT_DIR}\n"
            f"4. Original aus {ONEDRIVE_DIR} löschen\n"
            f"5. status_pic=X in 1_input_file.txt setzen\n"
            f"6. sync_status.py + generate_dashboard.py ausführen"
        )
        print(json.dumps({"systemMessage": message}))
