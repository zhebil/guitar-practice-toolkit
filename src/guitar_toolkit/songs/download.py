#!/usr/bin/env python3
"""Download songs from YouTube using yt-dlp."""

import argparse
import subprocess
from pathlib import Path


def download_song(
    url: str,
    output_dir: Path = Path("songs"),
    filename: str | None = None,
    audio_format: str = "mp3",
    quality: int = 0,
) -> Path:
    """Download audio from a YouTube URL via yt-dlp.

    Returns path to downloaded file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    if filename:
        template = str(output_dir / f"{filename}.%(ext)s")
    else:
        template = str(output_dir / "%(title)s.%(ext)s")

    cmd = [
        "yt-dlp",
        "-x",
        "--audio-format", audio_format,
        "--audio-quality", str(quality),
        "-o", template,
        "--print", "after_move:filepath",
        url,
    ]

    result = subprocess.run(cmd, check=True, capture_output=True, text=True)

    # yt-dlp --print after_move:filepath prints the final path
    lines = result.stdout.strip().splitlines()
    if lines:
        return Path(lines[-1])

    # Fallback: glob for the file
    pattern = f"{filename}.*" if filename else "*.mp3"
    matches = sorted(output_dir.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    if matches:
        return matches[0]

    raise RuntimeError("Download completed but output file not found")


def search_and_download(
    query: str,
    output_dir: Path = Path("songs"),
    filename: str | None = None,
) -> Path:
    """Search YouTube and download the first result."""
    return download_song(
        url=f"ytsearch1:{query}",
        output_dir=output_dir,
        filename=filename,
    )


def main():
    parser = argparse.ArgumentParser(description="Download songs from YouTube")
    parser.add_argument("query", help="YouTube URL or search query")
    parser.add_argument("--search", action="store_true", help="Treat query as search term instead of URL")
    parser.add_argument("--output", type=Path, default=Path("songs"), help="Output directory")
    parser.add_argument("--name", help="Custom filename (without extension)")
    args = parser.parse_args()

    if args.search or not args.query.startswith(("http://", "https://")):
        path = search_and_download(args.query, args.output, args.name)
    else:
        path = download_song(args.query, args.output, args.name)

    print(f"Downloaded: {path}")


if __name__ == "__main__":
    main()
