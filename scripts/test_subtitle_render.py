import subprocess
import shutil
import re
from pathlib import Path
from PIL import Image

tmp = Path("output/test_caption")
tmp.mkdir(parents=True, exist_ok=True)
fonts_dir = Path("assets/fonts").resolve()

def _ms_to_ass(ms: int) -> str:
    h = ms // 3_600_000
    m = (ms % 3_600_000) // 60_000
    s = (ms % 60_000) // 1_000
    cs = (ms % 1_000) // 10
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

def _srt_time_to_ms(t_str: str) -> int:
    t_str = t_str.strip().replace(",", ".")
    parts = t_str.split(":")
    h = int(parts[0])
    m = int(parts[1])
    s_parts = parts[2].split(".")
    s = int(s_parts[0])
    ms = int(s_parts[1].ljust(3, "0")[:3])
    return (h * 3600 + m * 60 + s) * 1000 + ms

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
    srt_text = srt_path.read_text(encoding="utf-8").strip()
    blocks = re.split(r"\n\s*\n", srt_text)

    events = []
    for b in blocks:
        lines = [ln.strip() for ln in b.splitlines() if ln.strip()]
        if len(lines) >= 3 and "-->" in lines[1]:
            t_match = re.match(r"(\S+)\s*-->\s*(\S+)", lines[1])
            if t_match:
                start_ms = _srt_time_to_ms(t_match.group(1))
                end_ms = _srt_time_to_ms(t_match.group(2))
                text = " ".join(lines[2:])
                events.append(
                    f"Dialogue: 0,{_ms_to_ass(start_ms)},{_ms_to_ass(end_ms)},Default,,0,0,0,,{text}"
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

# Test with multi-line SRT
sample_srt = tmp / "sample.srt"
sample_srt.write_text("""1
00:00:00,000 --> 00:00:02,500
The classroom clock ticks

2
00:00:02,500 --> 00:00:05,000
backwards at midnight
""", encoding="utf-8")

sample_ass = tmp / "sample.ass"
srt_to_ass(sample_srt, sample_ass, font_name="Creepster", font_size=72, margin_v=460)

(tmp / "_fonts").mkdir(exist_ok=True)
shutil.copyfile(fonts_dir / "CreepsterCaps.ttf", tmp / "_fonts" / "CreepsterCaps.ttf")

out_video = tmp / "sample.mp4"
cmd = [
    "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=black:s=1080x1920:d=4:r=30",
    "-vf", "subtitles=sample.ass:fontsdir='_fonts'",
    "-c:v", "libx264", "-pix_fmt", "yuv420p",
    str(out_video.resolve())
]
p = subprocess.run(cmd, capture_output=True, text=True, cwd=str(tmp))
print("FFmpeg return code:", p.returncode)
if p.returncode != 0:
    print(p.stderr[-300:])
else:
    print("Video rendered successfully!")

# Extract a frame at 1.0s and verify captions exist
frame_png = tmp / "frame_1s.png"
subprocess.run([
    "ffmpeg", "-y", "-ss", "1.0", "-i", str(out_video.resolve()),
    "-vframes", "1", str(frame_png.resolve())
], capture_output=True)

im = Image.open(frame_png)
bg = im.getpixel((0, 0))
non_bg_y = []
for y in range(im.height):
    for x in range(im.width):
        if im.getpixel((x, y)) != bg:
            non_bg_y.append(y)
            break
if non_bg_y:
    print(f"FOUND text in video at Y={min(non_bg_y)} to Y={max(non_bg_y)} (center={int((min(non_bg_y)+max(non_bg_y))/2)}px)")
else:
    print("NO TEXT FOUND IN VIDEO!")


