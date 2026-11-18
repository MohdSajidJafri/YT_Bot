#!/usr/bin/env python3
"""Test image generation using free Pollinations.ai (Flux/SDXL)."""

import os
import sys
import time
import urllib.parse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

# Load .env
try:
    from dotenv import load_dotenv
    load_dotenv(REPO_ROOT / ".env")
except ImportError:
    env_file = REPO_ROOT / ".env"
    if env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

import httpx
from pipeline.channel_presets import get_preset
from pipeline.images import full_visual_prompt

OUT_DIR = REPO_ROOT / "output" / "test_images"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# 4 diverse horror scenes for testing
TEST_BEATS = [
    "an eerie empty school classroom at 3 AM with moonlight cutting through dusty windows",
    "a shadowy figure standing alone at an old chalkboard in darkness",
    "close-up of antique chalk floating and writing impossible symbols on the wall",
    "a terrifying long dark school corridor with faint flickering green emergency lights",
]


def generate_pollinations_image(
    prompt: str,
    out_path: Path,
    width: int = 768,
    height: int = 1360,
    model: str = "flux",
) -> bool:
    """Download image from Pollinations.ai free API."""
    encoded_prompt = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&model={model}&nologo=true&private=true"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }

    print(f"   Downloading: {out_path.name} ({width}x{height}, model={model})...")
    with httpx.Client(timeout=90.0, follow_redirects=True) as client:
        for attempt in range(1, 4):
            try:
                resp = client.get(url, headers=headers)
                if resp.status_code == 200 and len(resp.content) > 5000:
                    out_path.write_bytes(resp.content)
                    size_kb = len(resp.content) // 1024
                    print(f"   ✅ Saved {out_path.name} ({size_kb} KB)")
                    return True
                elif resp.status_code in (402, 429):
                    wait_s = 46
                    try:
                        import re
                        m = re.search(r"Retry after (\d+)s", resp.text)
                        if m:
                            wait_s = int(m.group(1)) + 2
                    except Exception:
                        pass
                    print(f"   ⏳ Pollinations free IP limit (Status {resp.status_code}). Waiting {wait_s}s...")
                    time.sleep(wait_s)
                else:
                    print(f"   ⚠️ Status {resp.status_code}, retrying...")
                    time.sleep(5)
            except Exception as e:
                print(f"   ⚠️ Error on attempt {attempt}: {e}")
                time.sleep(4)

    return False


def main():
    preset = get_preset("ghost_stories")
    style_suffix = preset.get("image_style_suffix", "")
    w = int(os.environ.get("DEAPI_IMAGE_WIDTH", "768"))
    h = int(os.environ.get("DEAPI_IMAGE_HEIGHT", "1360"))

    print("🎨 Generating test images with Pollinations.ai (Free Flux)...")
    print(f"📁 Destination folder: {OUT_DIR}\n")

    results = []
    for i, beat in enumerate(TEST_BEATS, 1):
        prompt = full_visual_prompt(beat, style_suffix=style_suffix)
        out_file = OUT_DIR / f"test_scene_{i:02d}.png"
        ok = generate_pollinations_image(prompt, out_file, width=w, height=h, model="flux")
        results.append((out_file, ok))
        if i < len(TEST_BEATS):
            time.sleep(2)

    succeeded = [f for f, ok in results if ok]
    print("\n" + "=" * 60)
    print(f"🎉 Complete! Successfully generated {len(succeeded)}/{len(TEST_BEATS)} images.")
    print(f"📂 Check your images in: {OUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
