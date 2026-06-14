# YouTube → Rekordbox

A small local web app: paste a YouTube link, it downloads the audio, converts it
to a tagged **320 kbps MP3** (title, artist, and cover art embedded), and adds the
track to your **rekordbox 6** library — into a **"YouTube Imports"** playlist.

> ⚠️ **Only download content you're legally entitled to use.** This tool is for
> your own recordings, royalty-free tracks, and other material you have the rights to.

---

## What you need

| Requirement | Notes |
|---|---|
| **Python 3.10+** | <https://www.python.org/downloads/> — on Windows, tick *"Add Python to PATH"* during install. |
| **ffmpeg** | Used to transcode audio to MP3. Install instructions below. |
| **rekordbox 6** | Required for the "Add to library" step. The download/convert part works without it. |

### Installing ffmpeg

- **Windows:** `winget install Gyan.FFmpeg` (or `choco install ffmpeg`)
- **macOS:** `brew install ffmpeg`
- **Linux:** `sudo apt install ffmpeg` (Debian/Ubuntu) or your distro's equivalent

Verify it's on your PATH:

```bash
ffmpeg -version
```

---

## Setup

Clone the repo, then create a virtual environment and install the dependencies.

```bash
git clone https://github.com/sofiebauwens/RekordboxConverter.git
cd RekordboxConverter

# Create & activate a virtual environment
python -m venv .venv

# Activate it:
#   Windows (PowerShell):   .venv\Scripts\Activate.ps1
#   Windows (cmd):          .venv\Scripts\activate.bat
#   macOS / Linux:          source .venv/bin/activate

pip install -r requirements.txt
```

---

## Run

**Windows:** double-click **`run.bat`** (it starts the server and opens your browser).

**Any OS** (from the project folder, with your virtual environment activated):

```bash
cd backend
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Then open **<http://127.0.0.1:8000>** in your browser.

---

## How to use

1. **Close rekordbox completely.** Writing to the library while rekordbox is open
   can corrupt it, so the app refuses to add until it's closed. The status pill in
   the top-right shows whether it's safe.
2. Paste a YouTube link → **Fetch**. Edit the auto-filled **Title / Artist** if you like.
3. Click **Add to Rekordbox** and watch the progress (download → convert → tag → add).
4. Open rekordbox — the track is in your collection and in the **YouTube Imports** playlist.

---

## Where files go

- **MP3s** are saved permanently to `~/Music/PioneerDJ/YouTube/`.
  Rekordbox references tracks by their file path, so **don't move or delete them**
  after importing.
- Before the first database write each session, your rekordbox `master.db` is
  backed up to `~/rekordbox/db_backups/master_<timestamp>.db`.
- Re-adding the same link won't create duplicates (existing paths are detected).

---

## Platform support

| Feature | Windows | macOS / Linux |
|---|---|---|
| Download + convert to tagged MP3 | ✅ | ✅ |
| Add directly to rekordbox library | ✅ | ⚠️ not yet |

The library-write step currently locates the rekordbox database via the Windows
`%APPDATA%` path. macOS/Linux support (where the rekordbox DB lives under
`~/Library/Pioneer/rekordbox/`) isn't wired up yet — **contributions welcome!**
In the meantime, macOS/Linux users can still use the app to download and tag MP3s,
then drag them into rekordbox manually.

---

## How it works

- **`backend/downloader.py`** — `yt-dlp` grabs the best audio, ffmpeg transcodes to
  320 kbps MP3, and `mutagen` embeds the title, artist, and cover art.
- **`backend/rekordbox_io.py`** — `pyrekordbox` opens `master.db`, adds the track
  (get-or-create artist), ensures the *YouTube Imports* playlist exists, and links it.
  It backs up the DB first and refuses to write while rekordbox is running.
- **`backend/main.py`** — FastAPI server tying it together and serving the frontend.
- **`frontend/`** — a single-page vanilla HTML/CSS/JS UI (no build step).

**Tech stack:** FastAPI · Uvicorn · yt-dlp · pyrekordbox · mutagen · vanilla JS

---

## Troubleshooting

- **"ffmpeg not found"** — make sure `ffmpeg -version` works in the same terminal
  you launch the app from. On Windows you may need to reopen the terminal after install.
- **"Rekordbox is running"** — quit rekordbox fully (check the system tray / menu bar).
- **Nothing happens on Add** — confirm rekordbox 6 is installed and has been opened at
  least once, so `master.db` exists.

---

## License

No license file yet — add one (e.g. MIT) if you want others to reuse the code.
