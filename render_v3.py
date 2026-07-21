from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageFilter, ImageOps

ROOT = Path.cwd()
ASSET_DIR = ROOT / "assets"
WORK_DIR = ROOT / "work-v3"
OUT_DIR = ROOT / "output"
MODEL_DIR = ROOT / "models"
for d in (ASSET_DIR, WORK_DIR, OUT_DIR, MODEL_DIR):
    d.mkdir(parents=True, exist_ok=True)

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
    "tasks.png": "1AFF3Eyrzj12Wb2OMaEwqApVEUzk1GNPq",
    "methods.jpg": "10MERVgWG6-VSmHqxSvTRheZoBu1vqu9-",
    "upload.png": "1W0KHwmxa-U0tRv21-7FMOE0e7pukOXmP",
    "scripts.png": "1xOlPakkrFxM-o9JcXPF-TReA9Jn_O8bb",
    "requirements.png": "1ME4Iis9hbzpIzUirM0wwlhe8DB50rdR5",
    "activity.png": "1ws5HlVPNVNdXeqtFivUbjY-y2th0y5jU",
    "scrolling.mp4": "1FV2SMv2g4lmVF9YGEtiYRWziWbHEl0Px",
}

SCENES = [
    ("creator", 7.0), ("creator", 6.0), ("earnings.jpg", 5.0),
    ("creator", 5.0), ("creator", 6.0), ("methods.jpg", 6.0),
    ("tasks.png", 5.0), ("scripts.png", 5.0), ("requirements.png", 5.0),
    ("scrolling.mp4", 7.0), ("upload.png", 5.0), ("activity.png", 5.0),
    ("earnings.jpg", 5.0), ("creator", 7.0), ("creator", 16.0),
]


def run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(cmd), flush=True)
    return subprocess.run(cmd, text=True, check=check)


def duration(path: Path) -> float:
    return float(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path),
    ], text=True).strip())


def restore_creator() -> Path:
    payload = ASSET_DIR / "ai_creator_0.jpg.b64"
    if not payload.exists():
        raise RuntimeError("AI creator payload missing")
    target = ASSET_DIR / "ai_creator_0.jpg"
    target.write_bytes(base64.b64decode(payload.read_text(encoding="ascii").strip(), validate=True))
    with Image.open(target) as image:
        if image.width < 300 or image.height < 400:
            raise RuntimeError(f"Invalid creator image: {image.size}")
    return target


def prepare_creator_image(source: Path) -> Path:
    portrait = Image.open(source).convert("RGB")
    background = ImageOps.fit(portrait, (768, 768), method=Image.Resampling.LANCZOS)
    background = background.filter(ImageFilter.GaussianBlur(18))
    foreground = ImageOps.contain(portrait, (650, 740), method=Image.Resampling.LANCZOS)
    canvas = background.copy()
    canvas.paste(foreground, ((768 - foreground.width) // 2, 18))
    target = WORK_DIR / "creator-square.jpg"
    canvas.save(target, quality=95)
    return target


def fetch_assets() -> None:
    import gdown
    for name, file_id in DRIVE_ASSETS.items():
        target = ASSET_DIR / name
        if target.exists() and target.stat().st_size > 1024:
            continue
        result = gdown.download(f"https://drive.google.com/uc?id={file_id}", str(target), quiet=False, fuzzy=True)
        if not result or not target.exists() or target.stat().st_size < 1024:
            raise RuntimeError(f"Failed to download {name}")


def synthesize_voice() -> Path:
    import soundfile as sf
    from kokoro_onnx import Kokoro

    model = MODEL_DIR / "kokoro-v1.0.int8.onnx"
    voices = MODEL_DIR / "voices-v1.0.bin"
    if not model.exists() or not voices.exists():
        raise RuntimeError("Kokoro models missing; no robotic fallback is allowed")
    engine = Kokoro(str(model), str(voices))
    samples, rate = engine.create(
        VOICE_SCRIPT,
        voice=os.getenv("KOKORO_VOICE", "am_michael"),
        speed=float(os.getenv("KOKORO_SPEED", "1.03")),
        lang="en-us",
    )
    raw = WORK_DIR / "voice-raw.wav"
    sf.write(raw, samples, rate)
    polished = WORK_DIR / "voice.wav"
    run([
        "ffmpeg", "-y", "-i", str(raw), "-af",
        "highpass=f=70,lowpass=f=15000,equalizer=f=180:t=q:w=1.1:g=1.4,equalizer=f=3200:t=q:w=1.0:g=1.2,acompressor=threshold=-20dB:ratio=2.1:attack=14:release=120:makeup=1.5dB,loudnorm=I=-15:TP=-1.2:LRA=7",
        "-ar", "48000", "-ac", "1", str(polished),
    ])
    if polished.stat().st_size < 100_000:
        raise RuntimeError("Natural narration generation failed")
    return polished


def endpoint_name(client) -> str:
    data = client.view_api(return_format="dict")
    named = data.get("named_endpoints", {}) if isinstance(data, dict) else {}
    if named:
        for name, spec in named.items():
            text = json.dumps(spec).lower()
            if "source image" in text or "driven audio" in text or "preprocess" in text:
                return name
        return next(iter(named))
    unnamed = data.get("unnamed_endpoints", {}) if isinstance(data, dict) else {}
    if unnamed:
        return next(iter(unnamed))
    raise RuntimeError(f"No callable SadTalker endpoint found: {data}")


def generate_talking_head(image: Path, voice: Path) -> Path:
    from gradio_client import Client, handle_file

    space = os.getenv("TALKING_HEAD_SPACE", "Beer1819/LipSyncerFull")
    client = Client(space, verbose=True)
    api_name = endpoint_name(client)
    print(f"Using {space} endpoint {api_name}")
    args = [
        handle_file(str(image)), handle_file(str(voice)), "crop", False, False,
        1, 256, 2, "facevid2vid", 1.15, False, None, "pose", False,
        max(1, int(duration(voice))), True,
    ]
    try:
        result = client.predict(*args, api_name=api_name)
    except Exception as first_error:
        print(f"Primary endpoint call failed: {first_error}")
        # Some SadTalker Spaces expose the shorter legacy endpoint.
        result = client.predict(
            handle_file(str(image)), handle_file(str(voice)), "crop", False, False,
            api_name=api_name,
        )
    candidate = result[0] if isinstance(result, (tuple, list)) else result
    if isinstance(candidate, dict):
        candidate = candidate.get("video") or candidate.get("path") or candidate.get("name")
    path = Path(str(candidate))
    if not path.exists():
        raise RuntimeError(f"SadTalker returned no local video: {result}")
    output = WORK_DIR / "talking-head.mp4"
    shutil.copy2(path, output)
    if output.stat().st_size < 100_000 or duration(output) < duration(voice) * 0.85:
        raise RuntimeError("Talking-head model returned an invalid video")
    return output


def ass_time(seconds: float) -> str:
    cs = max(0, round(seconds * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02}:{s:02}.{cs:02}"


def captions(total: float) -> Path:
    words = DISPLAY_SCRIPT.replace("\n", " ").split()
    chunks, current = [], []
    for word in words:
        trial = current + [word]
        if current and (len(trial) > 5 or len(" ".join(trial)) > 31):
            chunks.append(current)
            current = [word]
        else:
            current = trial
    if current:
        chunks.append(current)
    elapsed = 0.0
    events = []
    total_words = sum(len(c) for c in chunks)
    emphasis = {"broke", "cooked", "scam", "fake", "ugc", "paid", "campaigns", "bread", "method"}
    for chunk in chunks:
        span = total * len(chunk) / total_words
        rendered = []
        for word in chunk:
            clean = word.lower().strip(".,!?—'\"")
            rendered.append((r"{\c&H00D7FF&\b1}" + word + r"{\r}") if clean in emphasis else word)
        events.append(f"Dialogue: 0,{ass_time(elapsed)},{ass_time(min(total, elapsed + span))},Caption,,0,0,0,,{' '.join(rendered)}")
        elapsed += span
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Caption,DejaVu Sans,66,&H00FFFFFF,&H000000FF,&H00000000,&H90000000,-1,0,0,0,100,100,0,0,1,5,1,2,70,70,150,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""
    out = WORK_DIR / "captions.ass"
    out.write_text(header + "\n".join(events) + "\n", encoding="utf-8")
    return out


def make_creator_scene(talking: Path, out: Path, start: float, length: float) -> None:
    vf = (
        "split=2[bg0][fg0];"
        "[bg0]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,gblur=sigma=28,eq=brightness=-0.28[bg];"
        "[fg0]scale=1030:1700:force_original_aspect_ratio=decrease[fg];"
        "[bg][fg]overlay=(W-w)/2:(H-h)/2-30,eq=contrast=1.035:saturation=1.04,format=yuv420p"
    )
    run([
        "ffmpeg", "-y", "-ss", f"{start:.3f}", "-i", str(talking), "-t", f"{length:.3f}",
        "-vf", vf, "-an", "-r", "30", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", str(out),
    ])


def make_app_scene(asset: Path, talking: Path, out: Path, start: float, length: float, index: int) -> None:
    loop = ["-stream_loop", "-1"] if asset.suffix.lower() == ".mp4" else ["-loop", "1"]
    graph = (
        "[0:v]split=2[bg0][app0];"
        "[bg0]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,gblur=sigma=28,eq=brightness=-0.42[bg];"
        "[app0]scale=900:1480:force_original_aspect_ratio=decrease[app];"
        "[1:v]scale=290:290:force_original_aspect_ratio=increase,crop=290:290[pip];"
        "[bg][app]overlay=(W-w)/2:(H-h)/2-10[base];"
        "[base][pip]overlay=W-w-40:170,drawbox=x=0:y=0:w=iw:h=145:color=black@0.40:t=fill,"
        f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:text='METHODS STEP {index:02d}':fontcolor=white:fontsize=38:x=46:y=50,format=yuv420p[v]"
    )
    run([
        "ffmpeg", "-y", *loop, "-i", str(asset), "-ss", f"{start:.3f}", "-i", str(talking),
        "-t", f"{length:.3f}", "-filter_complex", graph, "-map", "[v]", "-an", "-r", "30",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", str(out),
    ])


def music(total: float) -> Path:
    out = WORK_DIR / "music.m4a"
    synth = "0.05*sin(2*PI*55*t)+0.028*sin(2*PI*110*t)+0.016*sin(2*PI*220*t)*(0.5+0.5*lt(mod(t,0.25),0.04))"
    run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", f"aevalsrc={synth}:s=48000:d={total:.3f}",
        "-af", f"highpass=f=42,lowpass=f=5200,afade=t=in:st=0:d=1,afade=t=out:st={max(0,total-2):.3f}:d=2,volume=0.22",
        "-c:a", "aac", "-b:a", "160k", str(out),
    ])
    return out


def main() -> None:
    creator = prepare_creator_image(restore_creator())
    fetch_assets()
    voice = synthesize_voice()
    total = duration(voice)
    talking = generate_talking_head(creator, voice)
    cap = captions(total)

    requested = sum(v for _, v in SCENES)
    cursor = 0.0
    clips = []
    for index, (kind, seconds) in enumerate(SCENES, 1):
        length = total * seconds / requested
        out = WORK_DIR / f"scene-{index:02d}.mp4"
        if kind == "creator":
            make_creator_scene(talking, out, cursor, length)
        else:
            make_app_scene(ASSET_DIR / kind, talking, out, cursor, length, index)
        clips.append(out)
        cursor += length

    concat = WORK_DIR / "concat.txt"
    concat.write_text("".join(f"file '{p.as_posix()}'\n" for p in clips), encoding="utf-8")
    visuals = WORK_DIR / "visuals.mp4"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-c", "copy", str(visuals)])
    bed = music(total)
    output = OUT_DIR / "infinite-money-glitch-ugc-v3.mp4"
    vf = (
        f"subtitles={cap.as_posix()},"
        "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:text='INFINITE MONEY GLITCH  •  UGC':fontcolor=white:fontsize=52:x=(w-text_w)/2:y=62:box=1:boxcolor=black@0.60:boxborderw=19,"
        "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='AI-GENERATED CREATOR  •  ILLUSTRATIVE EARNINGS  •  RESULTS VARY':fontcolor=white@0.92:fontsize=21:x=(w-text_w)/2:y=h-62:box=1:boxcolor=black@0.62:boxborderw=10"
    )
    af = "[1:a]volume=1.0[voice];[2:a]volume=0.15[bed];[voice][bed]amix=inputs=2:duration=first:dropout_transition=2,loudnorm=I=-14:TP=-1:LRA=8[a]"
    run([
        "ffmpeg", "-y", "-i", str(visuals), "-i", str(voice), "-i", str(bed),
        "-filter_complex", af, "-vf", vf, "-map", "0:v:0", "-map", "[a]", "-t", f"{total:.3f}",
        "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(output),
    ])
    thumb = OUT_DIR / "thumbnail-v3.jpg"
    run(["ffmpeg", "-y", "-ss", "2.5", "-i", str(output), "-frames:v", "1", "-q:v", "2", str(thumb)])
    (OUT_DIR / "transcript-v3.txt").write_text(DISPLAY_SCRIPT, encoding="utf-8")
    report = {
        "title": "Infinite money glitch (UGC)",
        "duration_seconds": round(duration(output), 3),
        "resolution": "1080x1920",
        "voice_engine": "Kokoro ONNX",
        "talking_head_engine": os.getenv("TALKING_HEAD_SPACE", "Beer1819/LipSyncerFull"),
        "person": "original AI-generated creator",
        "robotic_fallback": False,
        "still_image_mouth_warp": False,
        "assets": list(DRIVE_ASSETS),
    }
    (OUT_DIR / "report-v3.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
