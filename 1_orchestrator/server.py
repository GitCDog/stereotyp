#!/usr/bin/env python3
"""
Lokaler Backend-Server für das Stereotypen Dashboard.

Verwendung:
  python server.py          # startet auf http://localhost:5000
"""

import json
import subprocess
import sys
import threading
from pathlib import Path

from flask import Flask, jsonify, request, send_file
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Globaler Task-Status
_task = {"status": "idle", "message": "", "percent": 0}
_task_lock = threading.Lock()


def set_task(status, message, percent):
    with _task_lock:
        _task["status"] = status
        _task["message"] = message
        _task["percent"] = percent


def parse_range(val: str) -> list[str]:
    """Unterstützt: '8', '4-10', '100_01', '100_01,100_02', '100_01-100_05'."""
    import re
    val = val.strip()
    if "," in val:
        return [v.strip() for v in val.split(",") if v.strip()]
    m = re.match(r'^(\d+)_(\d+)-\d+_(\d+)$', val)
    if m:
        prefix, start, end = m.group(1), int(m.group(2)), int(m.group(3))
        width = len(m.group(2))
        return [f"{prefix}_{i:0{width}d}" for i in range(start, end + 1)]
    if "-" in val and "_" not in val:
        parts = val.split("-")
        return [str(i) for i in range(int(parts[0]), int(parts[1]) + 1)]
    return [val]


def run_script(args: list[str]):
    subprocess.run([sys.executable] + args, cwd=Path(__file__).parent)


def refresh_dashboard():
    run_script(["sync_status.py"])
    run_script(["generate_dashboard.py"])


# ── Seiten ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_file("dashboard.html")


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
                total = len(numbers)
                for i, nr in enumerate(numbers):
                    set_task("running", f"Audio #{nr}...", int((i / total) * 90))
                    run_script(["generate_audio.py", "--story", str(nr)])
            else:
                set_task("running", "Nächstes Audio...", 10)
                run_script(["generate_audio.py"])
            set_task("running", "Dashboard aktualisieren...", 95)
            refresh_dashboard()
            set_task("complete", "Fertig!", 100)
        except Exception as e:
            set_task("error", str(e), 0)

    set_task("running", "Starte...", 5)
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
        try:
            if story_val:
                numbers = parse_range(story_val)
                total = len(numbers)
                for i, nr in enumerate(numbers):
                    set_task("running", f"Video #{nr}...", int((i / total) * 90))
                    run_script(["generate_videos.py", "--story", str(nr)])
            else:
                set_task("running", "Alle ausstehenden Videos...", 20)
                run_script(["generate_videos.py", "--all"])
            set_task("running", "Dashboard aktualisieren...", 95)
            refresh_dashboard()
            set_task("complete", "Fertig!", 100)
        except Exception as e:
            set_task("error", str(e), 0)

    set_task("running", "Starte...", 5)
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


@app.route("/api/generate-gpt-prompt", methods=["POST"])
def generate_gpt_prompt():
    if _task["status"] == "running":
        return jsonify({"error": "Task läuft bereits"}), 409

    def task():
        try:
            set_task("running", "GPT-Prompts generieren...", 30)
            run_script(["generate_gpt_prompt.py"])
            set_task("complete", "gpt_prompts.txt aktualisiert!", 100)
        except Exception as e:
            set_task("error", str(e), 0)

    set_task("running", "Starte...", 5)
    threading.Thread(target=task, daemon=True).start()
    return jsonify({"status": "started"})


# ── Refresh (Datei-Scan + Dashboard) ────────────────────────────────────────

@app.route("/api/refresh", methods=["POST"])
def refresh():
    run_script(["sync_status.py"])
    refresh_dashboard()
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


if __name__ == "__main__":
    print("[+] Dashboard: http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
