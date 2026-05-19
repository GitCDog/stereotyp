#!/usr/bin/env python3
"""
Lokaler Backend-Server für das Stereotypen Dashboard.

Verwendung:
  python server.py          # startet auf http://localhost:5000
"""

import csv
import json
import os
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, request, send_file
from dotenv import load_dotenv

load_dotenv()

REPO_ROOT = Path(__file__).parent.parent
REIHENFOLGE_REL = "1_orchestrator/1_input/0_reihenfolge.txt"


def git_push_reihenfolge():
    """Committet und pusht 0_reihenfolge.txt nach GitHub."""
    no_window = subprocess.CREATE_NO_WINDOW
    try:
        diff = subprocess.run(
            ["git", "diff", "--quiet", REIHENFOLGE_REL],
            cwd=str(REPO_ROOT), capture_output=True, creationflags=no_window,
        )
        if diff.returncode == 0:
            return  # keine Änderung
        subprocess.run(["git", "add", REIHENFOLGE_REL], cwd=str(REPO_ROOT),
                       check=True, capture_output=True, creationflags=no_window)
        subprocess.run(
            ["git", "commit", "-m", "fix: Posting-Reihenfolge aktualisiert"],
            cwd=str(REPO_ROOT), check=True, capture_output=True, creationflags=no_window,
        )
        subprocess.run(["git", "push"], cwd=str(REPO_ROOT), check=True,
                       capture_output=True, creationflags=no_window)
    except subprocess.CalledProcessError as e:
        print(f"[!] Git Push Reihenfolge fehlgeschlagen: {e}")

app = Flask(__name__)

_server_start = datetime.now()

# Globaler Task-Status
_task = {"status": "idle", "message": "", "percent": 0, "log": []}
_task_lock = threading.Lock()

# Abort-Mechanismus
_current_proc = None
_proc_lock = threading.Lock()
_abort_flag = threading.Event()


def set_task(status, message, percent, log=None):
    with _task_lock:
        _task["status"] = status
        _task["message"] = message
        _task["percent"] = percent
        if log is not None:
            _task["log"] = log


def append_log(entry: str):
    with _task_lock:
        _task["log"].append(entry)


def parse_range(val: str) -> list[str]:
    """Unterstützt: '8', '4-10', '1,2,5'."""
    val = val.strip()
    if "," in val:
        return [v.strip() for v in val.split(",") if v.strip()]
    if "-" in val:
        parts = val.split("-")
        return [str(i) for i in range(int(parts[0]), int(parts[1]) + 1)]
    return [val]


def run_script(args: list[str]) -> int:
    global _current_proc
    if _abort_flag.is_set():
        return -1
    proc = subprocess.Popen(
        [sys.executable] + args,
        cwd=Path(__file__).parent,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    with _proc_lock:
        _current_proc = proc
    try:
        proc.wait()
    finally:
        with _proc_lock:
            if _current_proc is proc:
                _current_proc = None
    return proc.returncode


def refresh_dashboard():
    run_script(["sync_status.py"])
    run_script(["generate_dashboard.py"])


# ── Seiten ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_file("dashboard.html")


# ── Server-Status ────────────────────────────────────────────────────────────

@app.route("/api/status")
def status():
    uptime = datetime.now() - _server_start
    h, rem = divmod(int(uptime.total_seconds()), 3600)
    m, s = divmod(rem, 60)
    return jsonify({
        "started": _server_start.strftime("%d.%m.%Y %H:%M:%S"),
        "uptime": f"{h:02d}:{m:02d}:{s:02d}",
        "online": True,
    })


# ── Fortschritt ─────────────────────────────────────────────────────────────

@app.route("/api/progress")
def progress():
    with _task_lock:
        return jsonify(dict(_task))


# ── Audio ────────────────────────────────────────────────────────────────────

@app.route("/api/generate-audio", methods=["POST"])
def generate_audio():
    if _task["status"] == "running":
        return jsonify({"error": "Task läuft bereits"}), 409

    body = request.get_json(silent=True) or {}
    story_val = str(body.get("story", "")).strip()

    def task():
        try:
            if story_val:
                numbers = parse_range(story_val)
                candidates = [(nr, "") for nr in numbers]
            else:
                input_file = Path(__file__).parent / "1_input" / "1_input_file.txt"
                with open(input_file, encoding="utf-8") as f:
                    rows = list(csv.DictReader(f))
                candidates = [
                    (r["nr"].strip(), r.get("stereotyp", "").strip()) for r in rows
                    if r.get("status_story") == "X"
                    and r.get("status_audio", "") != "X"
                ]

            total = len(candidates)
            if not total:
                set_task("complete", "Keine ausstehenden Audios.", 100, log=[])
                return

            log = [f"⏳ #{nr}  {name}" for nr, name in candidates]
            set_task("running", f"0/{total} fertig", 5, log=log)

            for i, (nr, name) in enumerate(candidates):
                pct = int((i / total) * 90)
                log[i] = f"🔄 #{nr}  {name}"
                set_task("running", f"{i}/{total} fertig – generiere #{nr}...", pct, log=list(log))
                run_script(["generate_audio.py", "--story", str(nr)])
                log[i] = f"✅ #{nr}  {name}"
                set_task("running", f"{i+1}/{total} fertig", int(((i+1) / total) * 90), log=list(log))

            set_task("running", "Dashboard aktualisieren...", 95, log=list(log))
            refresh_dashboard()
            set_task("complete", f"Fertig! {total} Audio(s) generiert.", 100, log=list(log))
        except Exception as e:
            set_task("error", str(e), 0)

    set_task("running", "Starte...", 5, log=[])
    threading.Thread(target=task, daemon=True).start()
    return jsonify({"status": "started"})


# ── Audio für alle Pics ──────────────────────────────────────────────────────

@app.route("/api/generate-audio-for-pics", methods=["POST"])
def generate_audio_for_pics():
    if _task["status"] == "running":
        return jsonify({"error": "Task läuft bereits"}), 409

    def task():
        try:
            import csv
            input_file = Path(__file__).parent / "1_input" / "1_input_file.txt"
            with open(input_file, encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            candidates = [
                (r["nr"].strip(), r.get("stereotyp", "").strip()) for r in rows
                if r.get("status_pic") == "X"
                and r.get("status_audio", "") != "X"
                and r.get("status_story", "") == "X"
            ]
            total = len(candidates)
            if not total:
                set_task("complete", "Keine ausstehenden Audios für vorhandene Bilder.", 100, log=[])
                return

            log = [f"⏳ #{nr}  {name}" for nr, name in candidates]
            set_task("running", f"0/{total} fertig", 5, log=log)

            for i, (nr, name) in enumerate(candidates):
                pct = int(((i) / total) * 90)
                log[i] = f"🔄 #{nr}  {name}"
                set_task("running", f"{i}/{total} fertig – generiere #{nr}...", pct, log=list(log))
                run_script(["generate_audio.py", "--story", nr])
                log[i] = f"✅ #{nr}  {name}"
                set_task("running", f"{i+1}/{total} fertig", int(((i+1) / total) * 90), log=list(log))

            set_task("running", "Dashboard aktualisieren...", 95, log=list(log))
            refresh_dashboard()
            set_task("complete", f"Fertig! {total} Audio(s) generiert.", 100, log=list(log))
        except Exception as e:
            set_task("error", str(e), 0)

    set_task("running", "Starte...", 5, log=[])
    threading.Thread(target=task, daemon=True).start()
    return jsonify({"status": "started"})


# ── Bild ─────────────────────────────────────────────────────────────────────

@app.route("/api/generate-picture", methods=["POST"])
def generate_picture():
    if _task["status"] == "running":
        return jsonify({"error": "Task läuft bereits"}), 409

    body = request.get_json(silent=True) or {}
    story_val = str(body.get("story", "")).strip()

    def task():
        try:
            if story_val:
                set_task("running", f"Bild für {story_val}...", 10)
                run_script(["generate_pictures.py", story_val])
            set_task("running", "Dashboard aktualisieren...", 95)
            refresh_dashboard()
            set_task("complete", "Fertig!", 100)
        except Exception as e:
            set_task("error", str(e), 0)

    set_task("running", "Starte...", 5)
    threading.Thread(target=task, daemon=True).start()
    return jsonify({"status": "started"})


# ── Neue Story erstellen ─────────────────────────────────────────────────────

@app.route("/api/create-story", methods=["POST"])
def create_story():
    if _task["status"] == "running":
        return jsonify({"error": "Task läuft bereits"}), 409

    body = request.get_json(silent=True) or {}
    stereotyp = body.get("stereotyp", "").strip()
    stichworte = body.get("stichworte", "").strip()
    position = body.get("position", "")  # "start", "end", Zahl, oder leer = nicht einreihen

    if not stereotyp:
        return jsonify({"error": "Stereotyp fehlt"}), 400

    def task():
        try:
            input_file = Path(__file__).parent / "1_input" / "1_input_file.txt"
            with open(input_file, encoding="utf-8") as f:
                rows = list(csv.DictReader(f))

            # Prüfen ob Stereotyp schon existiert
            existing = next((r for r in rows if r.get("stereotyp", "").strip().lower() == stereotyp.lower()), None)
            if existing:
                new_nr = existing["nr"].strip()
                log = [f"ℹ️ #{new_nr} '{stereotyp}' existiert bereits – Story wird neu generiert"]
                set_task("running", f"Regeneriere Story #{new_nr}...", 10, log=log)
            else:
                max_nr = max(int(r["nr"].strip()) for r in rows if r.get("nr", "").strip().isdigit())
                new_nr = str(max_nr + 1)
                fieldnames = list(rows[0].keys())
                new_row = {k: "" for k in fieldnames}
                new_row["nr"] = new_nr
                new_row["stereotyp"] = stereotyp
                with open(input_file, "a", encoding="utf-8", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writerow(new_row)
                log = [f"📋 #{new_nr} '{stereotyp}' in CSV eingetragen"]
                if stichworte:
                    log.append(f"🔑 Stichworte: {stichworte}")
                set_task("running", f"Story #{new_nr} generieren...", 10, log=log)

            log.append(f"⏳ Story-Text via Claude generieren...")
            set_task("running", f"Story #{new_nr} via Claude generieren...", 30, log=list(log))
            args = ["generate_stories.py", "--story", new_nr]
            if stichworte:
                args += ["--stichworte", stichworte]
            run_script(args)
            log.append(f"✅ Story-Text gespeichert")

            log.append(f"⏳ Audio via ElevenLabs vertonen...")
            set_task("running", f"Audio für #{new_nr} generieren...", 65, log=list(log))
            run_script(["generate_audio.py", "--story", new_nr])
            log.append(f"✅ Audio fertig")

            log.append(f"⏳ Caption via Claude generieren...")
            set_task("running", f"Caption für #{new_nr} generieren...", 80, log=list(log))
            caption_args = ["generate_captions.py", "--story", new_nr]
            if stichworte:
                caption_args += ["--stichworte", stichworte]
            run_script(caption_args)
            log.append(f"✅ Caption fertig")

            if position:
                reihenfolge_path = Path(__file__).parent / "1_input" / "0_reihenfolge.txt"
                lines = []
                if reihenfolge_path.exists():
                    lines = [l.strip() for l in reihenfolge_path.read_text(encoding="utf-8").splitlines() if l.strip()]
                lines = [l for l in lines if l != new_nr]
                if position == "start":
                    lines.insert(0, new_nr)
                    log.append(f"📋 #{new_nr} an den Anfang der Reihenfolge gesetzt")
                elif position == "end":
                    lines.append(new_nr)
                    log.append(f"📋 #{new_nr} ans Ende der Reihenfolge gesetzt")
                else:
                    try:
                        pos = max(0, int(position) - 1)
                        lines.insert(pos, new_nr)
                        log.append(f"📋 #{new_nr} an Position {position} der Reihenfolge gesetzt")
                    except Exception:
                        lines.append(new_nr)
                reihenfolge_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
                git_push_reihenfolge()

            set_task("running", "GPT-Prompt aktualisieren...", 88, log=list(log))
            onedrive_out = r"C:\Users\slawa\OneDrive\8_stereotypen\gpt_prompts.txt"
            run_script(["generate_gpt_prompt.py", "--no-pic", "--out", onedrive_out])
            log.append(f"📝 GPT-Prompt aktualisiert")

            log.append(f"📷 Bild muss noch manuell erstellt werden (GPT)")
            set_task("running", "Dashboard aktualisieren...", 92, log=list(log))
            refresh_dashboard()
            set_task("complete", f"Story #{new_nr} '{stereotyp}' erstellt + vertont!", 100, log=list(log))
        except Exception as e:
            set_task("error", str(e), 0)

    set_task("running", "Starte...", 5, log=[])
    threading.Thread(target=task, daemon=True).start()
    return jsonify({"status": "started"})


# ── Story ────────────────────────────────────────────────────────────────────

@app.route("/api/generate-story", methods=["POST"])
def generate_story():
    if _task["status"] == "running":
        return jsonify({"error": "Task läuft bereits"}), 409

    body = request.get_json(silent=True) or {}
    story_val = str(body.get("story", "")).strip()

    def task():
        try:
            if story_val:
                numbers = parse_range(story_val)
                total = len(numbers)
                for i, nr in enumerate(numbers):
                    set_task("running", f"Story #{nr}...", int((i / total) * 90))
                    run_script(["generate_stories.py", "--story", str(nr)])
            else:
                set_task("running", "Nächste ausstehende Story...", 20)
                run_script(["generate_stories.py"])
            set_task("running", "Dashboard aktualisieren...", 95)
            refresh_dashboard()
            set_task("complete", "Fertig!", 100)
        except Exception as e:
            set_task("error", str(e), 0)

    set_task("running", "Starte...", 5)
    threading.Thread(target=task, daemon=True).start()
    return jsonify({"status": "started"})


# ── Caption ──────────────────────────────────────────────────────────────────

@app.route("/api/generate-caption", methods=["POST"])
def generate_caption():
    if _task["status"] == "running":
        return jsonify({"error": "Task läuft bereits"}), 409

    body = request.get_json(silent=True) or {}
    story_val = str(body.get("story", "")).strip()

    def task():
        try:
            if story_val:
                numbers = parse_range(story_val)
                total = len(numbers)
                for i, nr in enumerate(numbers):
                    set_task("running", f"Caption #{nr}...", int((i / total) * 90))
                    run_script(["generate_captions.py", "--story", str(nr)])
            else:
                set_task("running", "Alle ausstehenden Captions...", 10)
                run_script(["generate_captions.py"])
            set_task("running", "Dashboard aktualisieren...", 95)
            refresh_dashboard()
            set_task("complete", "Fertig!", 100)
        except Exception as e:
            set_task("error", str(e), 0)

    set_task("running", "Starte...", 5)
    threading.Thread(target=task, daemon=True).start()
    return jsonify({"status": "started"})


# ── Video ────────────────────────────────────────────────────────────────────

@app.route("/api/generate-video", methods=["POST"])
def generate_video():
    if _task["status"] == "running":
        return jsonify({"error": "Task läuft bereits"}), 409

    body = request.get_json(silent=True) or {}
    story_val = str(body.get("story", "")).strip()

    def task():
        _abort_flag.clear()
        try:
            input_file = Path(__file__).parent / "1_input" / "1_input_file.txt"
            if story_val:
                numbers = parse_range(story_val)
                with open(input_file, encoding="utf-8") as f:
                    all_rows = {r["nr"].strip(): r.get("stereotyp", "").strip()
                                for r in csv.DictReader(f)}
                candidates = [(nr, all_rows.get(nr, "")) for nr in numbers]
            else:
                with open(input_file, encoding="utf-8") as f:
                    rows = list(csv.DictReader(f))
                candidates = [
                    (r["nr"].strip(), r.get("stereotyp", "").strip()) for r in rows
                    if r.get("status_audio") == "X"
                    and r.get("status_pic") == "X"
                    and r.get("status_video", "") != "X"
                ]

            total = len(candidates)
            if not total:
                set_task("complete", "Keine Videos ausstehend.", 100, log=[])
                return

            log = [f"⏳ #{nr}  {name}" for nr, name in candidates]
            set_task("running", f"0/{total} Videos fertig", 5, log=log)

            for i, (nr, name) in enumerate(candidates):
                if _abort_flag.is_set():
                    set_task("idle", "Abgebrochen", 0, log=list(log))
                    return
                pct = int((i / total) * 88) + 5
                log[i] = f"🎬 #{nr}  {name}"
                set_task("running", f"{i}/{total} – rendere #{nr}: {name}...", pct, log=list(log))
                run_script(["generate_videos.py", "--story", str(nr)])
                if _abort_flag.is_set():
                    log[i] = f"⏹️ #{nr}  {name}"
                    set_task("idle", "Abgebrochen", 0, log=list(log))
                    return
                log[i] = f"✅ #{nr}  {name}"
                set_task("running", f"{i+1}/{total} fertig", int(((i + 1) / total) * 88) + 5, log=list(log))

            set_task("running", "Dashboard aktualisieren...", 97, log=list(log))
            refresh_dashboard()
            set_task("complete", f"Fertig! {total} Video(s) erstellt.", 100, log=list(log))
        except Exception as e:
            set_task("error", str(e), 0)

    _abort_flag.clear()
    set_task("running", "Starte...", 5, log=[])
    threading.Thread(target=task, daemon=True).start()
    return jsonify({"status": "started"})


# ── Bilder via Playwright (ChatGPT) ─────────────────────────────────────────

@app.route("/api/generate-pictures-playwright", methods=["POST"])
def generate_pictures_playwright():
    if _task["status"] == "running":
        return jsonify({"error": "Task läuft bereits"}), 409

    body = request.get_json(silent=True) or {}
    story_val = str(body.get("story", "")).strip()

    def task():
        try:
            if not story_val:
                set_task("error", "Story-Nummer oder Bereich angeben (z.B. 49 oder 49,50,51)", 0)
                return
            set_task("running", f"Playwright: Bilder für {story_val}...", 10)
            run_script(["generate_pictures_playwright.py", "--story", story_val])
            set_task("running", "Dashboard aktualisieren...", 95)
            refresh_dashboard()
            set_task("complete", f"Fertig! Bilder für {story_val} generiert.", 100)
        except Exception as e:
            set_task("error", str(e), 0)

    set_task("running", "Starte Playwright...", 5)
    threading.Thread(target=task, daemon=True).start()
    return jsonify({"status": "started"})


# ── Instagram Post ───────────────────────────────────────────────────────────

@app.route("/api/instagram-post", methods=["POST"])
def instagram_post():
    if _task["status"] == "running":
        return jsonify({"error": "Task läuft bereits"}), 409

    def task():
        try:
            set_task("running", "Instagram Post...", 20)
            run_script(["instagram_poster.py"])
            set_task("running", "Dashboard aktualisieren...", 95)
            refresh_dashboard()
            set_task("complete", "Fertig!", 100)
        except Exception as e:
            set_task("error", str(e), 0)

    set_task("running", "Starte...", 5)
    threading.Thread(target=task, daemon=True).start()
    return jsonify({"status": "started"})


# ── Refresh (Datei-Scan + Dashboard + neue Stories) ─────────────────────────

@app.route("/api/refresh", methods=["POST"])
def refresh():
    if _task["status"] == "running":
        return jsonify({"error": "Task läuft bereits"}), 409

    def task():
        _abort_flag.clear()
        log = []
        try:
            onedrive_dir = Path(r"C:\Users\slawa\OneDrive\8_stereotypen")
            def _count_imgs(d): return sum(len(list(d.glob(f"*.{e}"))) for e in ("png","jpg","jpeg")) if d.exists() else 0
            imgs_before = _count_imgs(onedrive_dir)

            set_task("running", "OneDrive: neue Bilder identifizieren...", 10, log=list(log))
            run_script(["onedrive_check.py", "--onedrive-only"])

            imgs_after = _count_imgs(onedrive_dir)
            processed = imgs_before - imgs_after
            if processed > 0:
                log.append(f"🖼️ {processed} Bild(er) aus OneDrive identifiziert und verarbeitet")
            else:
                log.append("✅ OneDrive: Keine neuen Bilder")

            set_task("running", "Sammelsurium → 1_input/ extrahieren...", 35, log=list(log))
            import sync_status as ss
            new_from_sammelsurium = ss.check_sammelsurium()
            if new_from_sammelsurium:
                log.append(f"📄 {new_from_sammelsurium} neue Stories aus Sammelsurium extrahiert")
            else:
                log.append("✅ Sammelsurium: Keine neuen Stories")

            set_task("running", "Dateien scannen & CSV aktualisieren...", 65, log=list(log))
            run_script(["sync_status.py"])
            log.append("🔄 CSV und Dateistatus synchronisiert")

            set_task("running", "GPT-Prompts für fehlende Bilder schreiben...", 80, log=list(log))
            onedrive_out = r"C:\Users\slawa\OneDrive\8_stereotypen\gpt_prompts.txt"
            run_script(["generate_gpt_prompt.py", "--no-pic", "--out", onedrive_out])
            log.append("📝 GPT Prompts aktualisiert")

            set_task("running", "Dashboard aktualisieren...", 90, log=list(log))
            refresh_dashboard()
            log.append("✅ Dashboard aktualisiert")

            msg = f"Fertig! {new_from_sammelsurium} neue Stories extrahiert." if new_from_sammelsurium else "Fertig!"
            set_task("complete", msg, 100, log=list(log))
        except Exception as e:
            set_task("error", str(e), 0)

    _abort_flag.clear()
    set_task("running", "Starte Refresh...", 5, log=[])
    threading.Thread(target=task, daemon=True).start()
    return jsonify({"status": "started"})


# ── Restart ──────────────────────────────────────────────────────────────────

@app.route("/api/restart", methods=["POST"])
def restart_server():
    def do_restart():
        import time, os
        time.sleep(1)
        subprocess.Popen(
            [sys.executable, "server.py"],
            cwd=Path(__file__).parent,
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
        )
        time.sleep(0.5)
        os._exit(0)
    threading.Thread(target=do_restart, daemon=True).start()
    return jsonify({"status": "restarting"})


# ── Abort ────────────────────────────────────────────────────────────────────

@app.route("/api/abort", methods=["POST"])
def abort_task():
    _abort_flag.set()
    with _proc_lock:
        proc = _current_proc
    if proc and proc.poll() is None:
        proc.terminate()
    with _task_lock:
        _task["status"] = "idle"
        _task["message"] = "Abgebrochen"
        _task["percent"] = 0
    return jsonify({"status": "aborted"})


# ── Reihenfolge ──────────────────────────────────────────────────────────────

def _video_on_cloudinary(nr) -> bool:
    """Prüft via CSV ob Video auf Cloudinary liegt.
    Bedingung: status_video=X und insta_post leer (noch nicht gepostet/gelöscht)."""
    input_file = Path(__file__).parent / "1_input" / "1_input_file.txt"
    nr_str = str(int(str(nr).strip()))
    try:
        with open(input_file, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if str(row.get("nr", "")).strip() == nr_str:
                    return row.get("status_video", "").strip() == "X" and not row.get("insta_post", "").strip()
    except Exception:
        pass
    return False


@app.route("/api/cloudinary-check")
def cloudinary_check():
    nr = request.args.get("nr", "").strip()
    if not nr:
        return jsonify({"error": "nr fehlt"}), 400
    exists = _video_on_cloudinary(nr)
    return jsonify({"exists": exists, "nr": nr})


@app.route("/api/reihenfolge", methods=["GET"])
def get_reihenfolge():
    path = Path(__file__).parent / "1_input" / "0_reihenfolge.txt"
    lines = []
    if path.exists():
        lines = [l.strip() for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    return jsonify({"reihenfolge": lines})


@app.route("/api/reihenfolge", methods=["POST"])
def set_reihenfolge():
    body = request.get_json(silent=True) or {}
    nr = str(body.get("nr", "")).strip()
    position = body.get("position", "end")  # "start", "end", oder Zahl

    if not nr:
        return jsonify({"error": "nr fehlt"}), 400

    try: nr = str(int(nr))
    except ValueError: pass

    path = Path(__file__).parent / "1_input" / "0_reihenfolge.txt"
    lines = []
    if path.exists():
        lines = [l.strip() for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]

    lines = [l for l in lines if l != nr]  # doppelte entfernen

    if position == "start":
        lines.insert(0, nr)
    elif position == "end":
        lines.append(nr)
    else:
        try:
            pos = max(0, int(position) - 1)
            lines.insert(pos, nr)
        except Exception:
            lines.append(nr)

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    threading.Thread(target=git_push_reihenfolge, daemon=True).start()
    return jsonify({"status": "ok", "reihenfolge": lines})


@app.route("/api/reihenfolge/remove", methods=["POST"])
def remove_reihenfolge():
    body = request.get_json(silent=True) or {}
    nr = str(body.get("nr", "")).strip()
    if not nr:
        return jsonify({"error": "nr fehlt"}), 400

    path = Path(__file__).parent / "1_input" / "0_reihenfolge.txt"
    if path.exists():
        def _norm(s):
            try: return str(int(s))
            except: return s
        nr_norm = _norm(nr)
        lines = [l.strip() for l in path.read_text(encoding="utf-8").splitlines()
                 if l.strip() and _norm(l.strip()) != nr_norm]
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    threading.Thread(target=git_push_reihenfolge, daemon=True).start()
    return jsonify({"status": "ok"})


# ── Mark Posted ──────────────────────────────────────────────────────────────

@app.route("/api/mark-posted", methods=["POST"])
def mark_posted():
    body = request.get_json(silent=True) or {}
    nr = body.get("nr")
    if not nr:
        return jsonify({"error": "nr fehlt"}), 400
    import input_reader as ir
    ir.update_field(int(nr), "insta_post", "X", "1_input/1_input_file.txt")
    refresh_dashboard()
    return jsonify({"status": "ok"})


@app.route("/api/unmark-posted", methods=["POST"])
def unmark_posted():
    body = request.get_json(silent=True) or {}
    nr = body.get("nr")
    if not nr:
        return jsonify({"error": "nr fehlt"}), 400
    import input_reader as ir
    ir.update_field(int(nr), "insta_post", "", "1_input/1_input_file.txt")
    refresh_dashboard()
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    print("[+] Dashboard: http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
