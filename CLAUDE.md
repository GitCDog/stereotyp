# 8_stereotypen – CLAUDE.md

## Projektübersicht

Vollautomatisierte Instagram-Reels-Pipeline für deutsche Stereotypen-Humor-Content.
Täglich wird automatisch ein Video auf Instagram gepostet via GitHub Actions.

**Arbeitsverzeichnis:** `1_orchestrator/` (alle Scripts laufen von dort)

---

## Pipeline (5 Schritte)

```
Story (Claude) → Audio (ElevenLabs) → Bild (GPT/manuell) → Video (ffmpeg) → YouTube Short → Instagram Post
```

| Schritt | Script | Status-Feld |
|---------|--------|-------------|
| 1. Story generieren | `generate_stories.py` | `status_story` |
| 2. Audio vertonen | `generate_audio.py` | `status_audio` |
| 3. Bild erstellen | `generate_pictures.py` | `status_pic` |
| 4. Video rendern | `generate_videos.py` | `status_video` |
| 5a. YouTube Short | `youtube_poster.py` (via instagram_poster) | `youtube_post` |
| 5b. Instagram posten | `instagram_poster.py` | `insta_post` |

---

## Dateistruktur

```
1_orchestrator/
  1_input/
    1_input_file.txt          ← Haupt-CSV (nr, stereotyp, status_*)
    0001_Die Funktionskleidung.txt  ← Story-Texte (4-stellig zero-padded)
    00_sammelsurium.txt       ← Staging-Datei für neue Stories (Format: NR: Name\nText)
    gpt_prompts.txt           ← Generierte Bild-Prompts für GPT
  output/
    0001_pic.png              ← Bilder
    0001_mp3.mp3              ← Audio-Dateien
    0001_Die Funktionskleidung.mp4  ← Fertige Videos
    captions.json             ← Instagram-Captions
    posted_videos.json        ← Log aller Posts
    0_used/                   ← Archiv (nach Videogenerierung verschoben)
  2_pic/                      ← Beispielbilder / Profilbild
  .env                        ← API Keys (nicht committed)
  config.yaml                 ← Konfiguration
  server.py                   ← Lokales Dashboard-Backend (http://localhost:5000)
  dashboard.html              ← Generiertes Dashboard
```

---

## Nummerierung

**Immer 4-stellig zero-padded:** `f"{int(nr):04d}"` → `0001`, `0042`, `0173`

- Alle Dateinamen: `0042_Stereotyp-Name.txt`, `0042_mp3.mp3`, `0042_pic.png`
- CSV-Spalte `nr`: plain integer als String (`"42"`, nicht `"0042"`)
- `_nr_str(nr)` in allen Scripts gibt immer 4-stelliges Format zurück

---

## CSV-Format

Datei: `1_input/1_input_file.txt`

```
nr,stereotyp,status_story,status_audio,seconds,status_pic,status_video,status_caption,insta_post,youtube_post
1,Die Funktionskleidung,X,X,81,X,X,X,X,X
```

- Status `X` = fertig, leer = ausstehend
- `seconds` = Audio-Dauer in Sekunden
- `youtube_post` = `X` nach erfolgreichem YouTube-Upload
- `nr` in CSV immer als plain integer (`"42"`, nie `"0042"`) — `_write_rows()` normalisiert automatisch
- 298+ Stories (Stand: Mai 2026), fortlaufend nummeriert bis 9999 möglich

---

## Story-Format

Jede Story-TXT-Datei **muss einen Absatz (`\n\n`) bei ~50% des Textes** haben.
Ohne Absatz wird die Vertonung in `generate_audio.py` blockiert (ElevenLabs-Pause).

Struktur (130–140 Wörter):
1. `Aufgepasst - ` (Opener)
2. Der Aufreißer (konkrete Alltagssituation)
3. Der Mythos (heilige Zeremonie / Naturgesetz)
4. Die „deutsche Logik" (2–3 Bullet-Points mit `•`)
5. Der soziale Endgegner
6. Der virale Twist (Pro-Tipp / trockener Vergleich)

Abschluss: `Tja,` statt `Ah ja,`

---

## Neue Stories hinzufügen

**Option A – Sammelsurium** (empfohlen für manuelle Stories):
Datei `1_input/00_sammelsurium.txt` mit Format:
```
174: Neuer Stereotyp
Story-Text hier...

175: Weiterer Stereotyp
...
```
→ Nach `sync_status.py` (oder Dashboard-Refresh) werden Stories automatisch extrahiert, Absatz automatisch eingefügt, CSV aktualisiert.

**Option B – Per Script:**
```bash
python generate_stories.py --story 42   # Story #42 generieren
python generate_stories.py --all        # Alle ausstehenden
```

---

## Bilder-Workflow (OneDrive)

Neue Bilder in `C:\Users\slawa\OneDrive\8_stereotypen\` ablegen:
- **Korrekt benannte Bilder** (`0042_pic.png`): werden beim Dashboard-Refresh automatisch nach `output/` kopiert, gelöscht und `status_pic=X` gesetzt
- **Unbekannte Dateinamen**: beim nächsten Session-Start erkennt Claude die Bilder via Vision und verarbeitet sie

GPT-Bild-Prompts generieren: Dashboard → `📝 GPT Prompts` (speichert in `1_input/gpt_prompts.txt`)

---

## Video-Pipeline (nach ffmpeg-Render)

`generate_videos.py` macht nach erfolgreicher Videogenerierung automatisch:
1. Whisper-Transkription → burned-in Karaoke-Untertitel
2. Upload zu Cloudinary (`stereotypen/` Ordner, `overwrite=True`)
3. `output/0042_pic.png` → `output/0_used/`
4. `output/0042_mp3.mp3` → `output/0_used/`
5. `output/0042_Name.mp4` → `output/0_used/`
6. `status_video=X` in CSV

**Untertitel-Spezifikation:**
- Modell: Whisper `small`, Sprache: `de`, `word_timestamps=True`
- Schrift: Trebuchet MS, 46px, Bold
- Farbe: Weiß (gesprochen) / Gelb (noch nicht gesprochen) — Karaoke `\k`-Tags
- Block-Größe: 5 Wörter, 1 Zeile sichtbar, Position: unten zentriert (MarginV=280)
- Format: ASS mit `PlayResX: 1080 / PlayResY: 1920`

**CLI-Flags:**
```bash
python generate_videos.py --story 42 --subtitles          # Mit Untertiteln (Standard via Dashboard)
python generate_videos.py --story 42 --subtitle-words 5   # Wörter pro Block (default: 5)
python generate_videos.py --all --subtitles               # Alle ausstehenden mit Untertiteln
```

---

## Instagram / Cloudinary

- Videos liegen auf Cloudinary (`stereotypen/` Ordner) für GitHub Actions
- `instagram_poster.py` sucht Video erst lokal, dann auf Cloudinary
- Nach erfolgreichem Post: Video von Cloudinary gelöscht, `insta_post=X` gesetzt
- GitHub Actions postet täglich random zwischen ~18:05–19:05 CEST
- Bei ≤ 2 Videos auf Cloudinary: automatisch GitHub Issue als Warnung

---

## YouTube Shorts

- `youtube_poster.py` – lädt Video als YouTube Short hoch (wird von `instagram_poster.py` aufgerufen)
- `youtube_auth.py` – einmalige lokale Authentifizierung, gibt Refresh-Token aus
- Scope: `https://www.googleapis.com/auth/youtube.force-ssl` (erlaubt upload + update)

**Titel-Format** (max. 100 Zeichen):
```
Aufgepasst - {Stereotyp} | {hashtags aus caption} @aufgepasst.stereotyp
```

**Beschreibungs-Format:**
```
{volle caption (Titel + Hashtags)}

#Shorts

insta: @aufgepasst.stereotyp
```

**Auth-Setup (einmalig lokal):**
```bash
python youtube_auth.py   # Browser öffnet sich → Konto auswählen → Erlauben
```
→ Refresh-Token in `.env` eintragen: `YOUTUBE_REFRESH_TOKEN=...`
→ Auch als GitHub Secret setzen: `gh secret set YOUTUBE_REFRESH_TOKEN --body "..."`

**GitHub Secrets für YouTube:**
- `YOUTUBE_CLIENT_ID`
- `YOUTUBE_CLIENT_SECRET`
- `YOUTUBE_REFRESH_TOKEN`

**Manueller Upload:**
```bash
python youtube_poster.py --story 42
```

---

## Lokales Dashboard

```bash
cd 1_orchestrator
python server.py   # → http://localhost:5000
```

Buttons:
- **Audio für alle Pics** – generiert Audios für alle Stories mit Bild aber ohne Audio
- **Refresh** – scannt Dateien, prüft OneDrive, aktualisiert CSV + Dashboard
- Andere Buttons (Story, Caption, Bild) sind bewusst grau (manueller Workflow)
- **Generieren** – startet Video-Render **mit Untertiteln** (`--subtitles`), keine Audio-Generierung

Features:
- 👁 Augen-Icon neben jedem Story-Namen → Hover zeigt Story-Text als Tooltip
- `youtube_post`-Spalte in der Tabelle (YT-Icon)

---

## GitHub Actions

Workflow: `.github/workflows/post_story.yml`
- Cron: `5 15 * * *` (17:05 UTC = 19:05 CEST) + random sleep 0–3600s → Post ~19:05–20:05 CEST
- Liest/schreibt CSV direkt via GitHub API
- Secrets: `INSTAGRAM_ACCESS_TOKEN`, `INSTAGRAM_RECIPIENT_ID`, `CLOUDINARY_*`, `GITHUB_TOKEN`, `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN`
- `STORY_NR` input für manuellen Dispatch einer bestimmten Story

---

## Wichtige Konventionen

- `input_reader.py` ist das zentrale CSV-Interface (nie direkt schreiben)
- `ir.update_field(nr, field, value, input_file)` – einzelnes Feld updaten
- `ir.find_row(nr, input_file)` – Zeile nach nr suchen
- `ir.safe_name(text)` – Dateiname-sicherer String
- SSL-Verify ist bewusst deaktiviert (Cloudinary-Kompatibilität auf Windows)
- Alle Scripts laufen mit `cwd = 1_orchestrator/`
