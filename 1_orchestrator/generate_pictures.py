#!/usr/bin/env python3
"""
Agent 2: Generiert Meme-Bilder via OpenAI gpt-image-1.

Story-Text wird direkt als Bildkontext übergeben – kein Claude-Zwischenschritt.

Verwendung:
  python generate_pictures.py 1        # Bild für Story #1
  python generate_pictures.py 1-10     # Bilder für Stories #1–10
"""

import os
import sys
import json
import base64
import argparse
import logging
from pathlib import Path

import yaml
import requests
from dotenv import load_dotenv

import input_reader as ir

load_dotenv()


def setup_logging() -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )
    return logging.getLogger(__name__)


def load_config(config_path: str = "config.yaml") -> dict:
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_story_text(nr: int, stories_dir: str) -> str | None:
    """Lese Story-Text aus 1_input/."""
    nr_str = f"{int(nr):03d}"

    for p in Path(stories_dir).glob(f"{nr_str}_*.txt"):
        return p.read_text(encoding="utf-8").strip()

    return None


SCENE_DIRECTION_PROMPT = """You are a visual art director for cinematic illustration campaigns about German culture and everyday life.

GLOBAL CONTEXT: All stories take place in Germany. Scenes must feel authentically German — think German supermarkets (REWE, Edeka, Aldi), German streets, Autobahn, German homes, offices, parks, bakeries, hardware stores (Bauhaus, OBI), beer gardens, etc. Characters dress like typical Germans. Signs, labels, and products in the background should look German.

STYLE: The illustrations are cinematic, highly detailed, semi-realistic — like a dramatic film still or graphic novel panel. NOT cartoonish, NOT flat, NOT playful. Grounded realism with subtle comic rendering, textured surfaces, natural imperfections.

MOOD: Derive the mood from the story. Most stories are ironic or absurdly serious — lean into that. The humor comes from treating mundane German habits with cinematic gravitas, not from silly bright colors. Mood options: "grounded and ironic", "slightly dramatic", "deadpan serious", "tense and absurd", "warm but solemn". Pick the one that fits.

Convert this German stereotype story into a precise visual scene direction for an image generation model.

Stereotype title: "{stereotyp}"
Story: {story_text}

Respond ONLY with a JSON object with these exact fields (all in English):
- scene: 1-2 sentences describing the specific German location and situation
- main_subject: description of the main character (appearance, pose, expression, clothing — typical German style, realistic proportions)
- secondary_characters: background characters and their reactions (max 1 sentence)
- environment_details: 2-3 specific visual objects/details that make the scene feel authentically German
- chaos_element: the single most visually striking/ironic element
- lighting: cinematic lighting description (direction, color temperature, contrast — avoid generic "warm and bright")
- mood: one short phrase describing the emotional tone of this specific scene

No extra text, only the JSON."""


def generate_scene_direction(api_key: str, stereotyp: str, story_text: str) -> dict:
    """Nutze GPT-4o um Story → visuelle Szenenanweisung zu konvertieren."""
    prompt = SCENE_DIRECTION_PROMPT.format(stereotyp=stereotyp, story_text=story_text)
    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": "gpt-4o",
            "max_tokens": 400,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
        },
        timeout=30,
    )
    response.raise_for_status()
    return json.loads(response.json()["choices"][0]["message"]["content"])


def build_image_prompt(stereotyp: str, scene: dict) -> str:
    """Baue finalen Image-Prompt aus strukturierten Szenen-Parametern."""
    mood = scene.get("mood", "grounded and ironic")
    return f"""A cinematic, highly detailed digital illustration in a semi-realistic comic style, resembling a dramatic film still. The scene takes place in Germany and must feel authentically German in setting, characters, and props.

Scene: {scene['scene']}

Main subject: {scene['main_subject']}

Secondary characters: {scene['secondary_characters']}

Environment details: {scene['environment_details']} Key visual element: {scene['chaos_element']}

Lighting: {scene['lighting']}

Mood: {mood}. The humor comes from treating a mundane German habit with cinematic gravitas — subtle irony, not slapstick.

Visual style: dark, moody, grounded realism with subtle comic rendering. Not cartoony. Not flat. Highly textured surfaces and natural imperfections.

Rendering quality: ultra detailed, sharp focus, realistic materials (skin, fabric, wood, glass), visible textures and fine details.

Color grading: slightly desaturated, realistic tones, subtle filmic color grading, no oversaturated colors.

Composition: like a movie scene, strong depth (foreground, midground, background), clear subject focus, natural perspective, immersive environment with storytelling details.

Camera: slightly wide-angle lens, eye-level, strong foreground-background separation.

Text overlay: very large bold title at the very top, occupying ~20% of the image height:
"{stereotyp.upper()}"

Typography: thick, bold, high contrast, white with dark outline, extremely readable against any background.

Avoid: flat cartoon style, simple shapes, bright playful colors, minimal shading, exaggerated cartoon proportions.

Style references: cinematic illustration, graphic novel realism, film still, noir-inspired atmosphere, authentically German setting.

Strict vertical 9:16 composition, optimized for Instagram Reels."""


def generate_image(api_key: str, prompt: str, nr: int, images_dir: str, logger: logging.Logger) -> bool:
    """Generiere Bild via OpenAI gpt-image-1 und speichere es."""
    url = "https://api.openai.com/v1/images/generations"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "gpt-image-1",
        "prompt": prompt,
        "size": "1024x1536",
        "quality": "high",
        "n": 1,
    }

    logger.info(f"[*] OpenAI API: gpt-image-1, 1024x1536, quality=high")
    logger.info(f"[*] Prompt (Auszug): {prompt[:150]}...")

    response = requests.post(url, headers=headers, json=payload, timeout=120)

    if response.status_code != 200:
        logger.error(f"[-] OpenAI Fehler {response.status_code}: {response.text[:300]}")
        return False

    data = response.json()
    image_item = data.get("data", [{}])[0]

    if "b64_json" in image_item:
        img_data = base64.b64decode(image_item["b64_json"])
    elif "url" in image_item:
        img_data = requests.get(image_item["url"], timeout=60).content
    else:
        logger.error("[-] Kein Bild in der API-Antwort")
        return False

    Path(images_dir).mkdir(parents=True, exist_ok=True)
    out_path = Path(images_dir) / f"{nr:03d}_pic.png"
    out_path.write_bytes(img_data)
    logger.info(f"[+] Bild gespeichert: {out_path} ({len(img_data):,} Bytes)")
    return True


def process_story_image(nr: int, config: dict, logger: logging.Logger, openai_key: str) -> bool:
    input_file = config["output"]["input_file"]
    stories_dir = config["output"]["stories_dir"]
    images_dir = config["output"]["images_dir"]

    row = ir.find_row(nr, input_file)
    if not row:
        logger.error(f"[-] Story #{nr} nicht gefunden")
        return False

    stereotyp = row["stereotyp"].strip()

    if row.get("status_pic") == "X":
        logger.info(f"[O] Story #{nr} bereits mit Bild – überspringe")
        return True

    logger.info("=" * 60)
    logger.info(f"Bild für Story #{nr}: {stereotyp}")
    logger.info("=" * 60)

    story_text = get_story_text(nr, stories_dir)
    if not story_text:
        logger.error(f"[-] Kein Story-Text für #{nr} gefunden.")
        return False

    logger.info(f"[*] GPT-4o: Story → visuelle Szenenanweisung...")
    try:
        scene = generate_scene_direction(openai_key, stereotyp, story_text)
        logger.info(f"[+] Szene: {scene.get('scene', '')[:80]}...")
    except Exception as e:
        logger.error(f"[-] GPT-4o Fehler: {e}")
        return False

    prompt = build_image_prompt(stereotyp, scene)
    logger.info(f"[*] Image-Prompt gebaut ({len(prompt)} Zeichen)")
    success = generate_image(openai_key, prompt, nr, images_dir, logger)

    if success:
        ir.update_field(nr, "status_pic", "X", input_file)
        logger.info(f"[+] CSV: status_pic=X")

    return success


def parse_range(input_str: str) -> list[str]:
    import re
    input_str = input_str.strip()
    if "," in input_str:
        return [v.strip() for v in input_str.split(",") if v.strip()]
    m = re.match(r'^(\d+)_(\d+)-\d+_(\d+)$', input_str)
    if m:
        prefix, start, end = m.group(1), int(m.group(2)), int(m.group(3))
        width = len(m.group(2))
        return [f"{prefix}_{i:0{width}d}" for i in range(start, end + 1)]
    if "-" in input_str and "_" not in input_str:
        parts = input_str.split("-")
        return [str(i) for i in range(int(parts[0]), int(parts[1]) + 1)]
    return [input_str]


def main():
    parser = argparse.ArgumentParser(description="Generiere Meme-Bilder für Stereotypen-Stories")
    parser.add_argument("story", nargs="?", help="Story-Nummer oder Bereich (z.B. 1 oder 1-10)")
    parser.add_argument("--config", default="config.yaml")
    args = parser.parse_args()

    logger = setup_logging()
    config = load_config(args.config)

    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        logger.error("[-] OPENAI_API_KEY fehlt in .env")
        sys.exit(1)

    if not args.story:
        print("Verwendung: python generate_pictures.py <nummer>")
        print("  Beispiel:  python generate_pictures.py 1")
        print("  Beispiel:  python generate_pictures.py 1-10")
        sys.exit(1)

    numbers = parse_range(args.story)
    logger.info(f"[*] Generiere Bilder für: {numbers}")

    success_count = 0
    for nr in numbers:
        if process_story_image(nr, config, logger, openai_key):
            success_count += 1

    logger.info("=" * 60)
    logger.info(f"[+] Generiert: {success_count}/{len(numbers)} Bilder")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
