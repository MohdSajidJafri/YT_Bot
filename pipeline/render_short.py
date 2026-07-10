"""FFmpeg: images + audio + captions → vertical Short MP4 (9:16).

Effects:
  - Ken Burns zoom (alternating zoom-in / zoom-out per scene)
  - Fadeblack crossfade between scenes (horror vibe)
  - Creepster font captions at the bottom
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FONTS_DIR = REPO_ROOT / "assets" / "fonts"
DEFAULT_FONT_FILE = "CreepsterCaps.ttf"
DEFAULT_FONT_NAME = "Creepster"

FPS = 30
FADE_DUR = 0.5
ZOOM_AMOUNT = 0.08
TITLE_OVERLAY_SECONDS = 2.5
HOOK_OVERLAY_SECONDS = 4.0
CTA_OVERLAY_SECONDS = 2.2


def _escape_drawtext_text(text: str) -> str:
    """Escape user/model text for FFmpeg drawtext filter values."""
    return (
        text.replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\\'")
        .replace("%", "\\%")
        .replace("\n", " ")
        .strip()
    )


def _compact_overlay_text(text: str, max_chars: int) -> str:
    text = " ".join(text.split())
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "..."


def render_vertical_short(
    image_paths: list[Path],
    total_duration: float,
    audio_path: Path,
    srt_path: Path,
    out_video: Path,
    *,
    width: int = 1080,
    height: int = 1920,
    font_file: str = DEFAULT_FONT_FILE,
    font_name: str = DEFAULT_FONT_NAME,
    title_text: str | None = None,
    hook_text: str | None = None,
    cta_text: str | None = "SUBSCRIBE FOR MORE",
) -> None:
    if not image_paths:
        raise ValueError("No images")
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg not found; install it (brew install ffmpeg)")

    out_video = Path(out_video)
    out_video.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_video.parent / "_tmp_render"
    tmp.mkdir(parents=True, exist_ok=True)

    n = len(image_paths)
    clip_dur = (total_duration + (n - 1) * FADE_DUR) / n if n > 1 else total_duration
    frames_per_clip = max(int(clip_dur * FPS), 2)

    from concurrent.futures import ThreadPoolExecutor

    def scale_image(i: int, src: Path) -> None:
        dst = tmp / f"img_{i + 1:02d}.png"
        subprocess.run(
            [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "warning",
                "-i", str(src),
                "-vf", (f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
                        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black"),
                "-update", "1", "-frames:v", "1",
                str(dst),
            ],
            check=True,
        )

    # ── 1. Pre-scale images in parallel ──────────────────────────────
    print(f"   Pre-scaling {n} images in parallel…")
    with ThreadPoolExecutor() as executor:
        list(executor.map(lambda item: scale_image(*item), enumerate(image_paths)))

    def generate_clip(i: int) -> None:
        src_img = tmp / f"img_{i + 1:02d}.png"
        clip = tmp / f"clip_{i + 1:02d}.mp4"
        zoom_rate = ZOOM_AMOUNT / frames_per_clip

        if i % 2 == 0:
            zoom_expr = f"min(zoom+{zoom_rate:.8f},{1 + ZOOM_AMOUNT})"
        else:
            zoom_expr = f"if(eq(on,1),{1 + ZOOM_AMOUNT},max(zoom-{zoom_rate:.8f},1.0))"

        vf = (
            f"zoompan=z='{zoom_expr}':"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"d={frames_per_clip}:s={width}x{height}:fps={FPS},"
            f"format=yuv420p"
        )

        subprocess.run(
            [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "warning",
                "-i", str(src_img),
                "-vf", vf,
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "15",
                str(clip),
            ],
            check=True,
        )

    # ── 2. Generate zoompan clips in parallel ────────────────────────
    print(f"   Generating {n} zoompan clips in parallel…")
    with ThreadPoolExecutor() as executor:
        list(executor.map(generate_clip, range(n)))

    # ── 3. Prepare subtitles + font ──────────────────────────────────
    shutil.copyfile(srt_path, tmp / "captions.srt")

    font_path = FONTS_DIR / font_file
    rendered_font_name = "Arial"
    fontsdir_arg = ""
    if font_path.is_file():
        font_dir = tmp / "_fonts"
        font_dir.mkdir(exist_ok=True)
        shutil.copyfile(font_path, font_dir / font_path.name)
        rendered_font_name = font_name
        fontsdir_arg = ":fontsdir='_fonts'"
    else:
        print(f"   ⚠ Font {font_path} not found — using {rendered_font_name}")
    overlay_font_arg = ""
    if font_path.is_file():
        overlay_font_arg = f"fontfile='{(Path('_fonts') / font_path.name).as_posix()}':"

    force_style = (
        f"FontName={rendered_font_name},"
        f"FontSize=68,"
        f"PrimaryColour=&H00FFFFFF,"
        f"OutlineColour=&H00000000,"
        f"BackColour=&H9A000000,"
        f"BorderStyle=4,Outline=2,Bold=1,"
        f"Shadow=0,Alignment=2,"
        f"MarginV=550,MarginL=28,MarginR=28"
    )

    bg_music_path = REPO_ROOT / "assets" / "audio" / "spooky_bg.mp3"
    if not bg_music_path.is_file():
        print("   Background music not found. Downloading default spooky ambiance track…")
        try:
            import httpx
            bg_music_path.parent.mkdir(parents=True, exist_ok=True)
            url = "https://archive.org/download/waving-ant-analog-horror/10%20-%20Dread%20Ambience%20%28Found%20Archive%29.mp3"
            with httpx.Client(follow_redirects=True, timeout=60.0) as client:
                resp = client.get(url)
                resp.raise_for_status()
                bg_music_path.write_bytes(resp.content)
            print("   Downloaded background music successfully.")
        except Exception as e:
            print(f"   ⚠ Failed to download background music: {e} — continuing without background music.")

    inputs: list[str] = []
    for i in range(n):
        inputs += ["-i", f"clip_{i + 1:02d}.mp4"]
    inputs += ["-i", str(audio_path.resolve())]

    bg_music_idx = None
    if bg_music_path.is_file():
        inputs += ["-stream_loop", "-1", "-i", str(bg_music_path.resolve())]
        bg_music_idx = n + 1

    filter_parts: list[str] = []

    sub_label = "subs"
    if n == 1:
        filter_parts.append(
            f"[0:v]subtitles=captions.srt{fontsdir_arg}:"
            f"force_style='{force_style}'[{sub_label}]"
        )
    else:
        prev = "[0:v]"
        for i in range(n - 1):
            offset = (i + 1) * (clip_dur - FADE_DUR)
            next_v = f"[{i + 1}:v]"
            out = f"[x{i}]"
            filter_parts.append(
                f"{prev}{next_v}xfade=transition=fadeblack:"
                f"duration={FADE_DUR:.4f}:offset={offset:.4f}{out}"
            )
            prev = out
        filter_parts.append(
            f"{prev}subtitles=captions.srt{fontsdir_arg}:"
            f"force_style='{force_style}'[{sub_label}]"
        )

    # Retention overlays: fast title/hook at open, CTA at close. Optional args keep
    # the renderer backward-compatible for older callers and tests.
    overlay_input = sub_label
    overlay_idx = 0
    if title_text:
        text = _escape_drawtext_text(_compact_overlay_text(title_text.upper(), 44))
        out = f"ov{overlay_idx}"
        filter_parts.append(
            f"[{overlay_input}]drawtext=text='{text}':"
            f"{overlay_font_arg}"
            f"x=(w-text_w)/2:y=h*0.09:fontsize=72:"
            f"fontcolor=white:borderw=5:bordercolor=black:"
            f"box=1:boxcolor=black@0.55:boxborderw=24:"
            f"enable='between(t,0,{TITLE_OVERLAY_SECONDS:.2f})'[{out}]"
        )
        overlay_input = out
        overlay_idx += 1

    if hook_text:
        text = _escape_drawtext_text(_compact_overlay_text(hook_text.upper(), 62))
        out = f"ov{overlay_idx}"
        filter_parts.append(
            f"[{overlay_input}]drawtext=text='{text}':"
            f"{overlay_font_arg}"
            f"x=(w-text_w)/2:y=h*0.31:fontsize=54:"
            f"fontcolor=white:borderw=4:bordercolor=black:"
            f"box=1:boxcolor=black@0.48:boxborderw=20:"
            f"enable='between(t,0.15,{HOOK_OVERLAY_SECONDS:.2f})'[{out}]"
        )
        overlay_input = out
        overlay_idx += 1

    if cta_text:
        text = _escape_drawtext_text(_compact_overlay_text(cta_text.upper(), 34))
        out = f"ov{overlay_idx}"
        start_time = max(total_duration - CTA_OVERLAY_SECONDS, 0)
        filter_parts.append(
            f"[{overlay_input}]drawtext=text='{text}':"
            f"{overlay_font_arg}"
            f"x=(w-text_w)/2:y=h*0.12:fontsize=58:"
            f"fontcolor=white:borderw=4:bordercolor=black:"
            f"box=1:boxcolor=black@0.50:boxborderw=22:"
            f"enable='gte(t,{start_time:.2f})'[{out}]"
        )
        overlay_input = out
        overlay_idx += 1

    filter_parts.append(f"[{overlay_input}]format=yuv420p[final]")

    audio_map = f"{n}:a"
    if bg_music_idx is not None:
        filter_parts.append(f"[{bg_music_idx}:a]volume=0.08[bg]")
        filter_parts.append(f"[{n}:a][bg]amix=inputs=2:duration=first:dropout_transition=2[mixed_audio]")
        audio_map = "[mixed_audio]"

    fc = ";\n".join(filter_parts)

    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "warning",
        *inputs,
        "-filter_complex", fc,
        "-map", "[final]", "-map", audio_map,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        "-movflags", "+faststart",
        str(out_video.resolve()),
    ]
    subprocess.run(cmd, check=True, cwd=str(tmp))

    # ── cleanup ──────────────────────────────────────────────────────
    shutil.rmtree(tmp, ignore_errors=True)
