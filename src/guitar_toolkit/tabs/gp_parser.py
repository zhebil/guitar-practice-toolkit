#!/usr/bin/env python3
"""Parse Guitar Pro files using PyGuitarPro."""

import argparse
from pathlib import Path


def parse_gp_file(path: Path) -> dict:
    """Parse a Guitar Pro file and extract metadata.

    Supports GP3, GP4, GP5 formats via PyGuitarPro.
    GPX (GP6+) is NOT supported — export as GP5 from Guitar Pro.

    Returns dict with: title, artist, album, tempo, time_signatures,
    tracks (name, tuning, strings), measure_count.
    """
    try:
        import guitarpro
    except ImportError:
        raise ImportError("PyGuitarPro required: pip install PyGuitarPro")

    if path.suffix.lower() in (".gpx", ".gp"):
        raise ValueError(
            f"Format {path.suffix} not supported by PyGuitarPro. "
            "Export as GP5 from Guitar Pro."
        )

    song = guitarpro.parse(str(path))

    # Extract time signatures from measure headers
    time_sigs = []
    seen = set()
    for header in song.measureHeaders:
        ts = f"{header.timeSignature.numerator}/{header.timeSignature.denominator.value}"
        if ts not in seen:
            time_sigs.append({"measure": header.number, "time_sig": ts})
            seen.add(ts)

    # Extract track info
    tracks = []
    for track in song.tracks:
        tuning = [str(s) for s in track.strings]
        tracks.append({
            "name": track.name.strip(),
            "channel": track.channel.instrument,
            "strings": len(track.strings),
            "tuning": tuning,
        })

    return {
        "title": song.title or "",
        "artist": song.artist or "",
        "album": song.album or "",
        "tempo": song.tempo.value,
        "time_signatures": time_sigs,
        "tracks": tracks,
        "measure_count": len(song.measureHeaders),
    }


def print_info(path: Path):
    """Pretty-print Guitar Pro file info."""
    info = parse_gp_file(path)

    print(f"Title:    {info['title']}")
    print(f"Artist:   {info['artist']}")
    if info["album"]:
        print(f"Album:    {info['album']}")
    print(f"Tempo:    {info['tempo']} BPM")
    print(f"Measures: {info['measure_count']}")

    if info["time_signatures"]:
        ts_str = ", ".join(
            f"{ts['time_sig']} (m.{ts['measure']})" for ts in info["time_signatures"]
        )
        print(f"Time Sig: {ts_str}")

    print(f"\nTracks ({len(info['tracks'])}):")
    for t in info["tracks"]:
        print(f"  - {t['name']} ({t['strings']} strings, tuning: {', '.join(t['tuning'])})")


def main():
    parser = argparse.ArgumentParser(description="Parse Guitar Pro files")
    parser.add_argument("input", type=Path, help="Guitar Pro file (.gp3/.gp4/.gp5)")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"File not found: {args.input}")
        return

    print_info(args.input)


if __name__ == "__main__":
    main()
