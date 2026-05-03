#!/usr/bin/env python3
"""
Löscht gezielt Videos von Cloudinary.
Verwendung: python cloudinary_delete.py
Benötigt CLOUDINARY_* Variablen in .env
"""

import os
import cloudinary
import cloudinary.api
from dotenv import load_dotenv

load_dotenv()

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True,
)

TO_DELETE = [
    "stereotypen/100_22_Das Arschgeweih",
    "stereotypen/005_Hausschuhe für Gäste",
]


def list_folder():
    """Zeige alle Videos im stereotypen-Ordner (zur Überprüfung der public_ids)."""
    result = cloudinary.api.resources(
        type="upload", resource_type="video",
        prefix="stereotypen/", max_results=50,
    )
    for r in result.get("resources", []):
        print(f"  {r['public_id']}")


def delete_videos(public_ids: list[str], dry_run: bool = False):
    for pid in public_ids:
        if dry_run:
            print(f"[DRY RUN] Würde löschen: {pid}")
            continue
        try:
            res = cloudinary.api.delete_resources([pid], resource_type="video")
            deleted = res.get("deleted", {})
            status = deleted.get(pid, "unbekannt")
            print(f"[+] {pid} → {status}")
        except Exception as e:
            print(f"[-] Fehler bei {pid}: {e}")


if __name__ == "__main__":
    print("=== Verfügbare Videos auf Cloudinary ===")
    list_folder()

    print("\n=== Lösche Videos ===")
    delete_videos(TO_DELETE, dry_run=False)
