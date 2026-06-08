#!/usr/bin/env python3
"""
Generiert Bilder via ChatGPT Web-Interface (Playwright).

- Öffnet Edge EINMAL mit dem echten Nutzerprofil
- Tippt Prompt in die offene ChatGPT-Seite
- Wartet auf Bild, lädt es herunter
- Wartet 5 Minuten, wiederholt mit nächster Story

Verwendung:
  python generate_pictures_playwright.py --story 49
  python generate_pictures_playwright.py --story 49-55
  python generate_pictures_playwright.py --story 49,51,53
  python generate_pictures_playwright.py --story 49 --wait 3   # 3 Minuten Pause
"""

import argparse
import base64
import logging
import sys
import time
from pathlib import Path

import requests

import re
import input_reader as ir
from generate_gpt_prompt_titled import TITLES, find_story_file

EDGE_PROFILE      = Path(r"C:\Users\slawa\AppData\Local\Microsoft\Edge\User Data")
INPUT_FILE        = "1_input/1_input_file.txt"
OUTPUT_DIR        = Path("output")
PROMPTS_FILE      = Path(r"C:\Users\slawa\OneDrive\8_stereotypen\gpt_prompts.txt")
CHATGPT_IMAGE_URL = "https://chatgpt.com/c/6a083e90-3238-83eb-ae9d-255dabbe121c"
DEFAULT_WAIT_SEC  = 30


def setup_logging() -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    return logging.getLogger(__name__)


def parse_stories(val: str) -> list[str]:
    val = val.strip()
    if "," in val:
        return [v.strip() for v in val.split(",") if v.strip()]
    if "-" in val:
        parts = val.split("-")
        return [str(i) for i in range(int(parts[0]), int(parts[1]) + 1)]
    return [val]


def nr_str(nr: str) -> str:
    return f"{int(nr):04d}"


def build_prompt(nr: str, stereotyp: str) -> str | None:
    nr_int = int(nr)
    title = TITLES.get(nr_int, stereotyp)
    story_file = find_story_file(nr)
    if not story_file:
        return None
    text = re.sub(r"\s+", " ", story_file.read_text(encoding="utf-8").strip())
    return (
        f'{nr_int}. erstelle ein bild (1024x1536) dazu, nicht düster und nicht böse '
        f'und nehme nicht so viel text in das bild rein, '
        f'Titel "{title}". Story: "{text}"'
    )


def load_prompt(nr: str, stereotyp: str = "") -> str | None:
    # Primär: direkt aus TITLES + Story-Text bauen (immer aktuell)
    prompt = build_prompt(nr, stereotyp)
    if prompt:
        return prompt
    # Fallback: gpt_prompts.txt
    if not PROMPTS_FILE.exists():
        return None
    nr_int = int(nr)
    for line in PROMPTS_FILE.read_text(encoding="utf-8").split("\n"):
        line = line.strip()
        if line.startswith(f"{nr_int}. ") or line.startswith(f"{nr_int:04d}. "):
            return line
    return None


def dismiss_popups(page):
    """Entfernt Google One Tap und andere störende Overlays."""
    page.evaluate("""() => {
        ['credential_picker_container', 'google-one-tap-anchor'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.remove();
        });
    }""")


def find_input(page):
    """Sucht das ChatGPT-Eingabefeld mit mehreren Selektoren."""
    candidates = [
        "#prompt-textarea",
        "[data-testid='prompt-textarea']",
        "div[contenteditable='true']",
        "[role='textbox']",
        "textarea",
    ]
    for sel in candidates:
        loc = page.locator(sel).first
        try:
            loc.wait_for(state="visible", timeout=5000)
            return loc
        except Exception:
            continue
    return None


def type_prompt(page, editor, prompt: str):
    """Fügt Prompt in das Eingabefeld ein."""
    editor.click()
    page.wait_for_timeout(300)
    # Via JS einfügen (funktioniert für contenteditable und textarea)
    page.evaluate("""(text) => {
        const el = document.activeElement;
        if (!el) return;
        if (el.tagName === 'TEXTAREA' || el.tagName === 'INPUT') {
            const setter = Object.getOwnPropertyDescriptor(
                window.HTMLTextAreaElement.prototype, 'value'
            ).set;
            setter.call(el, text);
            el.dispatchEvent(new Event('input', { bubbles: true }));
        } else {
            // contenteditable
            el.focus();
            document.execCommand('selectAll', false, null);
            document.execCommand('delete', false, null);
            document.execCommand('insertText', false, text);
        }
    }""", prompt)
    page.wait_for_timeout(400)


def send_prompt(page):
    """Sendet den Prompt (Send-Button oder Enter)."""
    try:
        btn = page.locator('[data-testid="send-button"]')
        btn.wait_for(state="visible", timeout=5000)
        btn.wait_for(state="enabled", timeout=5000)
        btn.click()
    except Exception:
        page.keyboard.press("Enter")


def get_image_snapshot(page) -> set:
    """Alle aktuell sichtbaren Bild-URLs als Set (vor dem Prompt)."""
    srcs = page.evaluate("""() =>
        Array.from(document.querySelectorAll('img[src]'))
            .map(img => img.src)
            .filter(src => src.length > 40 && !src.endsWith('.svg'))
    """)
    return set(srcs or [])


def find_image_for_existing_prompt(page, prompt_key: str) -> str | None:
    """Prüft ob dieser Prompt bereits beantwortet wurde (Bild im Chat vorhanden)."""
    return page.evaluate("""(key) => {
        const skip = ['avatar', 'logo', 'favicon', 'icon', 'spinner', 'profile', 'badge', 'button'];
        const messages = Array.from(document.querySelectorAll('[data-message-author-role]'));
        for (let i = 0; i < messages.length - 1; i++) {
            if (messages[i].getAttribute('data-message-author-role') !== 'user') continue;
            if (!messages[i].textContent.includes(key)) continue;
            const reply = messages[i + 1];
            if (!reply || reply.getAttribute('data-message-author-role') !== 'assistant') continue;
            const imgs = Array.from(reply.querySelectorAll('img[src]')).reverse();
            for (const img of imgs) {
                const src = img.src || '';
                if (!src || src.endsWith('.svg')) continue;
                if (skip.some(s => src.toLowerCase().includes(s))) continue;
                const w = img.naturalWidth || img.width || 0;
                const h = img.naturalHeight || img.height || 0;
                if (w > 100 || h > 100) return src;
                if (src.startsWith('blob:') || src.includes('oaiusercontent') ||
                    src.includes('oaidalleapiprodscus') || src.includes('openai')) return src;
            }
        }
        return null;
    }""", prompt_key)


def find_new_image(page, snapshot: set) -> str | None:
    """Findet ein Bild das NACH dem Snapshot neu auf der Seite erschienen ist."""
    return page.evaluate("""(known) => {
        const knownSet = new Set(known);
        const skip = ['avatar', 'logo', 'favicon', 'icon', 'spinner', 'profile', 'badge', 'button'];
        const imgs = Array.from(document.querySelectorAll('img[src]')).reverse();
        for (const img of imgs) {
            const src = img.src || '';
            if (!src || src.endsWith('.svg')) continue;
            if (skip.some(s => src.toLowerCase().includes(s))) continue;
            if (knownSet.has(src)) continue;
            // Breiter: jedes neue Bild das groß genug ist
            const w = img.naturalWidth || img.width || 0;
            const h = img.naturalHeight || img.height || 0;
            if (w > 200 || h > 200) return src;
            // Fallback: bekannte OpenAI-Domains
            if (src.startsWith('blob:')) return src;
            if (src.includes('oaidalleapiprodscus')) return src;
            if (src.includes('oaiusercontent')) return src;
            if (src.includes('openai')) return src;
        }
        return null;
    }""", list(snapshot))


def wait_for_new_image(page, logger, snapshot: set, timeout_sec: int = 180) -> str | None:
    """Pollt alle 10 Sekunden bis ein NEUES Bild (nicht im Snapshot) erscheint."""
    logger.info("[*] Warte auf neues Bild...")
    page.wait_for_timeout(5000)

    deadline = time.time() + timeout_sec
    elapsed = 5
    while time.time() < deadline:
        src = find_new_image(page, snapshot)
        if src:
            logger.info(f"[*] Neues Bild gefunden nach ~{elapsed}s")
            return src
        logger.info(f"    ... generiert noch ({elapsed}s vergangen, max {timeout_sec}s)")
        page.wait_for_timeout(10000)
        elapsed += 10

    # Debug: alle aktuellen img-Quellen loggen
    all_srcs = page.evaluate("""() =>
        Array.from(document.querySelectorAll('img[src]'))
            .map(img => img.src + ' [' + (img.naturalWidth||0) + 'x' + (img.naturalHeight||0) + ']')
    """)
    logger.info(f"[D] Bilder auf der Seite ({len(all_srcs)}):")
    for s in all_srcs:
        logger.info(f"    {s[:120]}")
    return None


def download_image(page, src: str) -> bytes:
    """Lädt Bild herunter – unterstützt blob: und http: URLs."""
    if src.startswith("blob:") or "chatgpt.com" in src:
        # Blob-URLs und ChatGPT-Backend-URLs benötigen Browser-Auth → via fetch()
        data_url = page.evaluate("""async (src) => {
            const resp = await fetch(src);
            const blob = await resp.blob();
            return new Promise(resolve => {
                const reader = new FileReader();
                reader.onload = () => resolve(reader.result);
                reader.readAsDataURL(blob);
            });
        }""", src)
        _, b64 = data_url.split(",", 1)
        return base64.b64decode(b64)
    else:
        resp = requests.get(src, timeout=60, verify=False)
        resp.raise_for_status()
        return resp.content


def process_story(page, nr: str, logger) -> bool:
    row = ir.find_row(nr, INPUT_FILE)
    if not row:
        logger.error(f"[-] Story #{nr} nicht in CSV")
        return False

    if row.get("status_pic") == "X":
        logger.info(f"[O] #{nr} hat bereits ein Bild – überspringe")
        return True

    prompt = load_prompt(nr, stereo)
    if not prompt:
        logger.error(f"[-] Kein Prompt für #{nr} (Story-Datei fehlt)")
        return False

    stereo = row.get("stereotyp", "")
    out_path = OUTPUT_DIR / f"{nr_str(nr)}_pic.png"

    logger.info(f"")
    logger.info(f"{'='*60}")
    logger.info(f"  Story #{nr}: {stereo}")
    logger.info(f"{'='*60}")
    logger.info(f"[*] Prompt: {prompt[:100]}...")

    # Zur ChatGPT-Seite navigieren
    if CHATGPT_IMAGE_URL not in page.url:
        page.goto(CHATGPT_IMAGE_URL, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)

    dismiss_popups(page)

    # Eingabefeld finden
    editor = find_input(page)
    if not editor:
        logger.error("[-] Eingabefeld nicht gefunden – bitte Edge öffnen und ChatGPT laden")
        return False

    # Warten bis lazy-geladene Bilder sichtbar sind, dann Snapshot
    page.wait_for_timeout(8000)
    snapshot = get_image_snapshot(page)
    logger.info(f"[*] Snapshot: {len(snapshot)} Bilder sichtbar")

    # Prüfen ob Prompt bereits im Chat beantwortet wurde (kein neuer Prompt nötig)
    prompt_key = prompt[prompt.index(". ") + 2:][:60] if ". " in prompt else prompt[:60]
    existing_src = find_image_for_existing_prompt(page, prompt_key)
    if existing_src:
        logger.info(f"[*] Prompt bereits beantwortet – lade vorhandenes Bild direkt")
        src = existing_src
    else:
        type_prompt(page, editor, prompt)
        send_prompt(page)
        src = wait_for_new_image(page, logger, snapshot)

    if not src:
        logger.error("[-] Kein Bild erhalten")
        return False

    # Herunterladen
    logger.info(f"[*] Lade Bild herunter...")
    img_bytes = download_image(page, src)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(img_bytes)
    logger.info(f"[+] Gespeichert: {out_path} ({len(img_bytes):,} Bytes)")

    # CSV aktualisieren
    ir.update_field(nr, "status_pic", "X", INPUT_FILE)
    logger.info(f"[+] status_pic=X gesetzt")
    return True


EDGE_EXE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
CDP_PORT  = 9222


def start_edge_with_debug(logger):
    """Beendet alle Edge-Prozesse, startet Edge mit Debug-Port, gibt Browser zurück."""
    import subprocess, urllib.request, urllib.error

    # Alle Edge-Prozesse beenden
    logger.info("[*] Beende laufende Edge-Prozesse...")
    subprocess.run(["taskkill", "/F", "/IM", "msedge.exe"],
                   capture_output=True)
    time.sleep(3)

    # Edge mit Debug-Port starten
    logger.info(f"[*] Starte Edge mit --remote-debugging-port={CDP_PORT}...")
    subprocess.Popen([
        EDGE_EXE,
        f"--remote-debugging-port={CDP_PORT}",
        "--profile-directory=Default",
        "--no-first-run",
        CHATGPT_IMAGE_URL,
    ])

    # Warten bis Debug-Port verfügbar
    for i in range(20):
        time.sleep(2)
        try:
            urllib.request.urlopen(f"http://localhost:{CDP_PORT}/json/version", timeout=2)
            logger.info(f"[+] Edge-Debug-Port bereit (nach {(i+1)*2}s)")
            break
        except Exception:
            logger.info(f"    ... warte auf Port ({(i+1)*2}s)")
    else:
        return None

    time.sleep(3)  # Kurz warten damit ChatGPT laden kann

    return f"http://localhost:{CDP_PORT}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--story", type=str, required=True,
                        help="Story-Nr: '49', '49-55' oder '49,51,53'")
    parser.add_argument("--wait", type=int, default=DEFAULT_WAIT_SEC,
                        help=f"Wartezeit in Sekunden zwischen Stories (Standard: {DEFAULT_WAIT_SEC})")
    args = parser.parse_args()

    logger = setup_logging()

    from playwright.sync_api import sync_playwright

    nrs = parse_stories(args.story)
    # Stories ohne Bild herausfiltern
    to_process = []
    for nr in nrs:
        row = ir.find_row(nr, INPUT_FILE)
        if row and row.get("status_pic") == "X":
            logger.info(f"[O] #{nr} bereits vorhanden – überspringe")
        else:
            to_process.append(nr)

    if not to_process:
        logger.info("[+] Keine Stories zu verarbeiten.")
        return

    logger.info(f"[*] {len(to_process)} Story/s: {', '.join(to_process)}")
    logger.info(f"[*] Wartezeit zwischen Stories: {args.wait} Sekunden")

    cdp_url = start_edge_with_debug(logger)
    if cdp_url is None:
        logger.error("[-] Edge konnte nicht gestartet werden.")
        sys.exit(1)

    with sync_playwright() as pw:
        browser = pw.chromium.connect_over_cdp(cdp_url)
        logger.info("[*] Verbunden mit Edge-Browser")

        # ChatGPT-Tab finden oder neuen Tab öffnen
        context = browser.contexts[0] if browser.contexts else browser.new_context()
        page = None
        for p in context.pages:
            if "chatgpt.com" in p.url:
                page = p
                logger.info(f"[*] ChatGPT-Tab gefunden: {p.url[:60]}")
                break

        if page is None:
            page = context.new_page()
            page.goto(CHATGPT_IMAGE_URL, wait_until="domcontentloaded")
            page.wait_for_timeout(4000)
            logger.info("[*] Neuen ChatGPT-Tab geöffnet")

        # Zur Bild-Konversation navigieren falls nötig
        if CHATGPT_IMAGE_URL not in page.url:
            page.goto(CHATGPT_IMAGE_URL, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)

        dismiss_popups(page)

        ok = err = 0
        for i, nr in enumerate(to_process):
            if i > 0:
                wait_sec = args.wait
                logger.info(f"")
                logger.info(f"[*] Warte {args.wait} Sekunden vor nächster Story...")
                time.sleep(wait_sec)

            try:
                success = process_story(page, nr, logger)
            except Exception as e:
                logger.error(f"[-] Story #{nr} Fehler: {e}")
                success = False
            if success:
                ok += 1
            else:
                err += 1

        logger.info(f"")
        logger.info(f"[+] Fertig: {ok} OK, {err} Fehler")
        logger.info(f"[*] Fertig – Browser bleibt offen.")


if __name__ == "__main__":
    main()
