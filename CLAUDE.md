# Guitar Practice Toolkit

Remove guitar from songs, download synced Guitar Pro tabs from Songsterr, detect BPM.

## Quick Reference

```bash
source venv/bin/activate
export PYTHONPATH=src:$PYTHONPATH

# Full workflow: download + remove guitar + BPM + tabs synced with audio
python -m guitar_toolkit.songs.workflow "Song Name" --artist "Artist" --url "URL"
python -m guitar_toolkit.songs.workflow "Song Name" --artist "Artist"  # auto-searches YouTube
python -m guitar_toolkit.songs.workflow "Song Name" --audio existing.mp3  # use local file

# Individual tools
python -m guitar_toolkit.demucs_mix "song.mp3"                         # remove guitar
python -m guitar_toolkit.bpm "song.mp3" --segments                     # detect BPM
python -m guitar_toolkit.songs.download "YouTube URL"                   # download song
python -m guitar_toolkit.tabs.download "Artist Song"                    # download GP tabs
python -m guitar_toolkit.tabs.sync --song 12345 --gp-file tab.gp       # sync tabs with audio
```

## Architecture

```
src/guitar_toolkit/
  audio.py            — load_audio, normalize, to_mp3, write_and_convert
  bpm.py              — detect_tempo, detect_beats, analyze_segments (CLI)
  demucs_mix.py       — Demucs stem separation + remix (CLI)
  songs/
    download.py       — yt-dlp YouTube download wrapper (CLI)
    workflow.py       — full workflow orchestrator (CLI)
  tabs/
    download.py       — Songsterr search + GP7/8 tab download (CLI)
    gen_gp.py         — Songsterr JSON -> Guitar Pro GPIF conversion
    sync.py           — sync GP file with YouTube audio via Songsterr video points (CLI)
    gp_parser.py      — PyGuitarPro GP3-GP5 parser (CLI)
    assets/blank.gp   — GP7/8 template for file generation
    assets/drum_kit.xml — drum notation template
```

## Workflow Steps

1. **Download audio** from YouTube (yt-dlp) or use local file
2. **Separate stems** via Demucs htdemucs_6s, mix all except guitar -> backing track
3. **Detect BPM** via librosa beat tracking with per-segment analysis
4. **Download tabs** from Songsterr CDN, convert to GP7/8 format
5. **Sync tabs with audio** — embed YouTube audio into GP file with per-measure SyncPoints

## Conventions

- Output: MP3 320kbps via ffmpeg
- Demucs model: htdemucs_6s (6 stems: vocals, guitar, bass, drums, piano, other)
- Dirs: `outputs/` (backing tracks), `separated/` (stem cache), `songs/` (downloads), `tabs/` (GP files)
- Tab format: GP7/8 (.gp ZIP with GPIF XML) — supports palm mute, dead notes, harmonics, bends, slides

## External Tools

- `ffmpeg` — MP3 encoding (`brew install ffmpeg`)
- `yt-dlp` — YouTube downloading (`brew install yt-dlp`)

## Python Environment

- Python 3.14, venv at `./venv/`
- Key deps: demucs, librosa, soundfile, numpy, torch
- Optional: PyGuitarPro (GP3-GP5 parsing only)
