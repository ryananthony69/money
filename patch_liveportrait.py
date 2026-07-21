from pathlib import Path

path = Path("render_v3.py")
source = path.read_text(encoding="utf-8")
source = source.replace("lowpass=f=15000", "lowpass=f=11000")

start = source.index("def endpoint_name(client)")
end = source.index("\n\ndef ass_time", start)
replacement = '''def generate_talking_head(image: Path, voice: Path) -> Path:
    from gradio_client import Client, handle_file

    space = os.getenv("TALKING_HEAD_SPACE", "KlingTeam/LivePortrait")
    driving = ASSET_DIR / "liveportrait-driving.mp4"
    if not driving.exists() or driving.stat().st_size < 100_000:
        raise RuntimeError("LivePortrait driving video is missing")

    client = Client(space, verbose=True)
    api_name = None
    fn_index = None
    try:
        data = client.view_api(return_format="dict")
        named = data.get("named_endpoints", {}) if isinstance(data, dict) else {}
        for name, spec in named.items():
            text = json.dumps(spec).lower()
            if (
                "driving video" in text
                or "relative motion" in text
                or "paste-back" in text
                or ("video" in text and "source portrait" in text)
            ):
                api_name = name
                break
        if api_name is None and named:
            # Prefer an endpoint exposing five inputs and two video outputs.
            for name, spec in named.items():
                params = spec.get("parameters", []) if isinstance(spec, dict) else []
                returns = spec.get("returns", []) if isinstance(spec, dict) else []
                if len(params) == 5 and len(returns) >= 2:
                    api_name = name
                    break
    except Exception as exc:
        print(f"LivePortrait API inspection warning: {exc}", flush=True)

    args = [
        handle_file(str(image)),
        handle_file(str(driving)),
        True,
        True,
        True,
    ]
    errors = []
    attempts = []
    if api_name:
        attempts.append(("api", api_name))
    attempts.extend([
        ("api", "/gpu_wrapped_execute_video"),
        ("api", "/execute_video"),
        ("fn", 0),
    ])

    result = None
    for mode, endpoint in attempts:
        try:
            print(f"Calling LivePortrait via {mode} endpoint {endpoint}", flush=True)
            if mode == "api":
                result = client.predict(*args, api_name=endpoint)
            else:
                result = client.predict(*args, fn_index=endpoint)
            break
        except Exception as exc:
            errors.append(f"{mode}:{endpoint}: {exc}")
            print(errors[-1], flush=True)
    if result is None:
        raise RuntimeError("All LivePortrait endpoints failed: " + " | ".join(errors))

    candidates = list(result) if isinstance(result, (tuple, list)) else [result]
    local_paths = []
    for candidate in candidates:
        if isinstance(candidate, dict):
            candidate = (
                candidate.get("video")
                or candidate.get("path")
                or candidate.get("name")
                or candidate.get("value")
            )
        if isinstance(candidate, dict):
            candidate = candidate.get("path") or candidate.get("name")
        if candidate:
            candidate_path = Path(str(candidate))
            if candidate_path.exists() and candidate_path.stat().st_size > 50_000:
                local_paths.append(candidate_path)
    if not local_paths:
        raise RuntimeError(f"LivePortrait returned no usable video: {result}")

    generated = max(local_paths, key=lambda item: item.stat().st_size)
    clip = WORK_DIR / "liveportrait-generated.mp4"
    shutil.copy2(generated, clip)
    clip_duration = duration(clip)
    if clip_duration < 0.5:
        raise RuntimeError("LivePortrait returned an invalid short clip")

    voice_duration = duration(voice)
    output = WORK_DIR / "talking-head.mp4"
    run([
        "ffmpeg", "-y", "-stream_loop", "-1", "-i", str(clip),
        "-t", f"{voice_duration + 0.5:.3f}", "-an",
        "-vf", "fps=30,format=yuv420p", "-c:v", "libx264",
        "-preset", "veryfast", "-crf", "18", str(output),
    ])
    if output.stat().st_size < 100_000 or duration(output) < voice_duration:
        raise RuntimeError("LivePortrait talking-head assembly was invalid")
    return output
'''

source = source[:start] + replacement + source[end:]
path.write_text(source, encoding="utf-8")
compile(source, str(path), "exec")
print("Applied LivePortrait model-driven creator patch")
