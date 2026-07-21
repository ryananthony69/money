from pathlib import Path

path = Path("render.py")
source = path.read_text(encoding="utf-8")

start = source.index("def make_static_motion(")
end = source.index("\n\ndef make_app_clip", start)
motion_replacement = '''def make_static_motion(source: Path, output: Path, duration: float, *, creator: bool) -> None:
    if creator:
        filter_complex = (
            "[0:v]fps=30,scale=1080:1920,split=2[base][m];"
            "[m]crop=240:105:420:1040,"
            "scale=240:'75+22*abs(sin(n*0.42))':eval=frame[mouth];"
            "[base][mouth]overlay=420:'1040+(105-h)/2':shortest=1,"
            "scale=1120:1992,"
            "crop=1080:1920:'20+5*sin(n/13)':'36+5*cos(n/15)',"
            "eq=contrast=1.035:saturation=1.04,format=yuv420p[v]"
        )
        run([
            "ffmpeg", "-y", "-loop", "1", "-i", str(source),
            "-t", f"{duration:.3f}", "-filter_complex", filter_complex,
            "-map", "[v]", "-an", "-r", "30", "-c:v", "libx264",
            "-preset", "veryfast", "-crf", "18", str(output),
        ])
        return

    vf = (
        "scale=1200:2134:force_original_aspect_ratio=increase,crop=1200:2134,"
        "zoompan=z='min(zoom+0.00045,1.045)':"
        "x='iw/2-(iw/zoom/2)+8*sin(on/17)':"
        "y='ih/2-(ih/zoom/2)+7*cos(on/19)':d=1:s=1080x1920:fps=30,"
        "eq=contrast=1.035:saturation=1.04,format=yuv420p"
    )
    run([
        "ffmpeg", "-y", "-loop", "1", "-i", str(source), "-t", f"{duration:.3f}",
        "-vf", vf, "-an", "-r", "30", "-c:v", "libx264", "-preset", "veryfast",
        "-crf", "18", str(output),
    ])
'''
source = source[:start] + motion_replacement + source[end:]

music_start = source.index("def create_music(")
music_end = source.index("\n\ndef main", music_start)
music_replacement = '''def create_music(duration: float) -> Path:
    music = WORK_DIR / "music.m4a"
    fade_out = max(0, duration - 2)
    audio_filter = (
        "[0:a]volume=0.060[a0];"
        "[1:a]volume=0.028[a1];"
        "[a0][a1]amix=inputs=2:duration=longest,"
        "highpass=f=38,lowpass=f=2400,"
        "afade=t=in:st=0:d=1.0:curve=tri,"
        f"afade=t=out:st={fade_out:.3f}:d=2:curve=tri,"
        "volume=0.34[m]"
    )
    run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"sine=frequency=55:sample_rate=48000:duration={duration:.3f}",
        "-f", "lavfi", "-i", f"sine=frequency=110:sample_rate=48000:duration={duration:.3f}",
        "-filter_complex", audio_filter, "-map", "[m]",
        "-c:a", "aac", "-b:a", "160k", str(music),
    ])
    return music
'''
source = source[:music_start] + music_replacement + source[music_end:]

path.write_text(source, encoding="utf-8")
compile(source, str(path), "exec")
print("Applied seam-reduced animated-mouth creator and portable music patches")
