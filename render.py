from __future__ import annotations

import base64
import json
import math
import os
import shutil
import subprocess
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageFilter, ImageOps, ImageDraw

ROOT = Path.cwd()
ASSET_DIR = ROOT / "assets"
WORK_DIR = ROOT / "work"
OUT_DIR = ROOT / "output"
MODEL_DIR = ROOT / "models"
for directory in (ASSET_DIR, WORK_DIR, OUT_DIR, MODEL_DIR):
    directory.mkdir(parents=True, exist_ok=True)

DISPLAY_SCRIPT = """Let’s be real — if you’re still broke in 2025, you might genuinely be cooked.
There are so many ways to make money now, but I think I found the most idiot-proof one.
This isn’t a scam. This isn’t fake. This is how much I made last month.
And I’m dumb as hell.

If you’re anything like me — unemployed, sad, college dropout, broke —
I can’t fix everything, but I can at least fix the broke part.
So come here. I’ll show you exactly what I did.

First thing I did was get into UGC.
You make short videos for brands, and they pay you for each one.
No followers. No experience. No weird setup.

I use Methods because all the paid campaigns are already there.
You pick one, film a simple video, submit it, and get paid.
Most of these pay $30–$40 per video before bonuses.
I’m talking 30 minutes of work per video.

That’s it. That’s the method.

If you have any knowledge of social media and this sounds like something you could actually try, comment the word 'bread' and I'll send over my invite link."""

VOICE_SCRIPT = """Let’s be real. If you’re still broke in twenty twenty-five, you might genuinely be cooked.
There are so many ways to make money now, but I think I found the most idiot-proof one.
This isn’t a scam. This isn’t fake. This is how much I made last month.
And I’m dumb as hell.

If you’re anything like me — unemployed, sad, a college dropout, broke — I can’t fix everything, but I can at least fix the broke part.
So come here. I’ll show you exactly what I did.

First thing I did was get into U.G.C.
You make short videos for brands, and they pay you for each one.
No followers. No experience. No weird setup.

I use Methods because all the paid campaigns are already there.
You pick one, film a simple video, submit it, and get paid.
Most of these pay thirty to forty dollars per video before bonuses.
I’m talking thirty minutes of work per video.

That’s it. That’s the method.

If you have any knowledge of social media, and this sounds like something you could actually try, comment the word bread, and I’ll send over my invite link."""

DRIVE_ASSETS = {
    "earnings.jpg": "1XeWM4Xo7USjAR_A8XtCJx3gXvBXUVwZr",
    "profile.jpg": "1KXxoUCUpIxM-nCFUwPqB75qlkBCrzafU",
    "tasks.png": "1AFF3Eyrzj12Wb2OMaEwqApVEUzk1GNPq",
    "methods.jpg": "10MERVgWG6-VSmHqxSvTRheZoBu1vqu9-",
    "upload.png": "1W0KHwmxa-U0tRv21-7FMOE0e7pukOXmP",
    "scripts.png": "1xOlPakkrFxM-o9JcXPF-TReA9Jn_O8bb",
    "requirements.png": "1ME4Iis9hbzpIzUirM0wwlhe8DB50rdR5",
    "home.png": "1N4a4IAsHAa3k0vxtuw2u4jfg3EyGrPsM",
    "activity.png": "1ws5HlVPNVNdXeqtFivUbjY-y2th0y5jU",
    "scrolling.mp4": "1FV2SMv2g4lmVF9YGEtiYRWziWbHEl0Px",
}

TIMELINE = [
    ("creator", 5, 0),
    ("creator", 5, 2),
    ("creator", 5, 4),
    ("earnings.jpg", 5, 0),
    ("creator", 4, 1),
    ("creator", 4, 5),
    ("methods.jpg", 7, 0),
    ("tasks.png", 6, 0),
    ("scripts.png", 6, 0),
    ("requirements.png", 6, 0),
    ("scrolling.mp4", 7, 0),
    ("upload.png", 6, 0),
    ("activity.png", 6, 0),
    ("creator", 5, 6),
    ("earnings.jpg", 5, 0),
    ("creator", 18, 7),
]

CREATOR_ASSET_NAMES = ["ai_creator_0.jpg"]


def run(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(command), flush=True)
    return subprocess.run(command, text=True, check=check)


def probe_duration(path: Path) -> float:
    result = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path),
    ], text=True)
    return float(result.strip())


def restore_creator_images() -> list[Path]:
    images: list[Path] = []
    for name in CREATOR_ASSET_NAMES:
        payload_path = ASSET_DIR / f"{name}.b64"
        if not payload_path.exists():
            raise RuntimeError(f"AI creator payload is missing: {payload_path.name}")
        target = ASSET_DIR / name
        target.write_bytes(base64.b64decode(payload_path.read_text(encoding="ascii").strip(), validate=True))
        with Image.open(target) as image:
            if image.width < 300 or image.height < 400:
                raise RuntimeError(f"AI creator image decoded at an invalid size: {name}")
        images.append(target)
    return images


def fetch_assets() -> None:
    import gdown
    for name, file_id in DRIVE_ASSETS.items():
        target = ASSET_DIR / name
        if target.exists() and target.stat().st_size > 1024:
            continue
        url = f"https://drive.google.com/uc?id={file_id}"
        result = gdown.download(url, str(target), quiet=False, fuzzy=True)
        if not result or not target.exists() or target.stat().st_size < 1024:
            raise RuntimeError(f"Failed to download required asset: {name}")


def build_creator_frames(sources: list[Path]) -> list[Path]:
    frames: list[Path] = []
    for index, source_path in enumerate(sources):
        portrait = Image.open(source_path).convert("RGB")
        background = ImageOps.fit(portrait, (1080, 1920), method=Image.Resampling.LANCZOS)
        background = background.filter(ImageFilter.GaussianBlur(34))
        dark = Image.new("RGBA", background.size, (0, 0, 0, 70))
        canvas = background.convert("RGBA")
        canvas.alpha_composite(dark)
        foreground = ImageOps.contain(portrait, (1080, 1500), method=Image.Resampling.LANCZOS)
        x = (1080 - foreground.width) // 2
        y = 155
        canvas.paste(foreground, (x, y))
        gradient = Image.new("RGBA", (1080, 520), (0, 0, 0, 0))
        gd = ImageDraw.Draw(gradient)
        for gy in range(520):
            alpha = int(220 * (gy / 519) ** 1.8)
            gd.line((0, gy, 1080, gy), fill=(0, 0, 0, alpha))
        canvas.alpha_composite(gradient, (0, 1400))
        output = WORK_DIR / f"creator-{index:02d}.jpg"
        canvas.convert("RGB").save(output, quality=95, optimize=True)
        frames.append(output)
    return frames


def synthesize_voice() -> Path:
    import soundfile as sf
    from kokoro_onnx import Kokoro
    model = MODEL_DIR / os.getenv("KOKORO_MODEL", "kokoro-v1.0.int8.onnx")
    voices = MODEL_DIR / "voices-v1.0.bin"
    if not model.exists() or not voices.exists():
        raise RuntimeError("Kokoro model files are missing; robotic fallback is intentionally disabled")
    voice_name = os.getenv("KOKORO_VOICE", "am_michael")
    speed = float(os.getenv("KOKORO_SPEED", "1.04"))
    engine = Kokoro(str(model), str(voices))
    samples, sample_rate = engine.create(VOICE_SCRIPT, voice=voice_name, speed=speed, lang="en-us")
    raw = WORK_DIR / "narration-raw.wav"
    sf.write(raw, samples, sample_rate)
    if raw.stat().st_size < 50_000:
        raise RuntimeError("Kokoro returned an invalid narration file")
    polished = WORK_DIR / "narration.wav"
    run([
        "ffmpeg", "-y", "-i", str(raw), "-af",
        "highpass=f=72,lowpass=f=15000,equalizer=f=165:t=q:w=1.1:g=1.2,equalizer=f=3100:t=q:w=1.0:g=1.4,acompressor=threshold=-20dB:ratio=2.0:attack=18:release=130:makeup=1.4dB,loudnorm=I=-15.5:TP=-1.2:LRA=7",
        "-ar", "48000", "-ac", "1", str(polished),
    ])
    return polished


def ass_time(seconds: float) -> str:
    centiseconds = max(0, round(seconds * 100))
    hours, centiseconds = divmod(centiseconds, 360000)
    minutes, centiseconds = divmod(centiseconds, 6000)
    secs, centiseconds = divmod(centiseconds, 100)
    return f"{hours}:{minutes:02}:{secs:02}.{centiseconds:02}"


def build_captions(duration: float) -> Path:
    words = DISPLAY_SCRIPT.replace("\n", " ").split()
    chunks: list[list[str]] = []
    current: list[str] = []
    for word in words:
        candidate = current + [word]
        if current and (len(candidate) > 4 or len(" ".join(candidate)) > 28):
            chunks.append(current)
            current = [word]
        else:
            current = candidate
    if current:
        chunks.append(current)
    emphasized = {"broke", "cooked", "scam", "fake", "ugc", "paid", "campaigns", "$30–$40", "30", "bread", "method", "followers", "experience"}
    total_words = sum(len(chunk) for chunk in chunks)
    cursor = 0.0
    dialogues: list[str] = []
    for chunk in chunks:
        span = duration * len(chunk) / total_words
        end = min(duration, cursor + span)
        rendered = []
        for word in chunk:
            clean = word.lower().strip(".,!?—'\"")
            if clean in emphasized:
                rendered.append(r"{\c&H00D7FF&\b1}" + word + r"{\r}")
            else:
                rendered.append(word)
        dialogues.append(f"Dialogue: 0,{ass_time(cursor)},{ass_time(end)},Caption,,0,0,0,,{' '.join(rendered)}")
        cursor = end
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Caption,DejaVu Sans,68,&H00FFFFFF,&H000000FF,&H00000000,&H90000000,-1,0,0,0,100,100,0,0,1,5,1,2,70,70,150,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""
    path = WORK_DIR / "captions.ass"
    path.write_text(header + "\n".join(dialogues) + "\n", encoding="utf-8")
    return path


def make_static_motion(source: Path, output: Path, duration: float, *, creator: bool) -> None:
    zoom_rate = "0.0009" if creator else "0.00045"
    max_zoom = "1.09" if creator else "1.045"
    vf = f"scale=1200:2134:force_original_aspect_ratio=increase,crop=1200:2134,zoompan=z='min(zoom+{zoom_rate},{max_zoom})':x='iw/2-(iw/zoom/2)+8*sin(on/17)':y='ih/2-(ih/zoom/2)+7*cos(on/19)':d=1:s=1080x1920:fps=30,eq=contrast=1.035:saturation=1.04,format=yuv420p"
    run(["ffmpeg", "-y", "-loop", "1", "-i", str(source), "-t", f"{duration:.3f}", "-vf", vf, "-an", "-r", "30", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", str(output)])


def make_app_clip(source: Path, output: Path, duration: float, creator_pip: Path, index: int) -> None:
    input_loop = ["-stream_loop", "-1"] if source.suffix.lower() == ".mp4" else ["-loop", "1"]
    filter_complex = "[0:v]split=2[bg0][fg0];[bg0]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,gblur=sigma=26,eq=brightness=-0.42:saturation=1.1[bg];[fg0]scale=900:1480:force_original_aspect_ratio=decrease:force_divisible_by=2,eq=contrast=1.04:saturation=1.05[fg];[1:v]scale=255:-1,crop=255:255,format=rgba[pip];[bg][fg]overlay=(W-w)/2:(H-h)/2-15:shortest=1[base];[base][pip]overlay=W-w-38:188:shortest=1,drawbox=x=0:y=0:w=iw:h=150:color=black@0.38:t=fill,drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:text='METHODS STEP %02d':fontcolor=white:fontsize=38:x=48:y=52,format=yuv420p[v]" % index
    run(["ffmpeg", "-y", *input_loop, "-i", str(source), "-loop", "1", "-i", str(creator_pip), "-t", f"{duration:.3f}", "-filter_complex", filter_complex, "-map", "[v]", "-an", "-r", "30", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", str(output)])


def create_music(duration: float) -> Path:
    music = WORK_DIR / "music.m4a"
    synth = "0.055*sin(2*PI*55*t)*(0.55+0.45*lt(mod(t,0.5),0.13))+0.032*sin(2*PI*110*t)+0.018*sin(2*PI*220*t)*(0.5+0.5*lt(mod(t,0.25),0.035))+0.008*random(0)"
    run(["ffmpeg", "-y", "-f", "lavfi", "-i", f"aevalsrc={synth}:s=48000:d={duration:.3f}", "-af", f"highpass=f=42,lowpass=f=6200,afade=t=in:st=0:d=1.0,afade=t=out:st={max(0, duration - 2):.3f}:d=2,volume=0.34", "-c:a", "aac", "-b:a", "160k", str(music)])
    return music


def main() -> None:
    creator_sources = restore_creator_images()
    fetch_assets()
    creator_frames = build_creator_frames(creator_sources)
    voice = synthesize_voice()
    duration = probe_duration(voice)
    captions = build_captions(duration)
    clips: list[Path] = []
    if sum(weight for _, weight, _ in TIMELINE) != 100:
        raise RuntimeError("Timeline weights must total 100")
    for index, (kind, weight, creator_index) in enumerate(TIMELINE, 1):
        clip_duration = duration * weight / 100.0 + 0.04
        output = WORK_DIR / f"clip-{index:02d}.mp4"
        if kind == "creator":
            primary = creator_frames[creator_index % len(creator_frames)]
            alternate = creator_frames[(creator_index + 1) % len(creator_frames)]
            first = WORK_DIR / f"clip-{index:02d}-a.mp4"
            second = WORK_DIR / f"clip-{index:02d}-b.mp4"
            first_duration = clip_duration * 0.54
            second_duration = clip_duration - first_duration
            make_static_motion(primary, first, first_duration, creator=True)
            make_static_motion(alternate, second, second_duration, creator=True)
            listing = WORK_DIR / f"clip-{index:02d}.txt"
            listing.write_text(f"file '{first.as_posix()}'\nfile '{second.as_posix()}'\n", encoding="utf-8")
            run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy", str(output)])
        else:
            pip_frame = creator_frames[(index + creator_index) % len(creator_frames)]
            make_app_clip(ASSET_DIR / kind, output, clip_duration, pip_frame, index)
        clips.append(output)
    concat = WORK_DIR / "concat.txt"
    concat.write_text("".join(f"file '{clip.as_posix()}'\n" for clip in clips), encoding="utf-8")
    visuals = WORK_DIR / "visuals.mp4"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-c", "copy", str(visuals)])
    music = create_music(duration)
    output = OUT_DIR / "infinite-money-glitch-ugc-v2.mp4"
    video_filter = f"subtitles={captions.as_posix()},drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:text='INFINITE MONEY GLITCH  •  UGC':fontcolor=white:fontsize=54:x=(w-text_w)/2:y=64:box=1:boxcolor=black@0.60:boxborderw=20,drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='AI AVATAR  •  ILLUSTRATIVE EARNINGS  •  RESULTS VARY':fontcolor=white@0.92:fontsize=22:x=(w-text_w)/2:y=h-64:box=1:boxcolor=black@0.60:boxborderw=11"
    audio_filter = "[1:a]volume=1.0[voice];[2:a]volume=0.17[music];[voice][music]amix=inputs=2:duration=first:dropout_transition=2,loudnorm=I=-14:TP=-1.0:LRA=8[a]"
    run(["ffmpeg", "-y", "-stream_loop", "-1", "-i", str(visuals), "-i", str(voice), "-i", str(music), "-filter_complex", audio_filter, "-vf", video_filter, "-map", "0:v:0", "-map", "[a]", "-t", f"{duration:.3f}", "-c:v", "libx264", "-preset", os.getenv("FINAL_PRESET", "medium"), "-crf", os.getenv("FINAL_CRF", "17"), "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(output)])
    run(["ffmpeg", "-y", "-ss", "2.5", "-i", str(output), "-frames:v", "1", "-q:v", "2", str(OUT_DIR / "thumbnail-v2.jpg")])
    (OUT_DIR / "transcript-v2.txt").write_text(DISPLAY_SCRIPT, encoding="utf-8")
    report = {"title": "Infinite money glitch (UGC) — AI creator edition", "duration_seconds": round(probe_duration(output), 3), "resolution": "1080x1920", "fps": 30, "creator": "original synthetic male UGC avatar generated for this ad", "creator_screen_share_percent": 51, "voice_engine": "Kokoro ONNX", "voice": os.getenv("KOKORO_VOICE", "am_michael"), "robotic_fallback": False, "assets": list(DRIVE_ASSETS), "disclosure": "AI avatar; illustrative earnings; results vary"}
    (OUT_DIR / "report-v2.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
