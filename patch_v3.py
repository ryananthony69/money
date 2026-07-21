from pathlib import Path

path = Path("render_v3.py")
source = path.read_text(encoding="utf-8")

# Kokoro emits 24 kHz audio before the final resample, so keep the low-pass
# below Nyquist to avoid FFmpeg rejecting the filter chain.
source = source.replace("lowpass=f=15000", "lowpass=f=11000")

start = source.index("def endpoint_name(client)")
end = source.index("\n\ndef ass_time", start)
replacement = '''def generate_talking_head(image: Path, voice: Path) -> Path:
    from gradio_client import Client

    space = os.getenv("TALKING_HEAD_SPACE", "Beer1819/LipSyncerFull")
    client = Client(space, verbose=True)
    voice_duration = max(1, int(duration(voice)))

    # This legacy Gradio 3.x Space uses the WebSocket queue protocol and
    # expects ordinary local file paths. Generation is fn_index=2; the first
    # two functions only toggle UI controls.
    result = client.predict(
        str(image),
        str(voice),
        "crop",
        False,
        False,
        1,
        256,
        2,
        "facevid2vid",
        1.15,
        False,
        None,
        "pose",
        False,
        voice_duration,
        True,
        fn_index=2,
    )

    candidate = result[0] if isinstance(result, (tuple, list)) else result
    if isinstance(candidate, dict):
        candidate = (
            candidate.get("video")
            or candidate.get("path")
            or candidate.get("name")
            or candidate.get("value")
        )
    if isinstance(candidate, dict):
        candidate = candidate.get("path") or candidate.get("name")

    output_path = Path(str(candidate))
    if not output_path.exists():
        raise RuntimeError(f"Talking-head model returned no local video: {result}")

    output = WORK_DIR / "talking-head.mp4"
    shutil.copy2(output_path, output)
    generated_duration = duration(output)
    if output.stat().st_size < 100_000 or generated_duration < duration(voice) * 0.85:
        raise RuntimeError(
            f"Talking-head output was invalid: size={output.stat().st_size}, "
            f"duration={generated_duration:.3f}"
        )
    return output
'''

source = source[:start] + replacement + source[end:]
path.write_text(source, encoding="utf-8")
compile(source, str(path), "exec")
print("Applied V3 legacy WebSocket client and audio-filter fixes")
