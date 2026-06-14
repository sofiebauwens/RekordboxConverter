"""Safely add tracks to the rekordbox 6 database."""
from __future__ import annotations

import datetime as _dt
import shutil
from pathlib import Path
from typing import Optional

from mutagen.mp3 import MP3
from pyrekordbox import Rekordbox6Database
from pyrekordbox.config import get_pioneer_app_dir
from pyrekordbox.utils import get_rekordbox_pid

PLAYLIST_NAME = "YouTube Imports"
_BACKUP_DIR = Path.home() / "rekordbox" / "db_backups"
_backed_up_this_session = False


def is_rekordbox_running() -> bool:
    try:
        return get_rekordbox_pid() > 0
    except Exception:
        return False


def _db_path() -> Path:
    """Locate rekordbox 6's master.db cross-platform.

    get_pioneer_app_dir() resolves the Pioneer application directory per OS
    (``%APPDATA%/Pioneer`` on Windows, ``~/Library/Pioneer`` on macOS).
    """
    return Path(get_pioneer_app_dir()) / "rekordbox" / "master.db"


def backup_database() -> Optional[Path]:
    """Copy master.db to a timestamped backup once per session."""
    global _backed_up_this_session
    if _backed_up_this_session:
        return None
    src = _db_path()
    if not src.exists():
        return None
    _BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = _BACKUP_DIR / f"master_{stamp}.db"
    shutil.copy2(src, dst)
    _backed_up_this_session = True
    return dst


def _audio_fields(mp3_path: Path) -> dict:
    """Read length/bitrate/etc from the MP3 so rekordbox displays them.

    add_content() already sets FileSize/FileType, so we only add what it misses.
    """
    fields: dict = {}
    try:
        audio = MP3(mp3_path)
        fields["Length"] = int(round(audio.info.length))
        fields["BitRate"] = int(round(audio.info.bitrate / 1000))  # kbps
        fields["SampleRate"] = int(audio.info.sample_rate)
    except Exception:
        pass
    return fields


def add_track(mp3_path: Path, title: str, artist: str) -> dict:
    """Add an MP3 to the rekordbox collection + the YouTube Imports playlist.

    Raises RuntimeError if rekordbox is running (writing then risks corruption).
    """
    if is_rekordbox_running():
        raise RuntimeError(
            "Rekordbox is running. Close it completely before adding tracks to the library."
        )

    backup_database()

    db = Rekordbox6Database()
    try:
        # Avoid duplicates by path.
        existing = None
        for c in db.get_content():
            if c.FolderPath and Path(c.FolderPath) == mp3_path:
                existing = c
                break

        if existing is None:
            content = db.add_content(str(mp3_path), Title=title, **_audio_fields(mp3_path))
            # Link the artist (get-or-create: add_artist raises if the name exists).
            if artist:
                try:
                    artist_row = db.get_artist(Name=artist).first() or db.add_artist(artist)
                    content.ArtistID = artist_row.ID
                except Exception:
                    pass
            created = True
        else:
            content = existing
            created = False

        # Ensure the playlist exists.
        playlist = db.get_playlist(Name=PLAYLIST_NAME).first()
        if playlist is None:
            playlist = db.create_playlist(PLAYLIST_NAME)

        # Add to playlist if not already there.
        in_playlist = any(
            s.ContentID == content.ID
            for s in db.get_playlist_songs(PlaylistID=playlist.ID)
        )
        if not in_playlist:
            db.add_to_playlist(playlist, content)

        db.commit()
        return {
            "content_id": str(content.ID),
            "created": created,
            "playlist": PLAYLIST_NAME,
        }
    finally:
        db.close()
