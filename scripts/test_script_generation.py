#!/usr/bin/env python3
"""Quickly test script generation using your configured API key (.env)."""

import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

# Load .env (supports both python-dotenv and fallback parsing)
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

from pipeline.channel_presets import get_preset
from pipeline.groq_script import generate_short_pack


def main():
    channel = sys.argv[1] if len(sys.argv) > 1 else "ghost_stories"
    preset = get_preset(channel)

    print(f"🎬 Testing script generation for channel: '{channel}'...")
    try:
        pack = generate_short_pack(preset, channel_id=channel)
    except Exception as e:
        print(f"\n❌ Script generation failed: {e}")
        sys.exit(1)

    title = pack.get("youtube_title", "")
    desc = pack.get("youtube_description", "")
    narration = pack.get("full_narration", "")
    pinned = pack.get("pinned_comment", "")
    prompts = pack.get("image_prompts", [])
    word_count = len(narration.split())

    print("\n" + "=" * 60)
    print("🔥 GENERATED SHORT SCRIPT PREVIEW")
    print("=" * 60)
    print(f"\n📌 TITLE: {title}")
    print(f"📝 DESCRIPTION: {desc}")
    print(f"💬 PINNED COMMENT: {pinned}")
    print(f"\n🎙️ NARRATION ({word_count} words):")
    print(f"   \"{narration}\"")

    sentences = [s.strip() for s in narration.replace("!", ".").replace("?", ".").split(".") if s.strip()]
    if sentences:
        print(f"\n🪝 OPENING HOOK (first sentence):")
        print(f"   \"{sentences[0]}\"")
        print(f"\n🔄 SEAMLESS LOOP CHECK (last sentence -> first sentence):")
        print(f"   End:   \"{sentences[-1]}\"")
        print(f"   Start: \"{sentences[0]}\"")

    print(f"\n🎨 IMAGE PROMPTS ({len(prompts)} scenes):")
    for i, p in enumerate(prompts, 1):
        print(f"   Scene {i}: {p}")

    print("\n" + "=" * 60)
    print("✅ Test succeeded! Your API key and prompt pipeline are working perfectly.")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
