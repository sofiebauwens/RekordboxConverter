"""Download a YouTube video and turn it into a tagged 320kbps MP3."""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Callable, Optional

from yt_dlp import YoutubeDL
from mutagen.id3 import ID3, TIT2, TPE1, APIC, ID3NoHeaderError
import urllib.request

# Where finished MP3s live. Rekordbox references files by path, so this is permanent.
OUTPUT_DIR = Path(os.path.expanduser("~")) / "Music" / "PioneerDJ" / "YouTube"

ProgressCb = Callable[[str, float, str], None]  # (stage, percent 0-100, message)


def _safe_filename(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*]', "", name)
    return name.strip()[:180] or "track"


def parse_artist_title(video_title: str, uploader: str) -> tuple[str, str]:
    """Best-effort split of a video title into (artist, title)."""
    cleaned = video_title
    # Drop common noise tags.
    for pat in [
        r"\(official.*?\)", r"\[official.*?\]", r"\(lyric.*?\)", r"\[lyric.*?\]",
        r"\(audio\)", r"\[audio\]", r"\(visualizer\)", r"\(hd\)", r"\(4k\)",
        r"\(music video\)", r"\(mv\)",
    ]:
        cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -–—")

    for sep in [" - ", " – ", " — ", " -", "- "]:
        if sep in cleaned:
            left, right = cleaned.split(sep, 1)
            return left.strip(), right.strip()
    # No separator: fall back to uploader as artist.
    uploader = re.sub(r"\s*-?\s*Topic$", "", uploader or "").strip()
    return uploader or "Unknown Artist", cleaned


def probe(url: str) -> dict:
    """Fetch metadata without downloading, for the editable preview."""
    with YoutubeDL({"quiet": True, "no_warnings": True, "skip_download": True}) as ydl:
        info = ydl.extract_info(url, download=False)
    artist, title = parse_artist_title(info.get("title", ""), info.get("uploader", ""))
    return {
        "raw_title": info.get("title", ""),
        "artist": artist,
        "title": title,
        "duration": info.get("duration"),
        "thumbnail": info.get("thumbnail"),
        "uploader": info.get("uploader"),
        "webpage_url": info.get("webpage_url", url),
    }


def _embed_tags(mp3_path: Path, title: str, artist: str, thumbnail_url: Optional[str]) -> None:
    try:
        tags = ID3(mp3_path)
    except ID3NoHeaderError:
        tags = ID3()
    tags.delall("TIT2")
    tags.delall("TPE1")
    tags.add(TIT2(encoding=3, text=title))
    tags.add(TPE1(encoding=3, text=artist))
    if thumbnail_url:
        try:
            with urllib.request.urlopen(thumbnail_url, timeout=15) as r:
                data = r.read()
            mime = "image/jpeg" if not thumbnail_url.lower().endswith(".png") else "image/png"
            tags.delall("APIC")
            tags.add(APIC(encoding=3, mime=mime, type=3, desc="Cover", data=data))
        except Exception:
            pass  # cover art is best-effort
    tags.save(mp3_path)


def download_mp3(
    url: str,
    title: str,
    artist: str,
    thumbnail_url: Optional[str],
    progress: ProgressCb,
) -> Path:
    """Download + convert to MP3, embed tags, return final file path."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    base = _safe_filename(f"{artist} - {title}")
    out_template = str(OUTPUT_DIR / f"{base}.%(ext)s")

    def hook(d: dict) -> None:
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            done = d.get("downloaded_bytes", 0)
            pct = (done / total * 100) if total else 0
            progress("downloading", pct, f"Downloading… {pct:0.0f}%")
        elif d["status"] == "finished":
            progress("converting", 100, "Converting to MP3…")

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": out_template,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "progress_hooks": [hook],
        "postprocessors": [
            {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "320"},
        ],
    }

    progress("downloading", 0, "Starting download…")
    with YoutubeDL(ydl_opts) as ydl:
        ydl.extract_info(url, download=True)

    mp3_path = OUTPUT_DIR / f"{base}.mp3"
    if not mp3_path.exists():
        # Fallback: find newest mp3 matching base.
        candidates = sorted(OUTPUT_DIR.glob(f"{base}*.mp3"), key=lambda p: p.stat().st_mtime)
        if candidates:
            mp3_path = candidates[-1]
        else:
            raise FileNotFoundError("MP3 conversion did not produce a file")

    progress("tagging", 100, "Writing tags & cover art…")
    _embed_tags(mp3_path, title, artist, thumbnail_url)
    return mp3_path
