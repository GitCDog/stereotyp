#!/usr/bin/env python3
"""
Einmalige lokale Authentifizierung für YouTube.
Führe dieses Script einmal lokal aus, um den Refresh-Token zu erhalten.

Voraussetzung:
  1. Google Cloud Console → Projekt erstellen
  2. YouTube Data API v3 aktivieren
  3. OAuth2-Client-ID erstellen (Typ: Desktop-App)
  4. client_secret.json herunterladen und in 1_orchestrator/ ablegen

Verwendung:
  python youtube_auth.py

Danach:
  - Refresh-Token in .env eintragen: YOUTUBE_REFRESH_TOKEN=...
  - Client-ID in .env: YOUTUBE_CLIENT_ID=...
  - Client-Secret in .env: YOUTUBE_CLIENT_SECRET=...
  - Alle drei als GitHub Secrets hinterlegen
"""

import json
import os
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]
CLIENT_SECRET_FILE = "client_secret.json"


def main():
    if not Path(CLIENT_SECRET_FILE).exists():
        print(f"[!] {CLIENT_SECRET_FILE} nicht gefunden.")
        print("    Lade die Datei aus der Google Cloud Console herunter:")
        print("    APIs & Services → Credentials → OAuth 2.0 Client IDs → Download JSON")
        return

    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
    creds = flow.run_local_server(port=0)

    with open(CLIENT_SECRET_FILE) as f:
        client_data = json.load(f)

    client_id = client_data["installed"]["client_id"]
    client_secret = client_data["installed"]["client_secret"]

    print("\n[OK] Authentifizierung erfolgreich!\n")
    print("Trage folgendes in deine .env und GitHub Secrets ein:")
    print(f"  YOUTUBE_CLIENT_ID={client_id}")
    print(f"  YOUTUBE_CLIENT_SECRET={client_secret}")
    print(f"  YOUTUBE_REFRESH_TOKEN={creds.refresh_token}")


if __name__ == "__main__":
    main()
