import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from pipeline.captions import strip_emojis as cap_strip, _split_into_chunks, srt_to_ass, EMOJI_PATTERN
from pipeline.groq_script import strip_emojis as groq_strip, sanitize_narration
from pipeline.render_short import _escape_drawtext_text, _compact_overlay_text

def test_emoji_elimination():
    sample_with_emojis = "The Whispering Mirror 👻💀 Warning: Do not look! ⚠️👁️ It is watching you... 🩸⏳"
    
    # 1. Direct strip functions
    c1 = cap_strip(sample_with_emojis)
    c2 = groq_strip(sample_with_emojis)
    assert not EMOJI_PATTERN.search(c1), f"Found emoji in c1: {c1}"
    assert not EMOJI_PATTERN.search(c2), f"Found emoji in c2: {c2}"
    assert "👻" not in c1 and "💀" not in c1 and "⚠️" not in c1 and "👁" not in c1 and "🩸" not in c1
    print("PASS: strip_emojis removes all test emojis")

    # 2. Render overlays
    escaped = _escape_drawtext_text(sample_with_emojis)
    assert not EMOJI_PATTERN.search(escaped), f"Found emoji in escaped: {escaped}"
    compacted = _compact_overlay_text(sample_with_emojis, 30)
    assert not EMOJI_PATTERN.search(compacted), f"Found emoji in compacted: {compacted}"
    print("PASS: render overlays are emoji-free")

    # 3. Narration sanitizer
    narr = sanitize_narration("Don't turn around [screams] 😱 just run! 🏃💨")
    assert not EMOJI_PATTERN.search(narr), f"Found emoji in narration: {narr}"
    assert "[screams]" not in narr
    print("PASS: narration sanitizer clean:", narr)

    # 4. Word boundary chunks
    fake_words = [
        {"text": "Don't", "offset_ms": 0, "duration_ms": 300},
        {"text": "look 💀", "offset_ms": 300, "duration_ms": 400},
        {"text": "behind.", "offset_ms": 700, "duration_ms": 500},
    ]
    chunks = _split_into_chunks(fake_words, max_words_per_line=3)
    for s, e, t in chunks:
        assert not EMOJI_PATTERN.search(t), f"Found emoji in chunk: {t}"
    print("PASS: caption chunks are emoji-free")

    # 5. srt_to_ass
    srt_tmp = REPO_ROOT / "output" / "verification" / "temp_emoji_test.srt"
    ass_tmp = REPO_ROOT / "output" / "verification" / "temp_emoji_test.ass"
    srt_tmp.parent.mkdir(parents=True, exist_ok=True)
    srt_tmp.write_text("1\n00:00:00,000 --> 00:00:01,000\nBeware 👻 of the dark 💀\n\n", encoding="utf-8")
    srt_to_ass(srt_tmp, ass_tmp)
    ass_content = ass_tmp.read_text(encoding="utf-8")
    assert "👻" not in ass_content and "💀" not in ass_content
    assert not EMOJI_PATTERN.search(ass_content)
    srt_tmp.unlink(missing_ok=True)
    ass_tmp.unlink(missing_ok=True)
    print("PASS: ASS subtitle generation completely removes emojis")

    print("\nALL EMOJI ELIMINATION TESTS PASSED 100%!")

if __name__ == "__main__":
    test_emoji_elimination()
