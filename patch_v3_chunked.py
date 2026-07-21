from pathlib import Path

path = Path("render_v3.py")
source = path.read_text(encoding="utf-8")
source = source.replace("lowpass=f=15000", "lowpass=f=11000")

start = source.index("def endpoint_name(client)")
end = source.index("\n\ndef ass_time", start)
replacement = '''def generate_talking_head(image: Path, voice: Path) -> Path:
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from gradio_client import Client

    spaces = [
        item.strip()
        for item in os.getenv(
            "TALKING_HEAD_SPACES",
            "Beer1819/LipSyncerFull,peterpeter8585/LipSyncer",
        ).split(",")
        if item.strip()
    ]
    if not spaces:
        raise RuntimeError("No talking-head Spaces configured")

    voice_seconds = duration(voice)
    chunk_seconds = float(os.getenv("TALKING_HEAD_CHUNK_SECONDS", "8.0"))
    chunk_dir = WORK_DIR / "talking-head-chunks"
    chunk_dir.mkdir(parents=True, exist_ok=True)
    chunks = []
    cursor = 0.0
    index = 0
    while cursor < voice_seconds - 0.05:
        length = min(chunk_seconds, voice_seconds - cursor)
        audio = chunk_dir / f"audio-{index:02d}.wav"
        run([
            "ffmpeg", "-y", "-ss", f"{cursor:.3f}", "-i", str(voice),
            "-t", f"{length:.3f}", "-ar", "48000", "-ac", "1", str(audio),
        ])
        chunks.append((index, audio, length))
        cursor += length
        index += 1

    assignments = {space: [] for space in spaces}
    for item_index, item in enumerate(chunks):
        assignments[spaces[item_index % len(spaces)]].append(item)

    results = {}
    failures = []

    def extract_path(result):
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
        return Path(str(candidate))

    def render_group(space, items):
        client = Client(space, verbose=True)
        completed = []
        for item_index, audio, length in items:
            print(f"Submitting chunk {item_index} ({length:.2f}s) to {space}", flush=True)
            result = client.predict(
                str(image), str(audio), "crop", False, False, 1, 256, 2,
                "facevid2vid", 1.15, False, None, "pose", False,
                max(1, int(round(length))), True, fn_index=2,
            )
            returned = extract_path(result)
            if not returned.exists():
                raise RuntimeError(f"{space} returned no video for chunk {item_index}: {result}")
            target = chunk_dir / f"video-{item_index:02d}.mp4"
            shutil.copy2(returned, target)
            if target.stat().st_size < 50_000:
                raise RuntimeError(f"{space} returned an undersized video for chunk {item_index}")
            completed.append((item_index, target))
        return completed

    with ThreadPoolExecutor(max_workers=len(spaces)) as executor:
        future_map = {
            executor.submit(render_group, space, items): space
            for space, items in assignments.items()
            if items
        }
        for future in as_completed(future_map):
            space = future_map[future]
            try:
                for item_index, target in future.result():
                    results[item_index] = target
            except Exception as exc:
                print(f"Host {space} failed: {exc}", flush=True)
                for item in assignments[space]:
                    if item[0] not in results:
                        failures.append(item)

    # Retry missing chunks one-by-one across all hosts before failing.
    for item_index, audio, length in failures:
        if item_index in results:
            continue
        last_error = None
        for space in reversed(spaces):
            try:
                completed = render_group(space, [(item_index, audio, length)])
                results[item_index] = completed[0][1]
                break
            except Exception as exc:
                last_error = exc
                print(f"Retry of chunk {item_index} on {space} failed: {exc}", flush=True)
        if item_index not in results:
            raise RuntimeError(f"All hosts failed chunk {item_index}: {last_error}")

    ordered = [results[i] for i in range(len(chunks))]
    concat = chunk_dir / "concat.txt"
    concat.write_text("".join(f"file '{item.as_posix()}'\\n" for item in ordered), encoding="utf-8")
    joined = chunk_dir / "joined.mp4"
    run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat),
        "-an", "-vf", "fps=25,format=yuv420p", "-c:v", "libx264",
        "-preset", "veryfast", "-crf", "18", str(joined),
    ])

    output = WORK_DIR / "talking-head.mp4"
    run([
        "ffmpeg", "-y", "-stream_loop", "-1", "-i", str(joined),
        "-t", f"{voice_seconds + 0.5:.3f}", "-an", "-c:v", "libx264",
        "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", str(output),
    ])
    if output.stat().st_size < 100_000 or duration(output) < voice_seconds:
        raise RuntimeError("Chunked talking-head assembly was invalid")

    os.environ["TALKING_HEAD_SPACE"] = "Chunked LipSyncer SadTalker"
    return output
'''

source = source[:start] + replacement + source[end:]
path.write_text(source, encoding="utf-8")
compile(source, str(path), "exec")
print("Applied parallel chunked SadTalker inference patch")
