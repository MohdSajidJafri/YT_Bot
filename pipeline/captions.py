"""Build SRT and ASS captions from Edge TTS sentence-level timestamps.

Splits each sentence into word groups (~3-5 words) and distributes
timing proportionally within the sentence's known time window.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.edge_tts_synth import SentenceTiming


EMOJI_PATTERN = re.compile(
    r"[\U00010000-\U0010ffff\u2600-\u27bf\u2300-\u23ff\u2b50-\u2b55\ufe00-\ufe0f\u200d\u20e3]+",
    flags=re.UNICODE,
)


def strip_emojis(text: str) -> str:
    """Remove all emojis and decorative symbols."""
    if not text:
        return ""
    clean = EMOJI_PATTERN.sub("", str(text))
    return " ".join(clean.split())


def _fmt_srt(ms: int) -> str:
    """Milliseconds -> SRT timestamp (00:00:00,000)."""
    h = ms // 3_600_000
    m = (ms % 3_600_000) // 60_000
    s = (ms % 60_000) // 1_000
    frac = ms % 1_000
    return f"{h:02d}:{m:02d}:{s:02d},{frac:03d}"


def _fmt_ass(ms: int) -> str:
    """Milliseconds -> ASS timestamp (0:00:00.00)."""
    h = ms // 3_600_000
    m = (ms % 3_600_000) // 60_000
    s = (ms % 60_000) // 1_000
    cs = (ms % 1_000) // 10
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _srt_time_to_ms(t_str: str) -> int:
    """Convert SRT time string (00:00:01,250) to milliseconds."""
    t_str = t_str.strip().replace(",", ".")
    parts = t_str.split(":")
    h = int(parts[0])
    m = int(parts[1])
    s_parts = parts[2].split(".")
    s = int(s_parts[0])
    ms = int(s_parts[1].ljust(3, "0")[:3])
    return (h * 3600 + m * 60 + s) * 1000 + ms


def _is_word_level(cues: list[SentenceTiming]) -> bool:
    """Check if cues contain individual words (WordBoundary) vs full sentences."""
    if not cues:
        return False
    sample = cues[:min(10, len(cues))]
    avg_words = sum(len(c["text"].split()) for c in sample) / len(sample)
    return avg_words <= 1.5


def _split_into_chunks(
    cues: list[SentenceTiming],
    max_words_per_line: int = 3,
) -> list[tuple[int, int, str]]:
    chunks: list[tuple[int, int, str]] = []
    if not cues:
        return chunks

    # Fast path: WordBoundary cues with microsecond-level precision
    if _is_word_level(cues):
        curr: list[SentenceTiming] = []
        for w in cues:
            txt = w["text"].strip()
            if not txt:
                continue
            curr.append(w)
            is_punct = any(txt.endswith(p) for p in (".", "!", "?", ",", ";", ":", "—", "-"))
            if len(curr) >= max_words_per_line or is_punct:
                s = curr[0]["offset_ms"]
                e = curr[-1]["offset_ms"] + curr[-1]["duration_ms"]
                t = strip_emojis(" ".join(item["text"].strip() for item in curr))
                if t:
                    chunks.append((s, e, t))
                curr = []
        if curr:
            s = curr[0]["offset_ms"]
            e = curr[-1]["offset_ms"] + curr[-1]["duration_ms"]
            t = strip_emojis(" ".join(item["text"].strip() for item in curr))
            if t:
                chunks.append((s, e, t))
        return chunks

    # Fallback path: SentenceBoundary cues (evenly distributed)
    for sent in cues:
        words = sent["text"].split()
        if not words:
            continue

        start_ms = sent["offset_ms"]
        dur_ms = sent["duration_ms"]

        if len(words) <= max_words_per_line:
            clean_t = strip_emojis(sent["text"])
            if clean_t:
                chunks.append((start_ms, start_ms + dur_ms, clean_t))
        else:
            n_groups = (len(words) + max_words_per_line - 1) // max_words_per_line
            ms_per_word = dur_ms / len(words) if words else 1

            pos = 0
            for g in range(n_groups):
                grp_start = pos
                grp_end = min(pos + max_words_per_line, len(words))
                grp_text = " ".join(words[grp_start:grp_end])

                t_start = start_ms + int(grp_start * ms_per_word)
                t_end = start_ms + int(grp_end * ms_per_word)
                t_end = min(t_end, start_ms + dur_ms)

                clean_grp = strip_emojis(grp_text)
                if clean_grp:
                    chunks.append((t_start, t_end, clean_grp))
                pos = grp_end

    return chunks


def build_srt(
    sentences: list[SentenceTiming],
    out_path: Path,
    total_duration: float,
    *,
    max_words_per_line: int = 3,
) -> Path:
    """Create .srt from sentence timestamps, splitting long sentences."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if not sentences:
        out_path.write_text("", encoding="utf-8")
        return out_path

    chunks = _split_into_chunks(sentences, max_words_per_line=max_words_per_line)
    lines: list[str] = []
    for i, (start, end, text) in enumerate(chunks):
        lines.append(str(i + 1))
        lines.append(f"{_fmt_srt(start)} --> {_fmt_srt(end)}")
        lines.append(text)
        lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


def srt_to_ass(
    srt_path: Path,
    ass_path: Path,
    *,
    font_name: str = "Creepster",
    font_size: int = 72,
    margin_v: int = 460,
    width: int = 1080,
    height: int = 1920,
) -> Path:
    """Convert an existing .srt file to .ass with exact 1080x1920 canvas resolution."""
    srt_path = Path(srt_path)
    ass_path = Path(ass_path)
    ass_path.parent.mkdir(parents=True, exist_ok=True)

    if not srt_path.is_file():
        ass_path.write_text("", encoding="utf-8")
        return ass_path

    srt_text = srt_path.read_text(encoding="utf-8").strip()
    blocks = re.split(r"\n\s*\n", srt_text)

    events: list[str] = []
    for b in blocks:
        lines = [ln.strip() for ln in b.splitlines() if ln.strip()]
        if len(lines) >= 3 and "-->" in lines[1]:
            t_match = re.match(r"(\S+)\s*-->\s*(\S+)", lines[1])
            if t_match:
                start_ms = _srt_time_to_ms(t_match.group(1))
                end_ms = _srt_time_to_ms(t_match.group(2))
                text = strip_emojis(" ".join(lines[2:]).replace("\n", " ").strip())
                if text:
                    events.append(
                        f"Dialogue: 0,{_fmt_ass(start_ms)},{_fmt_ass(end_ms)},Default,,0,0,0,,{text}"
                    )

    ass_header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,5,0,2,40,40,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ass_content = ass_header + "\n".join(events) + "\n"
    ass_path.write_text(ass_content, encoding="utf-8")
    return ass_path

