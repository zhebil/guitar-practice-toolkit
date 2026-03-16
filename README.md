# Guitar Practice Toolkit

Remove guitar from songs, download Guitar Pro tabs from Songsterr (synced with audio), and detect BPM.

## Install

### Prerequisites

```bash
# macOS
brew install python@3.14 ffmpeg yt-dlp
```

### Clone and setup

```bash
git clone git@github.com:zhebil/guitar-practice-toolkit.git
cd guitar-practice-toolkit

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

First run of Demucs will download the AI model (~50 MB).

### Verify

```bash
export PYTHONPATH=src:$PYTHONPATH
python -m guitar_toolkit.bpm --help
```

## Usage

### Full workflow

Prepare everything for practice in one command:

```bash
source venv/bin/activate
export PYTHONPATH=src:$PYTHONPATH

python -m guitar_toolkit.songs.workflow "Enter Sandman" --artist "Metallica" --url "https://youtube.com/..."
```

This will:
1. Download the song from YouTube
2. Remove guitar via Demucs AI stem separation
3. Detect BPM with segment analysis
4. Download Guitar Pro tabs from Songsterr (with palm muting, dead notes, harmonics, etc.)
5. Sync tabs with YouTube audio — embedded MP3 with per-measure SyncPoints

Output:
- `outputs/<song>_no_guitar.mp3` — backing track
- `tabs/<song>_synced.gp` — Guitar Pro file with embedded audio

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

## Project Structure

```
src/guitar_toolkit/
  audio.py            — audio loading, normalization, MP3 conversion
  bpm.py              — BPM detection with per-segment analysis
  demucs_mix.py       — Demucs stem separation + remix
  songs/
    download.py       — YouTube audio download (yt-dlp)
    workflow.py       — full workflow orchestrator
  tabs/
    download.py       — Songsterr tab search + download
    gen_gp.py         — Songsterr JSON -> Guitar Pro GPIF conversion
    sync.py           — sync GP file with YouTube audio
    gp_parser.py      — PyGuitarPro GP3-GP5 parser
    assets/           — GP7/8 template files
```
