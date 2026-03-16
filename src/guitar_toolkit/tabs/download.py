#!/usr/bin/env python3
"""Search and download guitar tabs from Songsterr as Guitar Pro files."""

import argparse
import json
import urllib.request
import urllib.parse
from pathlib import Path


SONGSTERR_API = "https://songsterr.com/api/songs"


def search_songsterr(query: str) -> list[dict]:
    """Search Songsterr for tabs.

    Returns list of dicts with keys: id, artist, title, tracks, url.
    """
    params = urllib.parse.urlencode({"pattern": query})
    url = f"{SONGSTERR_API}?{params}"

    req = urllib.request.Request(url, headers={
        "Accept": "application/json",
        "User-Agent": "guitar-toolkit/0.1",
    })
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())

    results = []
    for song in data:
        song_id = song.get("songId")
        artist = song.get("artist", "Unknown")
        title = song.get("title", "Unknown")

        slug = f"{artist}-{title}".lower().replace(" ", "-").replace("&", "and")
        page_url = f"https://www.songsterr.com/a/wsa/{slug}-tab-s{song_id}"

        track_names = []
        for t in song.get("tracks", []):
            name = t.get("name", t.get("instrument", ""))
            if name:
                track_names.append(name)

        results.append({
            "id": song_id,
            "artist": artist,
            "title": title,
            "tracks": track_names,
            "url": page_url,
            "is_junk": song.get("isJunk", False),
        })

    return [r for r in results if not r["is_junk"]]


def download_tab(song_id: int, output_dir: Path = Path("tabs"), filename: str | None = None) -> Path:
    """Download a Guitar Pro tab from Songsterr by song ID.

    Fetches track data from the Songsterr CDN and converts to GP7/8 format
    using the GPIF builder.
    """
    from guitar_toolkit.tabs.gen_gp import fetch_all_tracks, generate_gp

    output_dir.mkdir(parents=True, exist_ok=True)

    meta, tracks = fetch_all_tracks(song_id)

    if not filename:
        safe = f"{meta['artist']} - {meta['title']}".replace("/", "-")
        filename = safe

    output_path = output_dir / f"{filename}.gp"
    generate_gp(tracks, output_path, meta)
    return output_path


def search_and_download(
    query: str,
    output_dir: Path = Path("tabs"),
    filename: str | None = None,
) -> Path:
    """Search Songsterr and download the best matching tab as a GP file."""
    results = search_songsterr(query)
    if not results:
        raise RuntimeError(f"No tabs found for: {query}")

    print(f"Found {len(results)} results:")
    for i, r in enumerate(results[:5]):
        print(f"  {i+1}. {r['artist']} - {r['title']} (ID: {r['id']})")
        if r["tracks"]:
            print(f"     Tracks: {', '.join(r['tracks'][:4])}")

    best = results[0]
    print(f"\nDownloading: {best['artist']} - {best['title']}")

    if not filename:
        filename = f"{best['artist']} - {best['title']}".replace("/", "-")

    return download_tab(best["id"], output_dir, filename)


def main():
    parser = argparse.ArgumentParser(description="Download guitar tabs from Songsterr as Guitar Pro files")
    parser.add_argument("query", nargs="?", help="Search query (e.g. 'Arctic Monkeys R U Mine')")
    parser.add_argument("--output", type=Path, default=Path("tabs"), help="Output directory")
    parser.add_argument("--name", help="Custom filename (without extension)")
    parser.add_argument("--id", type=int, help="Download by Songsterr song ID directly")
    args = parser.parse_args()

    if args.id:
        path = download_tab(args.id, args.output, args.name)
    elif args.query:
        path = search_and_download(args.query, args.output, args.name)
    else:
        parser.error("Provide a search query or --id")

    print(f"Saved: {path}")


if __name__ == "__main__":
    main()
