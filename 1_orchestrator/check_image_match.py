#!/usr/bin/env python3
"""
Prüft via Claude Vision ob das Bild zum Stereotyp passt.
Exit 0 = passt, Exit 2 = passt nicht, Exit 1 = Fehler (kein Bild etc.)
"""
import sys
import subprocess
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import input_reader as ir

OUTPUT_DIR = Path(__file__).parent / "output"
USED_DIR = OUTPUT_DIR / "0_used"
INPUT_FILE = "1_input/1_input_file.txt"


def find_image(ns: str) -> Path | None:
    for ext in ("png", "jpg", "jpeg"):
        for d in (OUTPUT_DIR, USED_DIR):
            matches = list(d.glob(f"{ns}_pic*.{ext}"))
            if matches:
                return matches[0]
    return None


def check_match(image_path: Path, stereotyp: str) -> tuple[bool, str]:
    prompt = (
        f"Schau dir dieses Bild an: {image_path}\n\n"
        f"Es soll ein Instagram-Reel-Cover für den deutschen Stereotypen-Humor-Content "
        f"zum Thema \"{stereotyp}\" sein.\n\n"
        f"Passt das Bild thematisch zu diesem Stereotyp? "
        f"Antworte NUR mit 'JA' oder 'NEIN', dann ein Doppelpunkt, dann max. 1 Satz Begründung."
    )
    try:
        result = subprocess.run(
            ["claude", "-p", prompt, "--allowedTools", "Read",
             "--dangerously-skip-permissions"],
            capture_output=True, text=True, timeout=90,
            encoding="utf-8", errors="replace"
        )
        output = result.stdout.strip()
        if not output:
            output = result.stderr.strip() or "Keine Antwort"
        ok = output.upper().startswith("JA")
        return ok, output
    except Exception as e:
        return False, f"Claude-Aufruf fehlgeschlagen: {e}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--story", required=True, help="Story-Nummer")
    args = parser.parse_args()

    row = ir.find_row(args.story, INPUT_FILE)
    if not row:
        print(f"FEHLER: Story #{args.story} nicht gefunden", file=sys.stderr)
        sys.exit(1)

    ns = f"{int(args.story):04d}"
    stereotyp = row["stereotyp"].strip()
    image_path = find_image(ns)

    if not image_path:
        print(f"KEIN_BILD: Kein Bild für #{args.story} gefunden", file=sys.stderr)
        sys.exit(1)

    ok, reason = check_match(image_path, stereotyp)
    print(reason)
    sys.exit(0 if ok else 2)


if __name__ == "__main__":
    main()
