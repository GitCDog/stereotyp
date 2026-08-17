# Prompt: "E2E-posten"-Button im Dashboard

Kontext: Es gibt bereits eine vollständige End-to-End-Pipeline in
`1_orchestrator/server.py` (`sofort_posten()`, Route `POST /api/sofort-posten`,
~Zeile 1013–1254), die aber ihren Input aus `story_jetzt.xlsx` liest statt aus
den bestehenden Dashboard-Formularfeldern `#newStereotyp` / `#newStichworte`
(`1_orchestrator/dashboard.html`, "✍️ Neue Story erstellen"-Karte, ~Zeile
459–486). Ziel: ein neuer Button, der dieselbe Pipeline direkt mit den
Formularwerten anstößt.

## Prompt (zum Copy-Paste in eine neue Claude-Code-Session)

Füge im 8_stereotypen-Dashboard einen neuen Button "🚀 E2E-posten" direkt neben dem
bestehenden "Generieren"-Button (id="createStoryBtn", dashboard.html ~Zeile 484,
in der "✍️ Neue Story erstellen"-Karte) hinzu. Er nutzt dieselben bereits
vorhandenen Formularfelder #newStereotyp und #newStichworte, startet aber statt
create_story() die komplette Sofort-Posten-Pipeline.

### Ausgangslage
- server.py hat bereits eine vollständige E2E-Pipeline in sofort_posten()
  (Route POST /api/sofort-posten, Zeile 1013–1254): CSV-Eintrag anlegen → Story
  generieren → Titel → Caption → Bild (generate_pictures_playwright.py) → Audio
  → Bild-Passungs-Check (check_image_match.py) → Video (generate_videos.py
  --subtitles --bg-music) → Git-Sync → Instagram+YouTube-Post
  (instagram_poster.py mit FORCE_POST=1).
- Der einzige Unterschied zum gewünschten Feature: sofort_posten() liest
  stereotyp/stichworte/titel aus der nächsten offenen Zeile in
  story_jetzt.xlsx, statt sie als Parameter zu bekommen.

### Aufgabe
1. Refactoring: Extrahiere den Pipeline-Körper aus sofort_posten() (alles ab
   "1. In CSV eintragen" bis zum Instagram/YouTube-Post inkl. Logging/
   set_task-Aufrufen) in eine gemeinsame Funktion, z.B.
   run_full_pipeline(stereotyp: str, stichworte: str, titel: str | None = None,
   on_complete: Callable | None = None). on_complete wird nur für den
   xlsx-Sonderfall gebraucht (Status=X zurückschreiben in story_jetzt.xlsx).
2. sofort_posten() ruft danach nur noch: pending Zeile aus xlsx lesen →
   run_full_pipeline(..., on_complete=lambda: xlsx-Status setzen).
3. Neue Route POST /api/e2e-posten: liest {stereotyp, stichworte} aus dem
   JSON-Body (kommt von #newStereotyp/#newStichworte), prüft _task["status"]
   != "running" (409 wie bei den anderen Routen), startet
   run_full_pipeline(stereotyp, stichworte) in einem Background-Thread wie die
   bestehenden Routen (threading.Thread(..., daemon=True)).
4. dashboard.html: Button <button class="new-story-submit" id="e2eBtn"
   onclick="startE2EPosten()">🚀 E2E-posten</button> neben createStoryBtn
   einfügen. JS-Funktion startE2EPosten() liest #newStereotyp/#newStichworte
   (gleiche Validierung wie createStory() – Stereotyp darf nicht leer sein),
   zeigt vor dem POST einen confirm()-Dialog ("Wirklich sofort auf Instagram +
   YouTube posten?") — anders als der reguläre "Generieren"-Button postet
   dieser Weg tatsächlich live, das braucht eine bewusste Bestätigung —
   und postet danach an /api/e2e-posten. Fortschritt/Log-Anzeige über
   dasselbe bestehende Polling/UI wiederverwenden, das schon für
   createStory()/startAction() läuft (logTitle/logBox/logFill/logList,
   Polling von /api/progress).
5. Der neue Button bleibt disabled/inaktiv solange _task.status === "running"
   ist (gleiches Verhalten wie die anderen Action-Buttons).

### Nicht ändern
- sofort_posten()/story_jetzt.xlsx-Workflow bleibt unverändert nutzbar
  (nur intern auf die neue Hilfsfunktion umgestellt).
- Reihenfolge-Logik (0_reihenfolge.txt) aus create_story() wird hier NICHT
  gebraucht, da E2E sofort postet statt einzureihen.
