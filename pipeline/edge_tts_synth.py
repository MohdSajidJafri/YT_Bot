"""Edge TTS — free, no API key. Returns audio + sentence-level timestamps."""
from __future__ import annotations

import asyncio
import os
import subprocess
from pathlib import Path
from typing import TypedDict

VOICE = "en-US-ChristopherNeural"


class SentenceTiming(TypedDict):
    text: str
    offset_ms: int
    duration_ms: int


def _ffprobe_duration(path: Path, fallback_dur: float = 0.0) -> float:
    import shutil
    if not shutil.which("ffprobe"):
        return fallback_dur
    try:
        out = subprocess.check_output(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            text=True,
        ).strip()
        return float(out)
    except Exception:
        return fallback_dur


async def _synthesize_with_timing(
    text: str, out_path: Path, voice: str,
) -> list[SentenceTiming]:
    import edge_tts

    # Request WordBoundary for frame-perfect millisecond word synchronization
    communicate = edge_tts.Communicate(text, voice, boundary="WordBoundary")
    words: list[SentenceTiming] = []
    sentences: list[SentenceTiming] = []

    with open(out_path, "wb") as audio_file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_file.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                words.append(
                    SentenceTiming(
                        text=chunk["text"],
                        offset_ms=int(chunk["offset"]) // 10_000,
                        duration_ms=int(chunk["duration"]) // 10_000,
                    )
                )
            elif chunk["type"] == "SentenceBoundary":
                sentences.append(
                    SentenceTiming(
                        text=chunk["text"],
                        offset_ms=int(chunk["offset"]) // 10_000,
                        duration_ms=int(chunk["duration"]) // 10_000,
                    )
                )

    # Prefer exact word-level boundaries; fallback to sentence-level if voice doesn't emit words
    return words if words else sentences


def synthesize_full(
    text: str, out_path: Path, voice: str | None = None,
) -> tuple[float, list[SentenceTiming]]:
    """TTS the full narration. Returns (duration_seconds, sentence_timings)."""
    # Sanitize text to remove emojis, symbols, or stage cues that cause TTS hallucination
    import re
    text = re.sub(r"[\U00010000-\U0010ffff\u2600-\u27bf\u2300-\u23ff\u2b50-\u2b55\ufe00-\ufe0f\u200d]+", "", text)
    text = re.sub(r"\[.*?\]|\(.*?\)", "", text)
    text = re.sub(r"[*_#~`]", "", text)
    text = " ".join(text.split())

    voice = voice or os.environ.get("EDGE_TTS_VOICE", VOICE)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cues = asyncio.run(_synthesize_with_timing(text, out_path, voice))
    fallback_dur = (cues[-1]["offset_ms"] + cues[-1]["duration_ms"]) / 1000.0 if cues else 0.0
    dur = _ffprobe_duration(out_path, fallback_dur=fallback_dur) or fallback_dur
    return dur, cues
