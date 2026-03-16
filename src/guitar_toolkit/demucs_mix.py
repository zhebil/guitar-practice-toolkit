#!/usr/bin/env python3
"""Demucs stem separation and remixing — remove instruments from songs."""

import argparse
import subprocess
from pathlib import Path

import numpy as np

from guitar_toolkit.audio import load_audio, normalize, to_mp3


def log(msg: str):
    print(f"[demucs-mix] {msg}")


def run_demucs(input_path: Path, model: str, force: bool) -> Path:
    """Run demucs to separate stems. Returns path to stem directory."""
    stem_dir = Path("separated") / model / input_path.stem

    if stem_dir.exists() and not force:
        log(f"Using cached stems: {stem_dir}")
        return stem_dir

    log(f"Running demucs ({model}) on {input_path.name}")
    subprocess.run(
        ["demucs", "-n", model, str(input_path)],
        check=True,
    )

    if not stem_dir.exists():
        raise RuntimeError("Demucs output not found")

    return stem_dir


def mix_stems(stem_dir: Path, muted: set[str]) -> tuple[np.ndarray, int]:
    """Mix stems, excluding muted instruments. Returns (audio, sample_rate)."""
    mix = None
    sr = None
    used = []

    for wav in sorted(stem_dir.glob("*.wav")):
        name = wav.stem.lower()
        if name in muted:
            log(f"Muted: {name}")
            continue

        audio, rate = load_audio(wav)
        sr = sr or rate
        mix = audio if mix is None else mix + audio
        used.append(name)

    if mix is None:
        raise RuntimeError("No stems were mixed")

    log(f"Mixed stems: {', '.join(used)}")
    return normalize(mix), sr


def process_file(
    input_path: Path,
    model: str,
    muted: set[str],
    out_dir: Path,
    force: bool,
) -> Path:
    """Full pipeline: separate -> mix -> export MP3. Returns output path."""
    stem_dir = run_demucs(input_path, model, force)
    audio, sr = mix_stems(stem_dir, muted)

    out_dir.mkdir(parents=True, exist_ok=True)
    base_name = f"{input_path.stem}_no_{'_'.join(sorted(muted))}"

    import soundfile as sf
    wav_path = out_dir / f"{base_name}.wav"
    sf.write(wav_path, audio, sr)

    mp3_path = out_dir / f"{base_name}.mp3"
    to_mp3(wav_path, mp3_path)
    log(f"Written: {mp3_path}")

    wav_path.unlink()
    log("Cleaned up temporary WAV")

    return mp3_path


def main():
    parser = argparse.ArgumentParser(
        description="Demucs stem mixer (mute instruments and remix)"
    )
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument(
        "--model", default="htdemucs_6s",
        help="Demucs model (default: htdemucs_6s)",
    )
    parser.add_argument(
        "--mute", nargs="+", default=["guitar"],
        help="Stems to exclude (e.g. guitar piano)",
    )
    parser.add_argument(
        "--out-dir", type=Path, default=Path("outputs"),
        help="Output directory",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Force re-run demucs even if stems exist",
    )

    args = parser.parse_args()
    muted = set(s.lower() for s in args.mute)

    for input_path in args.inputs:
        if not input_path.exists():
            log(f"File not found: {input_path}")
            continue

        process_file(
            input_path=input_path,
            model=args.model,
            muted=muted,
            out_dir=args.out_dir,
            force=args.force,
        )


if __name__ == "__main__":
    main()
