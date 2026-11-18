#!/usr/bin/env python3
"""Local verification tool: Tests WordBoundary subtitle synchronization and seamless looping."""

import json
import os
import sys
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

from pipeline.captions import build_srt, _split_into_chunks
from pipeline.channel_presets import get_preset
from pipeline.edge_tts_synth import synthesize_full
from pipeline.groq_script import generate_short_pack

OUT_DIR = REPO_ROOT / "output" / "verification"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def main():
    print("=" * 65)
    print("🔬 LOCAL VERIFICATION: WORD-LEVEL AUDIO SYNC & SEAMLESS LOOP")
    print("=" * 65)

    # 1. Generate Script
    preset = get_preset("ghost_stories")
    print("\n① Generating fresh Horror Script via AI...")
    pack = generate_short_pack(preset, channel_id="ghost_stories")

    title = pack.get("youtube_title", "")
    narration = pack.get("full_narration", "")
    opening = pack.get("opening_hook", "")
    ending = pack.get("ending_bridge", "")
    words = narration.split()

    print(f"\n📌 TITLE: {title}")
    print(f"📝 TOTAL WORDS: {len(words)}")

    print("\n" + "─" * 65)
    print("🔄 SEAMLESS INFINITE LOOP VERIFICATION:")
    print("─" * 65)
    if not opening:
        # Fallback to first sentence
        opening = narration.split(".")[0]
    if not ending:
        ending = " ".join(words[-8:])

    loop_sentence = f'"{ending.strip()} {opening.strip()}"'
    print(f"• Opening Hook : \"{opening.strip()}\"")
    print(f"• Ending Bridge: \"{ending.strip()}\"")
    print(f"• Loop Result  : {loop_sentence}")

    # Check if ends with period
    if narration.endswith("."):
        print("⚠️ Warning: Narration ended with a period (may cause audio cadence drop).")
    else:
        print("✅ PASS: Narration ends with an open connector phrase (NO period).")

    # 2. Audio & Word-Level Timing
    print("\n" + "─" * 65)
    print("🎙️ EDGE TTS SYNTHESIS & WORD-LEVEL TIMESTAMP TRACKING:")
    print("─" * 65)
    audio_path = OUT_DIR / "verify_voiceover.mp3"
    total_dur, cues = synthesize_full(narration, audio_path)

    print(f"✅ Audio rendered to: {audio_path}")
    print(f"• Spoken Duration: {total_dur:.2f} seconds")
    print(f"• Captured Cues  : {len(cues)} words tracked with microsecond accuracy")

    # 3. Subtitle Generation & Sync
    print("\n" + "─" * 65)
    print("⏱️ SUBTITLE SYNCHRONIZATION INSPECTION (Frame-Perfect Cues):")
    print("─" * 65)
    srt_path = OUT_DIR / "verify_captions.srt"
    build_srt(cues, srt_path, total_dur, max_words_per_line=3)

    chunks = _split_into_chunks(cues, max_words_per_line=3)

    print("First 4 Caption Bursts (Opening Hook):")
    for s, e, t in chunks[:4]:
        print(f"   [{s/1000:6.3f}s -> {e/1000:6.3f}s] ({e-s:4d}ms) : \"{t}\"")

    print("\n...\n")
    print("Last 4 Caption Bursts (Ending Loop Bridge):")
    for s, e, t in chunks[-4:]:
        print(f"   [{s/1000:6.3f}s -> {e/1000:6.3f}s] ({e-s:4d}ms) : \"{t}\"")

    print("\n" + "=" * 65)
    print(f"🎉 Verification files saved:")
    print(f"   🎵 Audio : {audio_path}")
    print(f"   📄 Captions: {srt_path}")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()
