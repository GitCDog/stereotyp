#!/usr/bin/env python3
"""
Haupt-Orchestrator für die Stereotypen-Instagram-Automation.

Steuert die komplette Pipeline:
  Story → Bild → Audio → Video → Instagram-Post

Verwendung:
  python main.py                          # Nächste ausstehende Story komplett
  python main.py --story 5               # Story Nr. 5 gezielt
  python main.py --story 5 --auto-title  # Titel von Claude generieren lassen
  python main.py --step story            # Nur Story-Schritt
  python main.py --step audio            # Nur Audio-Schritt
  python main.py --step picture          # Nur Bild-Schritt
  python main.py --step video            # Nur Video-Schritt
  python main.py --step post             # Nur Instagram-Post
  python main.py --all                   # Alle ausstehenden Stories
  python main.py --dry-run               # Ohne Instagram-Upload
"""

import os
import sys
import argparse
import logging
import subprocess
from pathlib import Path

import yaml
from dotenv import load_dotenv

import input_reader as ir

load_dotenv()


def load_config(config_path: str = "config.yaml") -> dict:
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def setup_logging(log_file: str = "./logs/workflow.log") -> logging.Logger:
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    return logging.getLogger(__name__)


def run_script(script: str, extra_args: list[str] = None, logger: logging.Logger = None) -> bool:
    """Führe ein Sub-Skript aus und gib Erfolg zurück."""
    cmd = [sys.executable, script] + (extra_args or [])
    if logger:
        logger.info(f"[*] Starte: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=Path(__file__).parent)
    if result.returncode != 0:
        if logger:
            logger.error(f"[-] {script} fehlgeschlagen (exit {result.returncode})")
        return False
    return True


def step_story(story_nr: int | None, auto_title: bool, logger: logging.Logger) -> bool:
    args = []
    if story_nr:
        args += ["--story", str(story_nr)]
    if auto_title:
        args.append("--auto-title")
    logger.info("\n[1/5] Story generieren...")
    return run_script("generate_stories.py", args, logger)


def step_picture(story_nr: int | None, logger: logging.Logger) -> bool:
    logger.info("\n[2/5] Bild generieren...")
    if story_nr:
        return run_script("generate_pictures.py", [str(story_nr)], logger)
    # Finde nächste Story ohne Bild
    config = load_config()
    rows = ir.read_rows(config["output"]["input_file"])
    for row in rows:
        if row.get("status_story") == "X" and not row.get("status_pic", "").strip():
            return run_script("generate_pictures.py", [row["nr"].strip()], logger)
    logger.info("[+] Kein Bild ausstehend")
    return True


def step_audio(story_nr: int | None, logger: logging.Logger) -> bool:
    args = []
    if story_nr:
        args += ["--story", str(story_nr)]
    logger.info("\n[3/5] Audio generieren...")
    return run_script("generate_audio.py", args, logger)


def step_video(story_nr: int | None, logger: logging.Logger) -> bool:
    args = []
    if story_nr:
        args += ["--story", str(story_nr)]
    logger.info("\n[4/5] Video erstellen...")
    return run_script("generate_videos.py", args, logger)


def step_post(dry_run: bool, logger: logging.Logger) -> bool:
    if dry_run:
        logger.info("\n[5/5] Instagram-Post ÜBERSPRUNGEN (--dry-run)")
        return True
    logger.info("\n[5/5] Instagram-Post...")
    return run_script("instagram_poster.py", [], logger)


def step_dashboard(logger: logging.Logger):
    run_script("generate_dashboard.py", [], logger)


def run_full_pipeline(story_nr: int | None, auto_title: bool, dry_run: bool, logger: logging.Logger):
    """Führe die komplette Pipeline für eine Story aus."""
    logger.info("=" * 60)
    logger.info("STEREOTYPEN AUTOMATION – START")
    logger.info("=" * 60)

    results = {}
    results["story"] = step_story(story_nr, auto_title, logger)
    if not results["story"]:
        logger.error("[-] Story-Schritt fehlgeschlagen – Abbruch")
        return results

    results["picture"] = step_picture(story_nr, logger)
    results["audio"]   = step_audio(story_nr, logger)

    if results["audio"] and results["picture"]:
        results["video"] = step_video(story_nr, logger)
    else:
        logger.warning("[!] Bild oder Audio fehlt – Video-Schritt übersprungen")
        results["video"] = False

    if results.get("video"):
        results["post"] = step_post(dry_run, logger)

    step_dashboard(logger)

    logger.info("\n" + "=" * 60)
    logger.info("ERGEBNIS:")
    for k, v in results.items():
        icon = "✓" if v else "✗"
        logger.info(f"  {icon} {k}")
    logger.info("=" * 60)
    return results


def main():
    parser = argparse.ArgumentParser(description="Stereotypen Instagram Automation")
    parser.add_argument("--story", type=int, help="Story-Nummer (z.B. 5)")
    parser.add_argument("--step", choices=["story", "picture", "audio", "video", "post", "dashboard", "all"],
                        help="Einzelnen Schritt ausführen")
    parser.add_argument("--all", dest="run_all", action="store_true",
                        help="Alle ausstehenden Stories verarbeiten")
    parser.add_argument("--auto-title", action="store_true",
                        help="Titel von Claude generieren lassen")
    parser.add_argument("--dry-run", action="store_true",
                        help="Ohne Instagram-Upload")
    parser.add_argument("--config", default="config.yaml")
    args = parser.parse_args()

    config = load_config(args.config)
    logger = setup_logging(config["output"]["log_file"])

    if args.step and args.step != "all":
        # Einzelner Schritt
        if args.step == "story":
            step_story(args.story, args.auto_title, logger)
        elif args.step == "picture":
            step_picture(args.story, logger)
        elif args.step == "audio":
            step_audio(args.story, logger)
        elif args.step == "video":
            step_video(args.story, logger)
        elif args.step == "post":
            step_post(args.dry_run, logger)
        elif args.step == "dashboard":
            step_dashboard(logger)

    elif args.run_all:
        # Alle ausstehenden Stories
        rows = ir.read_rows(config["output"]["input_file"])
        pending = [r for r in rows if not r.get("status_story", "").strip()]
        logger.info(f"[*] {len(pending)} ausstehende Stories")
        for row in pending:
            try:
                run_full_pipeline(int(row["nr"]), args.auto_title, args.dry_run, logger)
            except Exception as e:
                logger.error(f"[-] Fehler bei Story #{row['nr']}: {e}")

    else:
        # Standard: nächste ausstehende Story
        run_full_pipeline(args.story, args.auto_title, args.dry_run, logger)


if __name__ == "__main__":
    main()
