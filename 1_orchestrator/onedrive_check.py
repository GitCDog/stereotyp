#!/usr/bin/env python3
"""
Läuft bei jedem Claude-Session-Start (via Hook).
Nutzt claude -p CLI (Pro-Subscription) für Bilderkennung. Komplett still.
"""

import csv
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

SCRIPT_DIR   = Path(__file__).parent
ONEDRIVE_DIR = Path(r"C:\Users\slawa\OneDrive\8_stereotypen")
OUTPUT_DIR   = SCRIPT_DIR / "output"
INPUT_FILE   = SCRIPT_DIR / "1_input" / "1_input_file.txt"
PYTHON       = sys.executable

sys.path.insert(0, str(SCRIPT_DIR))


def load_csv_rows() -> list[dict]:
    with open(INPUT_FILE, encoding="utf-8") as f:
        return [r for r in csv.DictReader(f) if r.get("nr", "").strip()]


def identify_image(img_path: Path, rows: list[dict]) -> str | None:
    """Nutzt claude -p CLI um Bild einer Story zuzuordnen."""
    story_list = "\n".join(
        f"{r['nr']}: {r['stereotyp']}" for r in rows
        if r.get("status_pic", "").strip() != "X"
    )
    prompt = (
        f"Schau dir das Bild unter diesem Pfad an: {img_path}\n"
        f"Welche Story-Nummer passt dazu? Antworte NUR mit der Zahl.\n\n"
        f"Verfügbare Stories:\n{story_list}"
    )
    try:
        result = subprocess.run(
            ["claude", "-p", prompt,
             "--allowedTools", "Read",
             "--dangerously-skip-permissions"],
            capture_output=True, text=True, timeout=60,
            encoding="utf-8", errors="replace"
        )
        output = result.stdout.strip()
        match = re.search(r'\b(\d{1,4})\b', output)
        if match:
            return match.group(1)
    except Exception:
        pass
    return None


def process_onedrive(rows: list[dict]):
    if not ONEDRIVE_DIR.exists():
        return
    images = sorted([
        p for ext in ("*.png", "*.jpg", "*.jpeg")
        for p in ONEDRIVE_DIR.glob(ext)
    ])
    if not images:
        return

    try:
        import input_reader as ir
    except ImportError:
        ir = None

    changed = False
    for img in images:
        nr = identify_image(img, rows)
        if not nr:
            continue
        nr_str = f"{int(nr):04d}"
        dest = OUTPUT_DIR / f"{nr_str}_pic{img.suffix.lower()}"
        shutil.copy2(img, dest)
        img.unlink()
        if ir:
            try:
                ir.update_field(nr, "status_pic", "X", str(INPUT_FILE))
            except Exception:
                pass
        changed = True

    if changed:
        subprocess.run([PYTHON, "sync_status.py"], cwd=SCRIPT_DIR, capture_output=True)


def generate_pending_videos(rows: list[dict]):
    pending = [
        r["nr"].strip() for r in rows
        if r.get("status_pic", "").strip() == "X"
        and r.get("status_audio", "").strip() == "X"
        and r.get("status_video", "").strip() != "X"
    ]
    if not pending:
        return
    subprocess.run([PYTHON, "generate_videos.py", "--all"], cwd=SCRIPT_DIR, check=False)
    subprocess.run([PYTHON, "sync_status.py"], cwd=SCRIPT_DIR, capture_output=True)
    subprocess.run([PYTHON, "generate_dashboard.py"], cwd=SCRIPT_DIR, capture_output=True)


def is_port_in_use(port: int) -> bool:
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def restart_server_and_open_dashboard():
    """Startet Server nur wenn nicht läuft; Browser nur einmal pro Tag."""
    import time
    from datetime import date

    LOCK_FILE = SCRIPT_DIR / ".browser_opened"

    if not is_port_in_use(5000):
        subprocess.Popen(
            [PYTHON, "server.py"],
            cwd=SCRIPT_DIR,
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
            close_fds=True,
        )
        time.sleep(2)

    # Browser nur einmal pro Tag öffnen
    today = str(date.today())
    last_opened = LOCK_FILE.read_text().strip() if LOCK_FILE.exists() else ""
    if last_opened != today:
        subprocess.Popen(
            ["cmd", "/c", "start", "", "http://localhost:5000"],
            shell=False
        )
        LOCK_FILE.write_text(today)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--onedrive-only", action="store_true")
    args = parser.parse_args()

    rows = load_csv_rows()
    process_onedrive(rows)

    if not args.onedrive_only:
        rows = load_csv_rows()
        generate_pending_videos(rows)
        restart_server_and_open_dashboard()


if __name__ == "__main__":
    main()
