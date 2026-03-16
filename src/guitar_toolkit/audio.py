#!/usr/bin/env python3
"""Shared audio loading, normalization, and MP3 conversion."""

import subprocess
from pathlib import Path

import numpy as np
import soundfile as sf


def load_audio(path: Path, always_2d: bool = True) -> tuple[np.ndarray, int]:
    """Load audio file via soundfile."""
    audio, sr = sf.read(path, always_2d=always_2d)
    return audio.astype(np.float32), sr


def normalize(audio: np.ndarray, target_peak: float = 0.98) -> np.ndarray:
    """Peak-normalize audio array."""
    peak = np.max(np.abs(audio))
    if peak == 0:
        return audio
    return audio * (target_peak / peak)


def to_mp3(wav_path: Path, mp3_path: Path, bitrate: str = "320k"):
    """Convert WAV to MP3 via ffmpeg."""
    subprocess.run(
        [
            "ffmpeg", "-i", str(wav_path),
            "-codec:a", "libmp3lame", "-b:a", bitrate,
            "-y", str(mp3_path),
        ],
        check=True,
        capture_output=True,
    )


def write_and_convert(
    audio: np.ndarray,
    sr: int,
    output_path: Path,
    bitrate: str = "320k",
) -> Path:
    """Write audio array to MP3 via temporary WAV."""
    output_path = Path(output_path)
    if output_path.suffix != ".mp3":
        output_path = output_path.with_suffix(".mp3")

    wav_path = output_path.with_suffix(".wav")
    sf.write(wav_path, audio, sr)

    to_mp3(wav_path, output_path, bitrate)
    wav_path.unlink()

    return output_path
