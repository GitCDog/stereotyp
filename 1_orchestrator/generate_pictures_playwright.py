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
import pyperclip

import re
import input_reader as ir
from generate_gpt_prompt_titled import TITLES, find_story_file

EDGE_PROFILE      = Path(r"C:\Users\slawa\AppData\Local\Microsoft\Edge\User Data")
INPUT_FILE        = "1_input/1_input_file.txt"
OUTPUT_DIR        = Path("output")
PROMPTS_FILE      = Path(r"C:\Users\slawa\OneDrive\8_stereotypen\gpt_prompts.txt")
CHATGPT_IMAGE_URL  = "https://chatgpt.com/c/6a5c8a83-11b4-83ed-9211-cb89ff3906f7"  # Stereotypen
CHATGPT_NAMES_URL  = "https://chatgpt.com/c/6a638035-5948-83eb-a0b2-087e174f69d8"  # Namen 2000–2999


def get_chatgpt_url(nr: str) -> str:
    return CHATGPT_NAMES_URL if 2000 <= int(nr) <= 2999 else CHATGPT_IMAGE_URL
DEFAULT_WAIT_SEC  = 30
# Eigenes persistentes Verzeichnis – kein Konflikt mit Default-Profil / WebView2-lockfile
CDP_USER_DATA = Path(r"C:\Users\slawa\AppData\Local\Temp\EdgeCDP")


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
    story_file = find_story_file(nr)
    if not story_file:
        return None
    text = re.sub(r"\s+", " ", story_file.read_text(encoding="utf-8").strip())
    if 2000 <= nr_int <= 2999:
        return (
            f'{nr_int}. erstelle ein portrait-bild (1024x1536) im Stil einer modernen flachen Illustration. '
            f'Zeige eine Person passend zum deutschen Namen "{stereotyp}" und zur folgenden Story. '
            f'Oben links nur den Namen "{stereotyp}" in grosser, dunkler moderner Schrift – kein weiterer Text im Bild, kein Titel. '
            f'Hintergrund: organische abstrakte Formen in gedaempften Farben, passend zur Stimmung der Story. '
            f'Die Person, Mimik, Kleidung, Koerpersprache und Hintergrundfarben sollen die Story widerspiegeln. '
            f'Stil: cleane Vektor-Illustration, warme Pastelltöne. Story: "{text}"'
        )
    title = TITLES.get(nr_int, stereotyp)
    return (
        f'{nr_int}. erstelle ein bild (1024x1536) dazu, nicht düster und nicht böse '
        f'und nehme nicht so viel text in das bild rein, '
        f'verändere die szene und personen im vergleich zum vorherigen bild, '
        f'stelle junge personen dar (20-35 jahre), '
        f'Titel "{title}". Story: "{text}"'
    )


def load_prompt(nr: str, stereotyp: str = "") -> str | None:
    return build_prompt(nr, stereotyp)


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
            logging.getLogger(__name__).info(f"[*] Eingabefeld gefunden: {sel}")
            return loc
        except Exception:
            continue
    return None


def type_prompt(page, editor, prompt: str):
    """Fügt Prompt ins ChatGPT-Eingabefeld ein."""
    logger = logging.getLogger(__name__)

    page.bring_to_front()
    page.wait_for_timeout(500)
    editor.click()
    page.wait_for_timeout(300)

    tag = editor.evaluate("el => el.tagName + ' id=' + el.id + ' ce=' + el.contentEditable")
    logger.info(f"[*] Eingabefeld: {tag}")

    # Ansatz 1: execCommand (läuft in JS-Kontext, kein OS-Fensterfokus nötig)
    result = page.evaluate("""(text) => {
        const el = document.querySelector('#prompt-textarea') ||
                   document.querySelector('[contenteditable="true"]');
        if (!el) return 'no element';
        el.focus();
        document.execCommand('selectAll', false, null);
        document.execCommand('delete', false, null);
        const ok = document.execCommand('insertText', false, text);
        const len = (el.innerText || el.value || '').length;
        return 'ok=' + ok + ' len=' + len;
    }""", prompt)
    logger.info(f"[*] execCommand: {result}")

    content = editor.evaluate("el => el.value || el.innerText || ''")
    logger.info(f"[*] Feld nach execCommand: {len(content)} Zeichen")
    if len(content) >= 10:
        return

    # Ansatz 2: DataTransfer Paste-Event
    logger.info("[*] execCommand fehlgeschlagen – versuche DataTransfer paste")
    result2 = page.evaluate("""(text) => {
        const el = document.querySelector('#prompt-textarea') ||
                   document.querySelector('[contenteditable="true"]');
        if (!el) return 'no element';
        el.focus();
        const range = document.createRange();
        range.selectNodeContents(el);
        const sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
        document.execCommand('delete', false, null);
        const dt = new DataTransfer();
        dt.setData('text/plain', text);
        el.dispatchEvent(new ClipboardEvent('paste', {clipboardData: dt, bubbles: true, cancelable: true}));
        return 'paste len=' + (el.innerText || el.value || '').length;
    }""", prompt)
    logger.info(f"[*] DataTransfer: {result2}")

    content2 = editor.evaluate("el => el.value || el.innerText || ''")
    logger.info(f"[*] Feld nach DataTransfer: {len(content2)} Zeichen")
    if len(content2) >= 10:
        return

    # Ansatz 3: Systemclipboard + Ctrl+V
    logger.info("[*] DataTransfer fehlgeschlagen – versuche Systemclipboard Ctrl+V")
    pyperclip.copy(prompt)
    editor.click()
    page.wait_for_timeout(400)
    editor.press("Control+a")
    page.wait_for_timeout(100)
    editor.press("Control+v")
    page.wait_for_timeout(600)
    content3 = editor.evaluate("el => el.value || el.innerText || ''")
    logger.info(f"[*] Feld nach Clipboard: {len(content3)} Zeichen")


def send_prompt(page):
    """Sendet den Prompt. Wartet bis Send-Button enabled ist, dann JS-Click oder Enter."""
    logger = logging.getLogger(__name__)
    btn = page.locator('[data-testid="send-button"]')
    try:
        btn.wait_for(state="visible", timeout=5000)
        for _ in range(30):
            if btn.is_enabled():
                break
            page.wait_for_timeout(300)
        if btn.is_enabled():
            logger.info("[*] Send-Button klicken")
            btn.click()
            return
        logger.info("[*] Send-Button nicht enabled nach 9s")
    except Exception as e:
        logger.info(f"[*] Send-Button Fehler: {e}")

    clicked = page.evaluate("""() => {
        const btn = document.querySelector('[data-testid="send-button"]') ||
                    document.querySelector('button[aria-label*="Send"]') ||
                    document.querySelector('button[type="submit"]');
        if (btn && !btn.disabled) { btn.click(); return true; }
        return false;
    }""")
    if clicked:
        logger.info("[*] Send via JS-Click")
        return
    logger.info("[*] Send via Enter")
    page.keyboard.press("Enter")


def _extract_file_id(src: str) -> str:
    """Extrahiert file_id aus ChatGPT estuary-URLs; fallback: volle URL."""
    m = re.search(r'id=(file_[^&]+)', src)
    return m.group(1) if m else src


def get_image_snapshot(page) -> set:
    """Scrollt den ChatGPT-Nachrichten-Container nach unten um lazy-Bilder zu laden,
    dann gibt alle file_ids (bzw. URLs) als Set zurück."""
    # ChatGPT hat einen eigenen Scroll-Container, nicht window/body
    page.evaluate("""() => {
        const container = document.querySelector(
            'div[class*="overflow-y-auto"], main, [role="main"], .flex-col.overflow-y-auto'
        );
        if (container) {
            container.scrollTop = container.scrollHeight;
        } else {
            window.scrollTo(0, document.body.scrollHeight);
        }
    }""")
    page.wait_for_timeout(8000)

    srcs = page.evaluate("""() =>
        Array.from(document.querySelectorAll('img[src]'))
            .map(img => img.src)
            .filter(src => src.length > 40 && !src.endsWith('.svg'))
    """)
    return {_extract_file_id(s) for s in (srcs or [])}


def find_bottom_image(page) -> str | None:
    """Nimmt das unterste generierte Bild im DOM – das ist immer die aktuellste Antwort."""
    return page.evaluate("""() => {
        const skip = ['avatar', 'logo', 'favicon', 'icon', 'spinner', 'profile', 'badge', 'button', 'auth0'];

        function isGeneratedImg(src) {
            if (!src || src.endsWith('.svg')) return false;
            if (skip.some(s => src.toLowerCase().includes(s))) return false;
            return true;
        }

        // Strategie 1: letzter Assistant-Message-Container (treffsicher, egal ob noch am Laden)
        const msgs = document.querySelectorAll(
            '[data-message-author-role="assistant"], article[data-testid*="conversation-turn"]'
        );
        if (msgs.length > 0) {
            const lastMsg = msgs[msgs.length - 1];
            for (const img of lastMsg.querySelectorAll('img[src]')) {
                if (isGeneratedImg(img.src)) return img.src;
            }
        }

        // Strategie 2: alle Bilder nach Position (Fallback)
        const imgs = Array.from(document.querySelectorAll('img[src]'));
        imgs.sort((a, b) => {
            const ay = a.getBoundingClientRect().top + window.scrollY;
            const by = b.getBoundingClientRect().top + window.scrollY;
            return by - ay;
        });
        for (const img of imgs) {
            const src = img.src || '';
            if (!isGeneratedImg(src)) continue;
            const w = img.naturalWidth || img.width || 0;
            const h = img.naturalHeight || img.height || 0;
            if (w > 200 || h > 200) return src;
            if (src.startsWith('blob:') || src.includes('chatgpt.com/backend') ||
                src.includes('oaiusercontent') || src.includes('oaidalleapiprodscus') ||
                src.includes('files.oai') || src.includes('file-')) return src;
        }
        return null;
    }""")


def wait_for_new_image(page, logger, snapshot: set, timeout_sec: int = 180) -> str | None:
    """Wartet bis ein neues Bild ganz unten erscheint (unterste DOM-Position, nicht im Snapshot)."""
    logger.info("[*] Warte auf neues Bild (unterste Position)...")
    page.wait_for_timeout(5000)

    deadline = time.time() + timeout_sec
    elapsed = 5
    while time.time() < deadline:
        # Zum Ende scrollen damit das neueste Bild sichtbar/geladen ist
        page.evaluate("""() => {
            const c = document.querySelector('div[class*="overflow-y-auto"], main, [role="main"]');
            if (c) c.scrollTop = c.scrollHeight;
            else window.scrollTo(0, document.body.scrollHeight);
        }""")
        page.wait_for_timeout(500)

        src = find_bottom_image(page)
        if src and _extract_file_id(src) not in snapshot:
            # Kurz warten damit finale URL geladen ist (kein Placeholder)
            page.wait_for_timeout(3000)
            src2 = find_bottom_image(page)
            final = src2 if src2 else src
            logger.info(f"[*] Neues Bild gefunden nach ~{elapsed}s: {final[:80]}")
            return final
        logger.info(f"    ... generiert noch ({elapsed}s vergangen, max {timeout_sec}s)")
        page.wait_for_timeout(9500)
        elapsed += 10

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

    stereo = row.get("stereotyp", "")
    prompt = load_prompt(nr, stereo)
    if not prompt:
        logger.error(f"[-] Kein Prompt für #{nr} (Story-Datei fehlt)")
        return False
    out_path = OUTPUT_DIR / f"{nr_str(nr)}_pic_{ir.safe_name(stereo)}.png"

    logger.info(f"")
    logger.info(f"{'='*60}")
    logger.info(f"  Story #{nr}: {stereo}")
    logger.info(f"{'='*60}")
    logger.info(f"[*] Prompt: {prompt[:100]}...")

    # Zur ChatGPT-Konversation navigieren (Stereotypen vs. Namen-URL)
    target_url = get_chatgpt_url(nr)
    if target_url not in page.url:
        page.goto(target_url, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)

    dismiss_popups(page)

    # Eingabefeld finden
    editor = find_input(page)
    if not editor:
        logger.error("[-] Eingabefeld nicht gefunden – bitte Edge öffnen und ChatGPT laden")
        return False

    # Snapshot: alle aktuellen Bilder merken
    snapshot = get_image_snapshot(page)
    logger.info(f"[*] Snapshot: {len(snapshot)} Bild-IDs gespeichert")

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
CDP_PORT = 9222


def start_edge_with_debug(logger):
    import subprocess, urllib.request
    # CDP bereits aktiv?
    for host in ["127.0.0.1", "localhost"]:
        try:
            urllib.request.urlopen(f"http://{host}:{CDP_PORT}/json/version", timeout=2)
            logger.info(f"[+] CDP-Port bereits aktiv ({host})")
            return f"http://{host}:{CDP_PORT}"
        except Exception:
            pass

    # Edge-Browser-Prozesse beenden
    logger.info("[*] Beende laufende Edge-Prozesse...")
    subprocess.run(["taskkill", "/F", "/IM", "msedge.exe"], capture_output=True)
    for _ in range(10):
        time.sleep(1)
        r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq msedge.exe"], capture_output=True)
        if b"msedge.exe" not in (r.stdout or b""):
            break
    logger.info("[*] Edge-Prozesse beendet")

    # CDP-Profilordner (persistiert zwischen Runs – Session bleibt erhalten)
    CDP_USER_DATA.mkdir(parents=True, exist_ok=True)

    logger.info(f"[*] Starte Edge mit Debug-Port {CDP_PORT} (CDP-Profil)...")
    subprocess.Popen([EDGE_EXE,
                      f"--remote-debugging-port={CDP_PORT}",
                      "--remote-allow-origins=*",
                      f"--user-data-dir={CDP_USER_DATA}",
                      "--no-first-run",
                      get_chatgpt_url(nrs[0]) if nrs else CHATGPT_IMAGE_URL])

    for i in range(20):
        time.sleep(2)
        for host in ["127.0.0.1", "localhost"]:
            try:
                urllib.request.urlopen(f"http://{host}:{CDP_PORT}/json/version", timeout=2)
                logger.info(f"[+] Edge bereit via {host} (nach {(i+1)*2}s)")
                return f"http://{host}:{CDP_PORT}"
            except Exception:
                pass
        logger.info(f"    ... warte ({(i+1)*2}s)")
    logger.error("[-] Edge Debug-Port nicht erreichbar")
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--story", type=str, required=True)
    parser.add_argument("--wait", type=int, default=DEFAULT_WAIT_SEC)
    args = parser.parse_args()

    logger = setup_logging()
    from playwright.sync_api import sync_playwright

    nrs = parse_stories(args.story)
    to_process = [nr for nr in nrs
                  if not (ir.find_row(nr, INPUT_FILE) or {}).get("status_pic") == "X"]
    if not to_process:
        logger.info("[+] Keine Stories zu verarbeiten.")
        return

    logger.info(f"[*] {len(to_process)} Story/s: {', '.join(to_process)}")

    cdp_url = start_edge_with_debug(logger)
    if not cdp_url:
        sys.exit(1)

    with sync_playwright() as pw:
        browser = pw.chromium.connect_over_cdp(cdp_url)
        context = browser.contexts[0] if browser.contexts else browser.new_context()
        first_url = get_chatgpt_url(to_process[0])
        page = next((p for p in context.pages if "chatgpt.com" in p.url), None)
        if page is None:
            page = context.new_page()
            page.goto(first_url, wait_until="domcontentloaded")
            page.wait_for_timeout(4000)
        if first_url not in page.url:
            page.goto(first_url, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
        logger.info(f"[*] Seite: {page.url[:60]}")

        dismiss_popups(page)

        ok = err = 0
        for i, nr in enumerate(to_process):
            # Zur richtigen URL navigieren wenn sich der Story-Typ ändert
            target_url = get_chatgpt_url(nr)
            if target_url not in page.url:
                logger.info(f"[*] Wechsle zu {target_url[:60]}")
                page.goto(target_url, wait_until="domcontentloaded")
                page.wait_for_timeout(3000)

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
