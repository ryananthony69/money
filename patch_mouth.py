from pathlib import Path

path = Path("render.py")
source = path.read_text(encoding="utf-8")
start = source.index("def make_static_motion(")
end = source.index("\n\ndef make_app_clip", start)
replacement = '''def make_static_motion(source: Path, output: Path, duration: float, *, creator: bool) -> None:
    if creator:
        filter_complex = (
            "[0:v]fps=30,scale=1080:1920,split=2[base][m];"
            "[m]crop=380:220:350:910,"
            "scale=380:'170+35*abs(sin(n*0.42))':eval=frame[mouth];"
            "[base][mouth]overlay=350:'910+(220-h)/2':shortest=1,"
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
path.write_text(source[:start] + replacement + source[end:], encoding="utf-8")
compile(path.read_text(encoding="utf-8"), str(path), "exec")
print("Applied animated-mouth creator patch")
