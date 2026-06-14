# YouTube → Rekordbox

A local web app: paste a YouTube link, it downloads the audio, converts to a
tagged 320 kbps MP3, and adds the track to your rekordbox 6 library (into a
**"YouTube Imports"** playlist).

## Requirements
- Python 3.10+ and `ffmpeg` on your PATH (both already present on this machine)
- rekordbox 6

## Setup (one time)
```
pip install -r requirements.txt
```

## Run
Double-click **`run.bat`**, or:
```
cd backend
python -m uvicorn main:app --port 8000
```
Then open http://127.0.0.1:8000

## How to use
1. **Close rekordbox completely.** Writing to the library while rekordbox is
   open can corrupt it, so the app refuses to add until it's closed. The status
   pill in the top-right shows whether it's safe.
2. Paste a YouTube link → **Fetch**. Edit the auto-filled Title / Artist if you like.
3. **Add to Rekordbox.** Watch the progress (download → convert → tag → add).
4. Open rekordbox — the track is in your collection and in the
   **YouTube Imports** playlist.

## Safety
- Before the first DB write each session, `master.db` is backed up to
  `~/rekordbox/db_backups/master_<timestamp>.db`.
- MP3s are stored permanently in `~/Music/PioneerDJ/YouTube/` (rekordbox
  references files by their path — don't move or delete them).

## Notes
- Only download content you're legally entitled to use.
- Duplicate paths are detected, so re-adding the same link won't create copies.
