from pathlib import Path

path = Path("render_local.py")
source = path.read_text(encoding="utf-8")
source = source.replace("lowpass=f=15000", "lowpass=f=11000")

start = source.index("def endpoint_name(client)")
end = source.index("\n\ndef ass_time", start)
replacement = '''def generate_talking_head(image: Path, voice: Path) -> Path:
    repo = ROOT / "third_party" / "Wav2Lip"
    inference = repo / "inference.py"
    checkpoint = repo / "checkpoints" / "wav2lip_gan.pth"
    detector = repo / "face_detection" / "detection" / "sfd" / "s3fd.pth"
    for required in (inference, checkpoint, detector):
        if not required.exists() or required.stat().st_size < 1024:
            raise RuntimeError(f"Local Wav2Lip dependency missing: {required}")

    output = WORK_DIR / "talking-head.mp4"
    command = [
        os.environ.get("PYTHON", "python"),
        "inference.py",
        "--checkpoint_path", str(checkpoint),
        "--face", str(image),
        "--audio", str(voice),
        "--outfile", str(output),
        "--pads", "0", "20", "0", "0",
        "--resize_factor", "1",
        "--wav2lip_batch_size", "64",
        "--nosmooth",
    ]
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=repo, text=True, check=True)

    generated_duration = duration(output)
    if output.stat().st_size < 100_000 or generated_duration < duration(voice) * 0.85:
        raise RuntimeError(
            f"Local Wav2Lip output invalid: size={output.stat().st_size}, "
            f"duration={generated_duration:.3f}"
        )
    return output
'''

source = source[:start] + replacement + source[end:]
source = source.replace(
    '"talking_head_engine": os.getenv("TALKING_HEAD_SPACE", "Beer1819/LipSyncerFull"),',
    '"talking_head_engine": "Local Wav2Lip GAN",',
)
path.write_text(source, encoding="utf-8")
compile(source, str(path), "exec")
print("Applied deterministic local Wav2Lip renderer patch")
