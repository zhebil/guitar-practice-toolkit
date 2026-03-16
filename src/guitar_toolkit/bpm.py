#!/usr/bin/env python3
"""Tempo detection and per-segment BPM analysis using librosa."""

import argparse
from pathlib import Path

import librosa
import numpy as np


def detect_tempo(audio_path: Path) -> float:
    """Detect overall BPM of an audio file."""
    y, sr = librosa.load(str(audio_path), sr=None)
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    return float(np.asarray(tempo).flat[0])


def detect_beats(audio_path: Path) -> tuple[float, np.ndarray]:
    """Detect tempo and beat positions.

    Returns (bpm, beat_times_in_seconds).
    """
    y, sr = librosa.load(str(audio_path), sr=None)
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    return float(np.asarray(tempo).flat[0]), beat_times


def analyze_segments(
    audio_path: Path,
    tolerance: float = 5.0,
    min_segment_sec: float = 3.0,
) -> list[dict]:
    """Analyze per-segment BPM from inter-beat intervals.

    Groups consecutive beats with similar BPM into segments,
    merges short segments into neighbors.

    Returns list of dicts with keys: start, end, bpm.
    Times are in seconds.
    """
    _, beat_times = detect_beats(audio_path)

    if len(beat_times) < 3:
        tempo = detect_tempo(audio_path)
        return [{"start": 0.0, "end": float(beat_times[-1]) if len(beat_times) else 0.0, "bpm": tempo}]

    ibis = np.diff(beat_times)
    local_bpms = 60.0 / ibis

    # Group into segments where BPM is stable within tolerance
    segments = []
    seg_start = beat_times[0]
    seg_bpms = [local_bpms[0]]

    for i in range(1, len(local_bpms)):
        median = np.median(seg_bpms)
        if abs(local_bpms[i] - median) < tolerance:
            seg_bpms.append(local_bpms[i])
        else:
            segments.append({
                "start": float(seg_start),
                "end": float(beat_times[i]),
                "bpm": float(np.median(seg_bpms)),
            })
            seg_start = beat_times[i]
            seg_bpms = [local_bpms[i]]

    segments.append({
        "start": float(seg_start),
        "end": float(beat_times[-1]),
        "bpm": float(np.median(seg_bpms)),
    })

    # Merge short segments and adjacent segments with similar BPM
    merged = []
    for seg in segments:
        duration = seg["end"] - seg["start"]
        if merged and duration < min_segment_sec:
            merged[-1]["end"] = seg["end"]
        elif merged and abs(seg["bpm"] - merged[-1]["bpm"]) < tolerance:
            merged[-1]["end"] = seg["end"]
            merged[-1]["bpm"] = (merged[-1]["bpm"] + seg["bpm"]) / 2
        else:
            merged.append(seg)

    return merged


def format_time(seconds: float) -> str:
    """Format seconds as M:SS."""
    m = int(seconds) // 60
    s = int(seconds) % 60
    return f"{m}:{s:02d}"


def main():
    parser = argparse.ArgumentParser(description="Detect BPM of audio files")
    parser.add_argument("input", type=Path, help="Audio file to analyze")
    parser.add_argument("--segments", action="store_true", help="Show per-segment BPM analysis")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"File not found: {args.input}")
        return

    duration = librosa.get_duration(path=str(args.input))
    tempo = detect_tempo(args.input)
    print(f"File:     {args.input.name}")
    print(f"Duration: {format_time(duration)}")
    print(f"BPM:      {tempo:.1f}")

    if args.segments:
        segments = analyze_segments(args.input)
        print(f"\n{'Start':>7s}  {'End':>7s}  {'Length':>7s}  {'BPM':>6s}")
        print("-" * 34)
        for seg in segments:
            start = format_time(seg["start"])
            end = format_time(seg["end"])
            length = format_time(seg["end"] - seg["start"])
            print(f"{start:>7s}  {end:>7s}  {length:>7s}  {seg['bpm']:5.1f}")


if __name__ == "__main__":
    main()
