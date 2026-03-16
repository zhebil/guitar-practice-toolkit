#!/usr/bin/env python3
"""Full practice workflow: download -> separate -> BPM -> tabs."""

import argparse
from pathlib import Path


def log(msg: str):
    print(f"[workflow] {msg}")


class SongWorkflow:
    """Orchestrate the complete song preparation workflow."""

    def __init__(
        self,
        song_name: str,
        artist: str | None = None,
        url: str | None = None,
        audio_path: Path | None = None,
        mute: list[str] | None = None,
    ):
        self.song_name = song_name
        self.artist = artist
        self.url = url
        self.audio_path = audio_path
        self.mute = mute or ["guitar"]
        self.results: dict = {}

    def step_download(self) -> Path:
        """Download song from YouTube."""
        from guitar_toolkit.songs.download import download_song, search_and_download

        if self.audio_path and self.audio_path.exists():
            log(f"Using existing audio: {self.audio_path}")
            self.results["audio"] = self.audio_path
            return self.audio_path

        safe_name = f"{self.artist} - {self.song_name}" if self.artist else self.song_name
        safe_name = safe_name.replace("/", "-")

        if self.url:
            log("Downloading from URL...")
            path = download_song(self.url, filename=safe_name)
        else:
            query = f"{self.artist} {self.song_name}" if self.artist else self.song_name
            log(f"Searching YouTube: {query}")
            path = search_and_download(query, filename=safe_name)

        log(f"Audio: {path}")
        self.results["audio"] = path
        self.audio_path = path
        return path

    def step_separate(self) -> Path:
        """Run demucs to create backing track."""
        from guitar_toolkit.demucs_mix import process_file

        if not self.audio_path:
            raise RuntimeError("No audio file — run step_download first")

        log(f"Separating stems (muting: {', '.join(self.mute)})...")
        mp3_path = process_file(
            input_path=self.audio_path,
            model="htdemucs_6s",
            muted=set(self.mute),
            out_dir=Path("outputs"),
            force=False,
        )
        self.results["backing"] = mp3_path
        return mp3_path

    def step_bpm(self) -> dict:
        """Detect BPM with segment analysis."""
        from guitar_toolkit.bpm import detect_tempo, analyze_segments

        if not self.audio_path:
            raise RuntimeError("No audio file — run step_download first")

        log("Analyzing BPM...")
        tempo = detect_tempo(self.audio_path)
        segments = analyze_segments(self.audio_path)

        bpm_info = {
            "tempo": tempo,
            "segments": segments,
            "stable": len(segments) <= 2 and all(
                abs(s["bpm"] - tempo) < 5 for s in segments
            ),
        }
        self.results["bpm"] = bpm_info
        log(f"BPM: {tempo:.0f}" + (" (stable)" if bpm_info["stable"] else f" ({len(segments)} segments)"))
        return bpm_info

    def step_tabs(self) -> Path | None:
        """Search and download tabs from Songsterr as a GP7/8 file."""
        from guitar_toolkit.tabs.download import search_songsterr
        from guitar_toolkit.tabs.gen_gp import fetch_all_tracks, generate_gp

        query = f"{self.artist} {self.song_name}" if self.artist else self.song_name
        log(f"Searching tabs: {query}")

        try:
            results = search_songsterr(query)
            if not results:
                log("No tabs found")
                self.results["tabs"] = None
                return None

            best = results[0]
            log(f"Found: {best['artist']} - {best['title']} ({len(best['tracks'])} tracks)")

            meta, tracks = fetch_all_tracks(best["id"])
            self.results["tab_meta"] = meta

            filename = f"{best['artist']} - {best['title']}".replace("/", "-")
            output_dir = Path("tabs")
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f"{filename}.gp"
            generate_gp(tracks, output_path, meta)

            self.results["tabs"] = output_path
            self.results["songsterr_id"] = best["id"]
            log(f"Tabs: {output_path}")
            return output_path
        except Exception as e:
            log(f"Tabs error: {e}")
            self.results["tabs"] = None
            return None

    def step_gp_info(self) -> dict | None:
        """Extract GP metadata from Songsterr API or PyGuitarPro."""
        tabs_path = self.results.get("tabs")
        if not tabs_path or not Path(tabs_path).exists():
            return None

        suffix = Path(tabs_path).suffix.lower()

        if suffix in (".gp3", ".gp4", ".gp5"):
            try:
                from guitar_toolkit.tabs.gp_parser import parse_gp_file
                info = parse_gp_file(tabs_path)
                self.results["gp_info"] = info
                return info
            except Exception as e:
                log(f"Could not parse GP file: {e}")
                return None

        tab_meta = self.results.get("tab_meta")
        if tab_meta:
            tracks = []
            for t in tab_meta.get("tracks", []):
                tracks.append({
                    "name": t.get("name", ""),
                    "instrument": t.get("instrument", ""),
                    "tuning": t.get("tuning", []),
                })
            info = {
                "title": tab_meta.get("title", ""),
                "artist": tab_meta.get("artist", ""),
                "tracks": tracks,
                "measure_count": 0,
            }
            self.results["gp_info"] = info
            return info

        return None

    def step_sync(self) -> Path | None:
        """Sync GP tabs with YouTube audio using Songsterr video points."""
        from guitar_toolkit.tabs.sync import (
            fetch_video_points, select_video_entry, sync_gp_file,
            download_youtube_audio, print_summary,
        )
        from guitar_toolkit.tabs.gen_gp import fetch_song_meta

        tabs_path = self.results.get("tabs")
        song_id = self.results.get("songsterr_id")
        if not tabs_path or not song_id:
            return None

        tabs_path = Path(tabs_path)
        if not tabs_path.exists():
            return None

        try:
            meta = fetch_song_meta(song_id)
            revision_id = meta["revisionId"]

            log("Fetching video sync points...")
            entries = fetch_video_points(song_id, revision_id)
            if not entries:
                log("No video sync points available")
                return None

            entry = select_video_entry(entries)
            points = entry["points"]
            video_id = entry["videoId"]

            # Download YouTube audio trimmed to measure 1
            audio_path = tabs_path.parent / ".tmp_sync_audio.mp3"
            trim_start = points[0] if points else 0.0
            log("Downloading YouTube audio for sync...")
            download_youtube_audio(video_id, audio_path, trim_start=trim_start)

            # Create synced GP file
            synced_path = tabs_path.with_name(tabs_path.stem + "_synced.gp")
            bpms = sync_gp_file(tabs_path, points, synced_path, mp3_path=audio_path)

            # Clean up temp audio
            if audio_path.exists():
                audio_path.unlink()

            self.results["synced_tabs"] = synced_path
            log(f"Synced tabs: {synced_path}")
            print_summary(bpms, points)
            return synced_path
        except Exception as e:
            log(f"Sync error: {e}")
            return None

    def run(self) -> dict:
        """Run all workflow steps."""
        self.step_download()
        self.step_separate()
        self.step_bpm()
        self.step_tabs()
        self.step_gp_info()
        self.step_sync()
        return self.results

    def summary(self) -> str:
        """Print summary of everything produced."""
        title = f"{self.song_name}"
        if self.artist:
            title += f" — {self.artist}"

        lines = [
            f"Song: {title}",
            "-" * (len(title) + 6),
        ]

        if "audio" in self.results:
            lines.append(f"Audio:   {self.results['audio']}")
        if "backing" in self.results:
            lines.append(f"Backing: {self.results['backing']}")
        if "bpm" in self.results:
            bpm = self.results["bpm"]
            status = "stable" if bpm.get("stable") else f"{len(bpm.get('segments', []))} segments"
            lines.append(f"BPM:     {bpm['tempo']:.0f} ({status})")
        if self.results.get("synced_tabs"):
            lines.append(f"Tabs:    {self.results['synced_tabs']} (synced with audio)")
        elif self.results.get("tabs"):
            lines.append(f"Tabs:    {self.results['tabs']}")
        if self.results.get("gp_info"):
            info = self.results["gp_info"]
            if info.get("tracks"):
                tunings = [t["name"] for t in info["tracks"][:3]]
                lines.append(f"Tracks:  {', '.join(tunings)}")

        lines.append("-" * (len(title) + 6))
        lines.append("Ready to practice!")
        return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Prepare a song for guitar practice")
    parser.add_argument("song", help="Song name")
    parser.add_argument("--artist", help="Artist name")
    parser.add_argument("--url", help="YouTube URL (searches if not provided)")
    parser.add_argument("--audio", type=Path, help="Use existing audio file instead of downloading")
    parser.add_argument("--mute", nargs="+", default=["guitar"], help="Instruments to remove")
    args = parser.parse_args()

    workflow = SongWorkflow(
        song_name=args.song,
        artist=args.artist,
        url=args.url,
        audio_path=args.audio,
        mute=args.mute,
    )

    workflow.run()
    print()
    print(workflow.summary())


if __name__ == "__main__":
    main()
