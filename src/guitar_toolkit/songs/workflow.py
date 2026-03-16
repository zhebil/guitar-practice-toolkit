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
        """Download tabs from Songsterr, sync with YouTube audio, output single GP file."""
        from guitar_toolkit.tabs.download import search_songsterr
        from guitar_toolkit.tabs.gen_gp import fetch_all_tracks, generate_gp, fetch_song_meta
        from guitar_toolkit.tabs.sync import (
            fetch_video_points, select_video_entry, sync_gp_file,
            download_youtube_audio, print_summary,
        )

        query = f"{self.artist} {self.song_name}" if self.artist else self.song_name
        log(f"Searching tabs: {query}")

        try:
            results = search_songsterr(query)
            if not results:
                log("No tabs found")
                return None

            best = results[0]
            song_id = best["id"]
            log(f"Found: {best['artist']} - {best['title']} ({len(best['tracks'])} tracks)")

            # Generate GP file from Songsterr track data
            meta, tracks = fetch_all_tracks(song_id)
            self.results["tab_meta"] = meta

            filename = f"{best['artist']} - {best['title']}".replace("/", "-")
            output_dir = Path("tabs")
            output_dir.mkdir(parents=True, exist_ok=True)
            raw_gp = output_dir / f".tmp_{filename}.gp"
            generate_gp(tracks, raw_gp, meta)

            # Sync with YouTube audio
            revision_id = meta["revisionId"]
            log("Fetching video sync points...")
            entries = fetch_video_points(song_id, revision_id)

            final_path = output_dir / f"{filename}.gp"

            if entries:
                entry = select_video_entry(entries)
                points = entry["points"]
                video_id = entry["videoId"]

                audio_path = output_dir / ".tmp_sync_audio.mp3"
                trim_start = points[0] if points else 0.0
                log("Downloading YouTube audio for sync...")
                download_youtube_audio(video_id, audio_path, trim_start=trim_start)

                bpms = sync_gp_file(raw_gp, points, final_path, mp3_path=audio_path)

                audio_path.unlink(missing_ok=True)
                raw_gp.unlink(missing_ok=True)

                log(f"Tabs (synced): {final_path}")
                print_summary(bpms, points)
            else:
                log("No video sync points — saving tabs without audio")
                raw_gp.rename(final_path)

            # Extract track info from meta
            gp_tracks = []
            for t in meta.get("tracks", []):
                gp_tracks.append({
                    "name": t.get("name", ""),
                    "instrument": t.get("instrument", ""),
                    "tuning": t.get("tuning", []),
                })
            self.results["gp_info"] = {
                "title": meta.get("title", ""),
                "artist": meta.get("artist", ""),
                "tracks": gp_tracks,
            }

            self.results["tabs"] = final_path
            return final_path
        except Exception as e:
            log(f"Tabs error: {e}")
            # Clean up temp files
            for tmp in Path("tabs").glob(".tmp_*"):
                tmp.unlink(missing_ok=True)
            return None

    def run(self) -> dict:
        """Run all workflow steps."""
        self.step_download()
        self.step_separate()
        self.step_bpm()
        self.step_tabs()
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
        if self.results.get("tabs"):
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
