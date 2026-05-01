#!/usr/bin/env python3
"""CSV-Helper für die Stereotypen-Input-Datei."""

import csv
import io
from pathlib import Path


INPUT_FILE = "1_input/1_input_file.txt"
COLUMNS = ["nr", "stereotyp", "status_story", "status_audio",
           "seconds", "status_pic", "status_video", "status_caption", "insta_post"]


def read_rows(input_file: str = INPUT_FILE) -> list[dict]:
    """Lese alle Zeilen aus der Input-CSV."""
    path = Path(input_file)
    if not path.exists():
        raise FileNotFoundError(f"Input-Datei nicht gefunden: {input_file}")
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = []
        for row in reader:
            if row.get("nr", "").strip() and row.get("stereotyp", "").strip():
                rows.append(dict(row))
    return rows


def _nr_match(row_nr: str, nr) -> bool:
    """Vergleiche Zeilen-Nr mit gesuchter Nr (int oder string wie '100_01')."""
    row_nr = row_nr.strip()
    nr_str = str(nr).strip()
    if row_nr == nr_str:
        return True
    try:
        return int(row_nr) == int(nr_str)
    except (ValueError, TypeError):
        return False


def find_row(nr, input_file: str = INPUT_FILE) -> dict | None:
    """Finde eine Zeile anhand der Nummer (int oder string wie '100_01')."""
    for row in read_rows(input_file):
        if _nr_match(row.get("nr", ""), nr):
            return row
    return None


def update_field(nr, field: str, value: str, input_file: str = INPUT_FILE) -> bool:
    """Aktualisiere ein Feld in der CSV für eine bestimmte Zeile (by nr)."""
    path = Path(input_file)
    rows = read_rows(input_file)

    updated = False
    for row in rows:
        if _nr_match(row.get("nr", ""), nr):
            row[field] = value
            updated = True
            break

    if not updated:
        return False

    # CSV zurückschreiben
    with open(path, encoding="utf-8", newline="") as f:
        original_content = f.read()

    fieldnames = list(csv.DictReader(io.StringIO(original_content)).fieldnames)

    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})

    return True


def add_row(data: dict, input_file: str = INPUT_FILE) -> bool:
    """Füge eine neue Zeile ans Ende der CSV an. False wenn nr bereits vorhanden."""
    path = Path(input_file)
    nr = data.get("nr", "")

    with open(path, encoding="utf-8", newline="") as f:
        original_content = f.read()

    fieldnames = list(csv.DictReader(io.StringIO(original_content)).fieldnames)
    rows = read_rows(input_file)

    for row in rows:
        if _nr_match(row.get("nr", ""), nr):
            return False

    rows.append(data)

    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})

    return True


def get_next_pending(field: str, input_file: str = INPUT_FILE) -> dict | None:
    """Finde die erste Zeile, bei der das Statusfeld leer ist."""
    for row in read_rows(input_file):
        if not row.get(field, "").strip():
            return row
    return None


def safe_name(stereotyp: str) -> str:
    """Erzeuge sicheren Dateinamen aus Stereotyp-Name."""
    import re
    name = stereotyp.strip()
    name = re.sub(r'[<>:"/\\|?*]', "", name)
    return name
