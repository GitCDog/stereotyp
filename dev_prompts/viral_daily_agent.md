# Prompt: Täglicher Viral-Themen-Agent (voll headless, ohne PC/Playwright)

Kontext: Der bestehende `.github/workflows/post_story.yml` postet nur bereits
fertig gerenderte Videos von Cloudinary — Story/Audio/Bild/Video werden aktuell
NICHT in GitHub Actions erzeugt, sondern lokal auf dem Windows-PC (u.a. weil
`generate_stories.py`/`generate_captions.py` den `claude -p`-CLI-Aufruf über eine
eingeloggte Pro-Account-Session nutzen, und `generate_pictures_playwright.py`
einen echten Browser mit ChatGPT-Login braucht). Für einen Agenten, der täglich
komplett autonom postet — auch wenn der PC aus ist — muss die gesamte Kette in
GitHub Actions laufen und darf nur API-basierte Schritte verwenden.

## Prompt (zum Copy-Paste in eine neue Claude-Code-Session)

Baue einen neuen, eigenständigen GitHub-Actions-Workflow
`.github/workflows/viral_daily_post.yml`, der täglich (Cron, z.B. 07:00 UTC —
vor dem bestehenden Post-Workflow um 15:05 UTC) volltautomatisch:
1. ein aktuelles virales Thema in Deutschland recherchiert,
2. daraus eine komplette Story-Instagram-Reel-Pipeline erzeugt,
3. das Ergebnis auf Instagram + YouTube postet,
alles nur mit GitHub-Actions-Runner-Ressourcen (`ubuntu-latest`) — OHNE dass der
private Windows-PC des Nutzers laufen muss, und OHNE Playwright/Browser-Login.

### Schritt 1: Themen-Recherche
- Neues Script `find_viral_topic.py` in 1_orchestrator/.
- Nutzt Claude über die Anthropic-API (nicht die `claude`-CLI mit Pro-Login,
  sondern die Python-SDK/HTTP-API mit `ANTHROPIC_API_KEY` als GitHub Secret) mit
  aktiviertem Web-Search-Tool, um aktuelle deutsche Trends zu recherchieren
  (X/Twitter-Trends, Google Trends DE, News-Schlagzeilen).
- Hartes Ausschlussfilter im Prompt: keine Tragödien, keine laufenden
  Straftaten/Gewalt, keine Minderjährigen, keine Angriffe auf einzelne
  Privatpersonen, keine Themen die stark parteipolitisch/wahlkampfbezogen sind
  (Klage-/Reputationsrisiko für den Account).
- Bevorzugt Themen, die sich als Verhalten/Ritual/Alltagsphänomen erzählen
  lassen (passend zum bestehenden STORY_PROMPT_TEMPLATE in
  generate_stories.py), nicht als reine Nachrichtenmeldung.
- Dedupliziert gegen alle bestehenden `stereotyp`-Werte in
  1_input/1_input_file.txt (per input_reader.py einlesen).
- Gibt einen `stereotyp`-String (+ optional Stichworte) zurück und legt analog
  zu server.py:create_story() eine neue Zeile mit nächster freier `nr` an.
- Bei keinem geeigneten Thema (z.B. alle Kandidaten gefiltert): Script beendet
  sich mit klarer Meldung, Workflow bricht kontrolliert ab (kein Post an dem Tag).

### Schritt 2: Story/Titel/Caption ohne Pro-CLI-Abhängigkeit
- Prüfe, ob `claude -p` auch mit `ANTHROPIC_API_KEY` (statt interaktivem
  Pro-Login) headless funktioniert, und wenn ja, nutze weiterhin
  generate_stories.py / generate_captions.py / generate_title()-Logik
  unverändert mit diesem Env-Var in der CI. Falls das nicht zuverlässig
  headless geht: die drei Claude-Aufrufe (Story, Titel, Caption) auf die
  Anthropic-Python-API mit ANTHROPIC_API_KEY umstellen, bei identischen
  Prompts/Formatvorgaben (130-140 Wörter, Aufgepasst-Opener, Tja-Schlusssatz
  etc. — siehe CLAUDE.md-Story-Format-Abschnitt).
- WICHTIG: klären, ob API-Nutzung andere Kosten/Kontingente verursacht als die
  Pro-CLI-Nutzung (siehe CLAUDE.md-Hinweis "andere Credits" bei
  claude-sonnet-4-6) — das ist eine bewusste Kostenentscheidung, keine rein
  technische.

### Schritt 3: Bild — OHNE Playwright
- Nutze ausschließlich `generate_pictures.py` (OpenAI `gpt-image-1` über
  REST-API mit `OPENAI_API_KEY`) — läuft vollständig headless in Actions.
  `generate_pictures_playwright.py` NICHT verwenden (braucht Browser-Session).
- `OPENAI_API_KEY` als neues GitHub Secret ergänzen.
- Optional: check_image_match.py (Claude prüft Bild-Passung zum Stereotyp)
  wie in server.py:sofort_posten() Schritt 6.5 mit einbauen, inkl. Abbruch bei
  Nicht-Passung.

### Schritt 4: Audio
- generate_audio.py (ElevenLabs REST-API) — bereits headless-fähig, nur
  `ELEVENLABS_API_KEY` als GitHub Secret sicherstellen.

### Schritt 5: Video
- generate_videos.py --subtitles (ffmpeg + Whisper) im Runner ausführen.
  ffmpeg und Whisper-Model-Download müssen als zusätzliche Workflow-Steps
  installiert werden (pip install openai-whisper, apt-get install ffmpeg).
  Laufzeit/Timeout im Workflow ausreichend hoch setzen (Whisper "small"
  Transkription + Rendering kann mehrere Minuten dauern) — orientiere dich am
  bestehenden `timeout-minutes: 200` in post_story.yml.
- Cloudinary-Upload passiert bereits automatisch innerhalb von
  generate_videos.py.

### Schritt 6: Posten
- instagram_poster.py mit FORCE_POST=1 und STORY_NR=<neue nr>, wie in
  server.py:sofort_posten() Schritt 8 — ruft intern youtube_poster.py mit auf.
- Nach Erfolg: CSV/Reihenfolge/dashboard.html committen & pushen, exakt wie im
  bestehenden post_story.yml-Schritt "Änderungen committen".

### Fehlerbehandlung
- Bei Fehlschlag in irgendeinem Schritt: Workflow bricht ab, aber alle bis
  dahin erfolgreich gesetzten status_*-Felder bleiben erhalten (kein Rollback),
  damit man den Rest bei Bedarf manuell übers Dashboard nachholen kann.
- Bei Fehlschlag: automatisch ein GitHub Issue erstellen (analog zum
  bestehenden "Nur noch X Video(s) auf Cloudinary"-Issue in post_story.yml),
  damit der Nutzer benachrichtigt wird, ohne dass der PC laufen muss.

### Neue GitHub Secrets, die ergänzt werden müssen
- ANTHROPIC_API_KEY (falls Schritt 2 auf API statt Pro-CLI umgestellt wird)
- OPENAI_API_KEY (für generate_pictures.py + Web-Search-Themenrecherche, falls
  GPT-4o für die Szenenbeschreibung weiter genutzt wird)
- ELEVENLABS_API_KEY (Audio)
- Bestehende Secrets (INSTAGRAM_*, CLOUDINARY_*, YOUTUBE_*) bleiben unverändert.

### Offene Entscheidung, die vor der Umsetzung geklärt werden sollte
Soll dieser Agent das bestehende `1_input_file.txt` direkt mit neuen,
KI-gewählten Themen befüllen (voll autonom, kein manuelles Review), oder soll
er das gewählte Thema + generierte Story erst als Draft/Issue/PR anlegen, das
der Nutzer kurz bestätigt, bevor automatisch auf Instagram gepostet wird?
Beides sollte im Implementierungs-Prompt als Alternative benannt werden, die
Entscheidung liegt beim Nutzer.
