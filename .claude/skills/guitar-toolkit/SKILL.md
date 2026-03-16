---
name: guitar-toolkit
description: Guitar practice toolkit. Use when the user asks to prepare a song for practice, remove instruments, analyze BPM, download songs or tabs, sync tabs with audio, or run the full practice workflow.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Guitar Practice Toolkit

## Setup

```bash
cd /Users/zhebil/work/guitar-remover && source venv/bin/activate && export PYTHONPATH=src:$PYTHONPATH
```

## Commands

### Full workflow (download + remove guitar + BPM + tabs + sync)

```bash
python -m guitar_toolkit.songs.workflow "Song Name" --artist "Artist" --url "youtube-url"
python -m guitar_toolkit.songs.workflow "Song Name" --artist "Artist"  # searches YouTube
python -m guitar_toolkit.songs.workflow "Song Name" --audio existing.mp3  # skip download
```

Output: backing track in `outputs/`, synced GP file in `tabs/`

### Remove guitar from a song

```bash
python -m guitar_toolkit.demucs_mix "song.mp3" [--mute guitar piano] [--force]
```

### Analyze BPM

```bash
python -m guitar_toolkit.bpm "song.mp3" --segments
```

### Download song from YouTube

```bash
python -m guitar_toolkit.songs.download "URL"
python -m guitar_toolkit.songs.download "search query" --search
```

### Download Guitar Pro tabs from Songsterr

```bash
python -m guitar_toolkit.tabs.download "Artist Song Name"
python -m guitar_toolkit.tabs.download --id 12345
```

### Sync GP tabs with YouTube audio

```bash
python -m guitar_toolkit.tabs.sync --song 12345 --gp-file tabs/file.gp
python -m guitar_toolkit.tabs.sync --song 12345 --list-videos
```

## Routing

- "prepare [song] for practice" / "set up [song]" -> full workflow
- "remove guitar from" / "make backing track" -> demucs_mix
- "what BPM" / "analyze tempo" / "detect bpm" -> bpm
- "download [song]" -> songs.download
- "find tabs for" / "get tabs" / "download tabs" -> tabs.download
- "sync tabs" / "sync with audio" -> tabs.sync
