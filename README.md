# Guitar Practice Toolkit

Remove guitar from songs, download Guitar Pro tabs from Songsterr (synced with audio), and detect BPM.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Requires: `brew install ffmpeg yt-dlp`

## Usage

### Full workflow

Prepare everything for practice in one command:

```bash
python -m guitar_toolkit.songs.workflow "Enter Sandman" --artist "Metallica" --url "https://youtube.com/..."
```

This will:
1. Download the song from YouTube
2. Remove guitar via Demucs AI stem separation
3. Detect BPM with segment analysis
4. Download Guitar Pro tabs from Songsterr (with palm muting, dead notes, harmonics, etc.)
5. Sync tabs with YouTube audio — embedded MP3 with per-measure SyncPoints

### Individual tools

```bash
# Remove guitar
python -m guitar_toolkit.demucs_mix "song.mp3"

# Detect BPM
python -m guitar_toolkit.bpm "song.mp3" --segments

# Download song
python -m guitar_toolkit.songs.download "YouTube URL"

# Download tabs
python -m guitar_toolkit.tabs.download "Metallica Enter Sandman"

# Sync tabs with audio
python -m guitar_toolkit.tabs.sync --song 19 --gp-file tabs/file.gp
```
