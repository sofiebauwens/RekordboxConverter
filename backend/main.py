"""FastAPI app: YouTube link -> MP3 -> rekordbox."""
from __future__ import annotations

import json
import queue
import threading
import uuid
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import downloader
import rekordbox_io

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"

app = FastAPI(title="YT → Rekordbox")

# Per-job progress queues.
_jobs: dict[str, queue.Queue] = {}
_recent: list[dict] = []


class ProbeReq(BaseModel):
    url: str


class AddReq(BaseModel):
    url: str
    title: str
    artist: str
    thumbnail: str | None = None


@app.get("/api/status")
def status():
    return {"rekordbox_running": rekordbox_io.is_rekordbox_running()}


@app.post("/api/probe")
def probe(req: ProbeReq):
    try:
        return downloader.probe(req.url)
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})


@app.get("/api/recent")
def recent():
    return list(reversed(_recent[-20:]))


@app.post("/api/add")
def add(req: AddReq):
    job_id = uuid.uuid4().hex
    q: queue.Queue = queue.Queue()
    _jobs[job_id] = q

    def emit(stage: str, pct: float, msg: str, **extra):
        q.put({"stage": stage, "percent": round(pct, 1), "message": msg, **extra})

    def worker():
        try:
            mp3 = downloader.download_mp3(
                req.url, req.title, req.artist, req.thumbnail,
                lambda s, p, m: emit(s, p, m),
            )
            emit("adding", 100, "Adding to rekordbox library…")
            result = rekordbox_io.add_track(mp3, req.title, req.artist)
            entry = {
                "title": req.title,
                "artist": req.artist,
                "thumbnail": req.thumbnail,
                "file": str(mp3),
                "playlist": result["playlist"],
            }
            _recent.append(entry)
            emit("done", 100,
                 f"Added to “{result['playlist']}” ✓" if result["created"]
                 else f"Already in library — ensured in “{result['playlist']}” ✓",
                 entry=entry)
        except Exception as e:
            emit("error", 0, str(e))
        finally:
            q.put(None)  # sentinel: stream complete

    threading.Thread(target=worker, daemon=True).start()
    return {"job_id": job_id}


@app.get("/api/events/{job_id}")
def events(job_id: str):
    q = _jobs.get(job_id)
    if q is None:
        return JSONResponse(status_code=404, content={"error": "unknown job"})

    def stream():
        while True:
            item = q.get()
            if item is None:
                _jobs.pop(job_id, None)
                break
            yield f"data: {json.dumps(item)}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.get("/")
def index():
    return FileResponse(FRONTEND / "index.html")


app.mount("/", StaticFiles(directory=FRONTEND), name="static")
