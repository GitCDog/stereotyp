#!/usr/bin/env python3
"""
Wird bei jedem Claude-Session-Start ausgeführt (via Hook).

Ablauf (vollautomatisch, keine manuelle Eingriffe):
1. OneDrive auf neue Bilder prüfen
   - Korrekt benannte (NNNN_pic.png) → sofort verschieben
   - Unbekannte Namen → Claude Vision API identifiziert sie, benennt um, verschiebt
2. Videos generieren für alle Stories mit Bild + Audio aber ohne Video
3. Kurze Info-Zusammenfassung als systemMessage ausgeben
"""

import base64
import csv
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR   = Path(__file__).parent
ONEDRIVE_DIR = Path(r"C:\Users\slawa\OneDrive\8_stereotypen")
OUTPUT_DIR   = SCRIPT_DIR / "output"
INPUT_FILE   = SCRIPT_DIR / "1_input" / "1_input_file.txt"
NAMED_PATTERN = re.compile(r'^\d{4}_pic\.png$')

sys.path.insert(0, str(SCRIPT_DIR))


def load_csv_rows() -> list[dict]:
    with open(INPUT_FILE, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def identify_image_with_claude(img_path: Path, rows: list[dict]) -> str | None:
    """Nutzt Claude Vision API um das Bild einer Story-Nummer zuzuordnen."""
    try:
        import anthropic, os
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

        img_data = base64.standard_b64encode(img_path.read_bytes()).decode("utf-8")

        # Stereotypen-Liste für Claude
        story_list = "\n".join(
            f"{r['nr']}: {r['stereotyp']}" for r in rows
            if r.get("status_pic", "") != "X"
        )

        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=50,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": "image/png", "data": img_data},
                    },
                    {
                        "type": "text",
                        "text": (
                            f"Dieses Bild gehört zu einer der folgenden Stereotypen-Stories. "
                            f"Antworte NUR mit der Nummer (z.B. '42'), nichts sonst.\n\n{story_list}"
                        ),
                    },
                ],
            }],
        )
        nr = response.content[0].text.strip().strip(".")
        if nr.isdigit():
            return nr
    except Exception as e:
        print(f"[!] Vision-API Fehler: {e}", file=sys.stderr)
    return None


def process_onedrive_images(rows: list[dict]) -> tuple[list[str], list[str]]:
    """Verarbeitet alle Bilder in OneDrive. Gibt (done, failed) zurück."""
    if not ONEDRIVE_DIR.exists():
        return [], []

    images = sorted(ONEDRIVE_DIR.glob("*.png"))
    if not images:
        return [], []

    try:
        import input_reader as ir
    except ImportError:
        ir = None

    done, failed = [], []

    for img in images:
        if NAMED_PATTERN.match(img.name):
            # Korrekt benannt → direkt verschieben
            nr_int = int(img.stem.replace("_pic", ""))
            nr_str = f"{nr_int:04d}"
            dest = OUTPUT_DIR / f"{nr_str}_pic.png"
            shutil.copy2(img, dest)
            img.unlink()
            done.append(f"{nr_str}_pic.png (bereits korrekt benannt)")
            if ir:
                try:
                    ir.update_field(str(nr_int), "status_pic", "X", str(INPUT_FILE))
                except Exception:
                    pass
        else:
            # Unbekannt → Claude Vision identifiziert
            print(f"[*] Identifiziere: {img.name} ...", file=sys.stderr)
            nr = identify_image_with_claude(img, rows)
            if nr:
                nr_str = f"{int(nr):04d}"
                dest = OUTPUT_DIR / f"{nr_str}_pic.png"
                shutil.copy2(img, dest)
                img.unlink()
                done.append(f"{nr_str}_pic.png (erkannt aus '{img.name}')")
                if ir:
                    try:
                        ir.update_field(nr, "status_pic", "X", str(INPUT_FILE))
                    except Exception:
                        pass
            else:
                failed.append(img.name)

    if done:
        subprocess.run([sys.executable, "sync_status.py"], cwd=SCRIPT_DIR, capture_output=True)

    return done, failed


def pending_videos(rows: list[dict]) -> list[str]:
    return [
        r["nr"].strip() for r in rows
        if r.get("status_pic") == "X"
        and r.get("status_audio") == "X"
        and r.get("status_video", "") != "X"
    ]


def main():
    summary = []

    rows = load_csv_rows()

    # 1. OneDrive-Bilder verarbeiten
    if ONEDRIVE_DIR.exists() and list(ONEDRIVE_DIR.glob("*.png")):
        done, failed = process_onedrive_images(rows)
        if done:
            summary.append(f"✅ {len(done)} Bild(er) aus OneDrive übernommen:\n" +
                           "\n".join(f"  • {f}" for f in done))
        if failed:
            summary.append(f"⚠️ {len(failed)} Bild(er) konnten nicht identifiziert werden:\n" +
                           "\n".join(f"  • {f}" for f in failed))
        # Rows neu laden nach Änderungen
        rows = load_csv_rows()

    # 2. Videos generieren
    pending = pending_videos(rows)
    if pending:
        summary.append(f"🎬 Videogenerierung gestartet für {len(pending)} Story(s): " +
                       ", ".join(f"#{n}" for n in pending))
        subprocess.run(
            [sys.executable, "generate_videos.py", "--all"],
            cwd=SCRIPT_DIR,
            check=False,
        )
        subprocess.run([sys.executable, "sync_status.py"], cwd=SCRIPT_DIR, capture_output=True)
        subprocess.run([sys.executable, "generate_dashboard.py"], cwd=SCRIPT_DIR, capture_output=True)
        summary.append(f"✅ {len(pending)} Video(s) fertig + auf Cloudinary hochgeladen.")

    if summary:
        print(json.dumps({"systemMessage": "🤖 Startup-Pipeline abgeschlossen:\n\n" + "\n\n".join(summary)}))


if __name__ == "__main__":
    main()
