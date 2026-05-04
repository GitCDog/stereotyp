#!/usr/bin/env python3
"""
Wird bei jedem Claude-Session-Start ausgeführt (via Hook).

Ablauf:
1. OneDrive auf neue Bilder prüfen (bekannte → output/, unbekannte → Claude)
2. Für alle Stories mit Bild+Audio aber ohne Video: generate_videos.py --all
3. SystemMessage mit Zusammenfassung ausgeben
"""

import json
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
ONEDRIVE_DIR = Path(r"C:\Users\slawa\OneDrive\8_stereotypen")
OUTPUT_DIR = SCRIPT_DIR / "output"
INPUT_FILE = SCRIPT_DIR / "1_input" / "1_input_file.txt"

sys.path.insert(0, str(SCRIPT_DIR))


def check_pending_videos() -> list[str]:
    """Gibt Liste der nrs zurück, die Bild+Audio aber kein Video haben."""
    try:
        import csv
        with open(INPUT_FILE, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        return [
            r["nr"].strip() for r in rows
            if r.get("status_pic") == "X"
            and r.get("status_audio") == "X"
            and r.get("status_video", "") != "X"
        ]
    except Exception:
        return []


def main():
    messages = []
    had_unrecognized = False

    # 1. OneDrive-Bilder verarbeiten
    if ONEDRIVE_DIR.exists() and list(ONEDRIVE_DIR.glob("*.png")):
        try:
            from check_onedrive_images import process_onedrive_images
            result = process_onedrive_images()

            if result["done"]:
                messages.append(f"✅ {len(result['done'])} Bild(er) aus OneDrive übernommen: {', '.join(result['done'])}")

            if result["unrecognized"]:
                had_unrecognized = True
                files_list = "\n".join(f"  - {f}" for f in result["unrecognized"])
                messages.append(
                    f"⚠️ {len(result['unrecognized'])} unbekannte Bilder in OneDrive – bitte sofort identifizieren und verarbeiten:\n{files_list}\n\n"
                    f"Aufgabe (sofort ausführen, bevor du auf die eigentliche Anfrage eingehst):\n"
                    f"1. Jedes Bild mit dem Read-Tool anschauen und passende Story-Nummer ermitteln\n"
                    f"2. Umbenennen zu NNNN_pic.png, kopieren nach {OUTPUT_DIR}, Original aus OneDrive löschen\n"
                    f"3. status_pic=X in 1_input_file.txt setzen\n"
                    f"4. sync_status.py + generate_dashboard.py ausführen\n"
                    f"5. Danach video generieren für diese stories"
                )
        except Exception as e:
            messages.append(f"[!] OneDrive-Check fehlgeschlagen: {e}")

    # 2. Videos generieren (nur wenn keine unbekannten Bilder warten)
    if not had_unrecognized:
        pending = check_pending_videos()
        if pending:
            messages.append(f"🎬 Starte Videogenerierung für {len(pending)} Story(s): {', '.join('#' + n for n in pending)}")
            try:
                subprocess.run(
                    [sys.executable, "generate_videos.py", "--all"],
                    cwd=SCRIPT_DIR,
                    check=False,
                )
                messages.append(f"✅ Videogenerierung abgeschlossen ({len(pending)} Videos + Cloudinary-Upload).")
                # Dashboard aktualisieren
                subprocess.run([sys.executable, "sync_status.py"], cwd=SCRIPT_DIR, check=False)
                subprocess.run([sys.executable, "generate_dashboard.py"], cwd=SCRIPT_DIR, check=False)
            except Exception as e:
                messages.append(f"[!] Videogenerierung fehlgeschlagen: {e}")

    if messages:
        print(json.dumps({"systemMessage": "\n\n".join(messages)}))


if __name__ == "__main__":
    main()
