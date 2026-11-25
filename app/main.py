"""Sheet music service: upload a PDF or photo, Audiveris turns it into MusicXML."""
import json
import os
import shutil
import subprocess
import threading
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile
from pydantic import BaseModel
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

DATA_DIR = Path(os.environ.get("DATA_DIR", "./data"))
JOBS_DIR = DATA_DIR / "jobs"
AUDIVERIS = os.environ.get("AUDIVERIS_BIN", "/opt/audiveris/bin/Audiveris")
TIMEOUT = int(os.environ.get("OMR_TIMEOUT", "900"))
OCR_LANGUAGES = os.environ.get("OCR_LANGUAGES", "eng+jpn")  # Tesseract codes, joined by +
ALLOWED = {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff"}

JOBS_DIR.mkdir(parents=True, exist_ok=True)
app = FastAPI(title="Sheet music")
_one_at_a_time = threading.Lock()  # Audiveris is memory-hungry; run one job at a time.
_edit_lock = threading.Lock()  # guards job.json read-modify-write


def _job_dir(job_id: str) -> Path:
    if not job_id.isalnum():
        raise HTTPException(404)
    d = JOBS_DIR / job_id
    if not d.is_dir():
        raise HTTPException(404)
    return d


def _read(d: Path) -> dict:
    return json.loads((d / "job.json").read_text())


def _write(d: Path, job: dict) -> None:
    tmp = d / "job.json.tmp"
    tmp.write_text(json.dumps(job))
    tmp.replace(d / "job.json")


def _thumbnail(d: Path, src: Path) -> None:
    """Small PNG of the first page of the upload, for the library."""
    out = d / "thumb.png"
    try:
        if src.suffix == ".pdf":
            subprocess.run(["pdftoppm", "-png", "-singlefile", "-f", "1", "-l", "1",
                            "-scale-to", "360", str(src), str(d / "thumb")],
                           capture_output=True, timeout=60)
        else:
            from PIL import Image
            with Image.open(src) as im:
                im.thumbnail((360, 360))
                im.convert("RGB").save(out)
    except Exception:
        pass  # A missing thumbnail is fine; the page shows a placeholder.


def _update(d: Path, **fields) -> dict:
    """Change some fields of a job without losing edits made meanwhile."""
    with _edit_lock:
        job = _read(d)
        job.update(fields)
        _write(d, job)
        return job


def _run(d: Path) -> None:
    with _one_at_a_time:
        job = _update(d, status="working", started=time.time())
        out = d / "out"
        out.mkdir(exist_ok=True)
        cmd = [AUDIVERIS, "-batch", "-export",
               "-constant", f"org.audiveris.omr.text.Language.defaultSpecification={OCR_LANGUAGES}",
               "-output", str(out), "--", str(d / job["input"])]
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT)
            (d / "audiveris.log").write_text(p.stdout + "\n" + p.stderr)
            scores = sorted(out.rglob("*.mxl"))
            if scores:
                # Keep a stable name for the first (often only) movement.
                shutil.copy(scores[0], d / "score.mxl")
                result = dict(status="done", movements=len(scores))
            else:
                result = dict(status="failed", error="Audiveris found no music in this file.")
        except subprocess.TimeoutExpired:
            result = dict(status="failed", error=f"Took longer than {TIMEOUT // 60} minutes.")
        except FileNotFoundError:
            result = dict(status="failed", error="Audiveris is not installed in this container.")
        _update(d, finished=time.time(), **result)


@app.post("/api/scores")
async def upload(file: UploadFile):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED:
        raise HTTPException(400, "Upload a PDF or an image (PNG, JPG, TIFF).")
    job_id = uuid.uuid4().hex[:12]
    d = JOBS_DIR / job_id
    d.mkdir()
    with open(d / f"input{ext}", "wb") as f:
        shutil.copyfileobj(file.file, f)
    title = Path(file.filename).stem
    _write(d, {"id": job_id, "title": title, "input": f"input{ext}",
               "status": "queued", "created": time.time()})
    _thumbnail(d, d / f"input{ext}")
    threading.Thread(target=_run, args=(d,), daemon=True).start()
    return _read(d)


@app.get("/api/scores")
def list_scores():
    jobs = [_read(d) for d in JOBS_DIR.iterdir() if (d / "job.json").exists()]
    return sorted(jobs, key=lambda j: j["created"], reverse=True)


@app.get("/api/scores/{job_id}")
def get_score(job_id: str):
    return _read(_job_dir(job_id))


class ScoreUpdate(BaseModel):
    title: str | None = None
    composer: str | None = None
    settings: dict | None = None  # reader settings: zoom, transpose, tempo



@app.patch("/api/scores/{job_id}")
def update_score(job_id: str, body: ScoreUpdate):
    d = _job_dir(job_id)
    with _edit_lock:
        job = _read(d)
        if body.title is not None and body.title.strip():
            job["title"] = body.title.strip()[:200]
        if body.composer is not None:
            job["composer"] = body.composer.strip()[:200]
        if body.settings is not None:
            job["settings"] = {**job.get("settings", {}), **body.settings}
        _write(d, job)
    return job


@app.delete("/api/scores/{job_id}")
def delete_score(job_id: str):
    d = _job_dir(job_id)
    if _read(d)["status"] in ("queued", "working"):
        raise HTTPException(409, "Still being read; delete it when it's finished.")
    shutil.rmtree(d)
    return {"deleted": job_id}


@app.get("/api/scores/{job_id}/thumb.png")
def thumb(job_id: str):
    p = _job_dir(job_id) / "thumb.png"
    if not p.exists():
        raise HTTPException(404)
    return FileResponse(p, media_type="image/png")


@app.get("/api/scores/{job_id}/original")
def original(job_id: str):
    d = _job_dir(job_id)
    job = _read(d)
    return FileResponse(d / job["input"], filename=job["title"] + Path(job["input"]).suffix)


@app.get("/api/scores/{job_id}/score.mxl")
def download(job_id: str):
    d = _job_dir(job_id)
    if not (d / "score.mxl").exists():
        raise HTTPException(404, "Not ready yet.")
    name = _read(d)["title"] + ".mxl"
    return FileResponse(d / "score.mxl", media_type="application/vnd.recordare.musicxml",
                        filename=name)


@app.get("/api/scores/{job_id}/log")
def log(job_id: str):
    p = _job_dir(job_id) / "audiveris.log"
    if not p.exists():
        raise HTTPException(404)
    return FileResponse(p, media_type="text/plain")


# Jobs left "working" by a restart are queued again.
for _d in JOBS_DIR.iterdir():
    if (_d / "job.json").exists() and _read(_d)["status"] in ("queued", "working"):
        threading.Thread(target=_run, args=(_d,), daemon=True).start()

app.mount("/", StaticFiles(directory=Path(__file__).parent / "static", html=True), name="static")
