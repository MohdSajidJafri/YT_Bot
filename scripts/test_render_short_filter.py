#!/usr/bin/env python3
from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from pipeline.render_short import HOOK_OVERLAY_SECONDS, TITLE_OVERLAY_SECONDS, render_vertical_short


def main() -> None:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        srt_path = tmp / "captions.srt"
        srt_path.write_text("1\n00:00:00,000 --> 00:00:01,000\nhello\n", encoding="utf-8")
        audio_path = tmp / "voiceover.mp3"
        audio_path.write_bytes(b"")
        out_video = tmp / "short.mp4"

        calls: list[tuple[list[str], str | None]] = []

        def _fake_run(cmd: list[str], check: bool = True, cwd: str | None = None):
            calls.append((cmd, cwd))
            return None

        with (
            patch("pipeline.render_short.shutil.which", return_value="/usr/bin/ffmpeg"),
            patch("pipeline.render_short.subprocess.run", side_effect=_fake_run),
        ):
            render_vertical_short(
                image_paths=[tmp / "img1.png", tmp / "img2.png"],
                total_duration=10.0,
                audio_path=audio_path,
                srt_path=srt_path,
                out_video=out_video,
                title_text="The hitchhiker's dilemma",
                hook_text="I've always been drawn here",
                cta_text="Subscribe for more",
            )

    cmd = calls[-1][0]
    fc = cmd[cmd.index("-filter_complex") + 1]
    assert "HITCHHIKER\\\\'S" in fc
    assert f"between(t\\,0\\,{TITLE_OVERLAY_SECONDS:.2f})" in fc
    assert f"between(t\\,0.15\\,{HOOK_OVERLAY_SECONDS:.2f})" in fc
    assert "gte(t\\," in fc
    print("render_short filter expression escaping test passed")


if __name__ == "__main__":
    main()
