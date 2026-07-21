from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path.cwd()
ASSET_DIR = ROOT / "assets"
WORK_DIR = ROOT / "work"
OUT_DIR = ROOT / "output"
for directory in (ASSET_DIR, WORK_DIR, OUT_DIR):
    directory.mkdir(parents=True, exist_ok=True)

SCRIPT = """Let’s be real — if you’re still broke in 2025, you might genuinely be cooked.
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

ASSETS = {
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
SEQUENCE = [
    "earnings.jpg", "profile.jpg", "scrolling.mp4", "tasks.png",
    "methods.jpg", "scripts.png", "requirements.png", "scrolling.mp4",
    "home.png", "activity.png", "upload.png", "earnings.jpg",
]


def run(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(command), flush=True)
    return subprocess.run(command, text=True, check=check)


def fetch_assets() -> None:
    import gdown
    for name, file_id in ASSETS.items():
        target = ASSET_DIR / name
        if target.exists() and target.stat().st_size > 1024:
            continue
        url = f"https://drive.google.com/uc?id={file_id}"
        result = gdown.download(url, str(target), quiet=False, fuzzy=True)
        if not result or not target.exists() or target.stat().st_size < 1024:
            raise RuntimeError(f"Failed to download required asset: {name}")


async def neural_voice(path: Path) -> bool:
    try:
        import edge_tts
        voice = os.getenv("EDGE_TTS_VOICE", "en-US-GuyNeural")
        communicate = edge_tts.Communicate(SCRIPT, voice, rate="+12%", pitch="-2Hz")
        await communicate.save(str(path))
        return path.exists() and path.stat().st_size > 1024
    except Exception as exc:
        print(f"Neural narration unavailable: {exc}")
        return False


def narration() -> Path:
    text_path = WORK_DIR / "transcript.txt"
    text_path.write_text(SCRIPT, encoding="utf-8")
    mp3 = WORK_DIR / "narration.mp3"
    if asyncio.run(neural_voice(mp3)):
        return mp3
    wav = WORK_DIR / "narration.wav"
    run(["espeak", "-s", "175", "-p", "42", "-a", "165", "-f", str(text_path), "-w", str(wav)])
    return wav


def probe_duration(path: Path) -> float:
    result = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path)
    ], text=True)
    return float(result.strip())


def srt_time(seconds: float) -> str:
    ms = max(0, round(seconds * 1000))
    hours, ms = divmod(ms, 3_600_000)
    minutes, ms = divmod(ms, 60_000)
    secs, ms = divmod(ms, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{ms:03}"


def captions(duration: float) -> Path:
    words = SCRIPT.replace("\n", " ").split()
    chunks: list[list[str]] = []
    current: list[str] = []
    for word in words:
        candidate = current + [word]
        if current and (len(candidate) > 4 or len(" ".join(candidate)) > 25):
            chunks.append(current)
            current = [word]
        else:
            current = candidate
    if current:
        chunks.append(current)
    total_words = sum(len(chunk) for chunk in chunks)
    elapsed = 0.0
    lines = []
    for index, chunk in enumerate(chunks, 1):
        span = duration * len(chunk) / total_words
        end = min(duration, elapsed + span)
        lines.extend([str(index), f"{srt_time(elapsed)} --> {srt_time(end)}", " ".join(chunk), ""])
        elapsed = end
    path = WORK_DIR / "captions.srt"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def make_clip(source: Path, output: Path, duration: float, index: int) -> None:
    input_args = ["-stream_loop", "-1"] if source.suffix.lower() == ".mp4" else ["-loop", "1"]
    foreground_y = "(H-h)/2+18*sin(t*0.75)"
    vf = (
        "[0:v]split=2[bg0][fg0];"
        "[bg0]scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,gblur=sigma=24,eq=brightness=-0.38:saturation=1.15[bg];"
        "[fg0]scale=920:1600:force_original_aspect_ratio=decrease:force_divisible_by=2,"
        "eq=contrast=1.04:saturation=1.07[fg];"
        f"[bg][fg]overlay=(W-w)/2:{foreground_y}:shortest=1,"
        "drawbox=x=0:y=0:w=iw:h=150:color=black@0.30:t=fill,"
        f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
        f"text='METHOD {index:02d}':fontcolor=white:fontsize=34:x=52:y=54,"
        "format=yuv420p[v]"
    )
    run([
        "ffmpeg", "-y", *input_args, "-i", str(source), "-t", f"{duration:.3f}",
        "-filter_complex", vf, "-map", "[v]", "-an", "-r", "30",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", str(output)
    ])


def main() -> None:
    fetch_assets()
    voice = narration()
    duration = probe_duration(voice)
    caption_path = captions(duration)
    clip_duration = duration / len(SEQUENCE) + 0.18
    clips: list[Path] = []
    for index, name in enumerate(SEQUENCE, 1):
        clip = WORK_DIR / f"clip-{index:02d}.mp4"
        make_clip(ASSET_DIR / name, clip, clip_duration, index)
        clips.append(clip)
    concat = WORK_DIR / "concat.txt"
    concat.write_text("".join(f"file '{clip.as_posix()}'\n" for clip in clips), encoding="utf-8")
    visuals = WORK_DIR / "visuals.mp4"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-c", "copy", str(visuals)])
    music = WORK_DIR / "music.m4a"
    synth = "0.13*sin(2*PI*110*t)+0.09*sin(2*PI*164.81*t)+0.07*sin(2*PI*220*t)"
    run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", f"aevalsrc={synth}:s=48000:d={duration:.3f}",
        "-af", f"lowpass=f=1200,afade=t=in:st=0:d=1.2,afade=t=out:st={max(0,duration-2):.3f}:d=2,volume=0.16",
        "-c:a", "aac", "-b:a", "160k", str(music)
    ])
    output = OUT_DIR / "infinite-money-glitch-ugc.mp4"
    subtitle_filter = (
        f"subtitles={caption_path.as_posix()}:force_style='FontName=DejaVu Sans,FontSize=18,"
        "PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=3,Outline=2,"
        "Shadow=1,Alignment=2,MarginV=55',"
        "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
        "text='INFINITE MONEY GLITCH':fontcolor=white:fontsize=58:x=(w-text_w)/2:y=70:"
        "box=1:boxcolor=black@0.58:boxborderw=22,"
        "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
        "text='AI-GENERATED AD - ILLUSTRATIVE EARNINGS - RESULTS VARY':"
        "fontcolor=white@0.90:fontsize=23:x=(w-text_w)/2:y=h-72:box=1:boxcolor=black@0.55:boxborderw=12"
    )
    audio_filter = (
        "[1:a]loudnorm=I=-16:TP=-1.5:LRA=9[voice];"
        "[2:a]volume=0.20[music];"
        "[voice][music]amix=inputs=2:duration=first:dropout_transition=2[a]"
    )
    run([
        "ffmpeg", "-y", "-stream_loop", "-1", "-i", str(visuals), "-i", str(voice), "-i", str(music),
        "-filter_complex", audio_filter, "-vf", subtitle_filter,
        "-map", "0:v:0", "-map", "[a]", "-t", f"{duration:.3f}",
        "-c:v", "libx264", "-preset", os.getenv("FINAL_PRESET", "medium"),
        "-crf", os.getenv("FINAL_CRF", "17"), "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(output)
    ])
    run(["ffmpeg", "-y", "-ss", "2", "-i", str(output), "-frames:v", "1", "-q:v", "2", str(OUT_DIR / "thumbnail.jpg")])
    shutil.copy2(WORK_DIR / "transcript.txt", OUT_DIR / "transcript.txt")
    report = {
        "title": "Infinite money glitch (UGC)",
        "duration_seconds": round(probe_duration(output), 3),
        "resolution": "1080x1920",
        "fps": 30,
        "assets": list(ASSETS),
        "voice": os.getenv("EDGE_TTS_VOICE", "en-US-GuyNeural"),
        "disclosure": "AI-generated ad; illustrative earnings; results vary",
    }
    (OUT_DIR / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
