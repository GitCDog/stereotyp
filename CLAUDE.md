# 8_stereotypen – CLAUDE.md

## Projektübersicht

Vollautomatisierte Instagram-Reels-Pipeline für deutsche Stereotypen-Humor-Content.
Täglich wird automatisch ein Video auf Instagram gepostet via GitHub Actions.

**Arbeitsverzeichnis:** `1_orchestrator/` (alle Scripts laufen von dort)

---

## Pipeline (5 Schritte)

```
Story (Claude) → Audio (ElevenLabs) → Bild (GPT/manuell) → Video (ffmpeg) → Instagram Post
```

| Schritt | Script | Status-Feld |
|---------|--------|-------------|
| 1. Story generieren | `generate_stories.py` | `status_story` |
| 2. Audio vertonen | `generate_audio.py` | `status_audio` |
| 3. Bild erstellen | `generate_pictures.py` | `status_pic` |
| 4. Video rendern | `generate_videos.py` | `status_video` |
| 5. Instagram posten | `instagram_poster.py` | `insta_post` |

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
nr,stereotyp,status_story,status_audio,seconds,status_pic,status_video,status_caption,insta_post
1,Die Funktionskleidung,X,X,81,X,X,X,X
```

- Status `X` = fertig, leer = ausstehend
- `seconds` = Audio-Dauer in Sekunden
- 173 Stories (Stand: Mai 2026), fortlaufend nummeriert bis 9999 möglich

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
1. Upload zu Cloudinary (`stereotypen/` Ordner)
2. `output/0042_pic.png` → `output/0_used/`
3. `output/0042_mp3.mp3` → `output/0_used/`
4. `output/0042_Name.mp4` → `output/0_used/`
5. `status_video=X` in CSV

---

## Instagram / Cloudinary

- Videos liegen auf Cloudinary (`stereotypen/` Ordner) für GitHub Actions
- `instagram_poster.py` sucht Video erst lokal, dann auf Cloudinary
- Nach erfolgreichem Post: Video von Cloudinary gelöscht, `insta_post=X` gesetzt
- GitHub Actions postet täglich random zwischen 18:30–19:30 CEST
- Bei ≤ 2 Videos auf Cloudinary: automatisch GitHub Issue als Warnung

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

---

## GitHub Actions

Workflow: `.github/workflows/post_story.yml`
- Cron: `30 16 * * *` (18:30 CEST) + random sleep 0–3600s
- Liest/schreibt CSV direkt via GitHub API
- Secrets: `INSTAGRAM_ACCESS_TOKEN`, `INSTAGRAM_RECIPIENT_ID`, `CLOUDINARY_*`, `GITHUB_TOKEN`
- `STORY_NR` input für manuellen Dispatch einer bestimmten Story

---

## Wichtige Konventionen

- `input_reader.py` ist das zentrale CSV-Interface (nie direkt schreiben)
- `ir.update_field(nr, field, value, input_file)` – einzelnes Feld updaten
- `ir.find_row(nr, input_file)` – Zeile nach nr suchen
- `ir.safe_name(text)` – Dateiname-sicherer String
- SSL-Verify ist bewusst deaktiviert (Cloudinary-Kompatibilität auf Windows)
- Alle Scripts laufen mit `cwd = 1_orchestrator/`
