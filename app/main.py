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
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

DATA_DIR = Path(os.environ.get("DATA_DIR", "./data"))
JOBS_DIR = DATA_DIR / "jobs"
AUDIVERIS = os.environ.get("AUDIVERIS_BIN", "/opt/audiveris/bin/Audiveris")
TIMEOUT = int(os.environ.get("OMR_TIMEOUT", "900"))
ALLOWED = {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff"}

JOBS_DIR.mkdir(parents=True, exist_ok=True)
app = FastAPI(title="Sheet music")
_one_at_a_time = threading.Lock()  # Audiveris is memory-hungry; run one job at a time.


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


def _run(d: Path) -> None:
    job = _read(d)
    with _one_at_a_time:
        job.update(status="working", started=time.time())
        _write(d, job)
        out = d / "out"
        out.mkdir(exist_ok=True)
        cmd = [AUDIVERIS, "-batch", "-export", "-output", str(out), "--", str(d / job["input"])]
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT)
            (d / "audiveris.log").write_text(p.stdout + "\n" + p.stderr)
            scores = sorted(out.rglob("*.mxl"))
            if scores:
                # Keep a stable name for the first (often only) movement.
                shutil.copy(scores[0], d / "score.mxl")
                job.update(status="done", movements=len(scores))
            else:
                job.update(status="failed", error="Audiveris found no music in this file.")
        except subprocess.TimeoutExpired:
            job.update(status="failed", error=f"Took longer than {TIMEOUT // 60} minutes.")
        except FileNotFoundError:
            job.update(status="failed", error="Audiveris is not installed in this container.")
        job["finished"] = time.time()
        _write(d, job)


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
    threading.Thread(target=_run, args=(d,), daemon=True).start()
    return _read(d)


@app.get("/api/scores")
def list_scores():
    jobs = [_read(d) for d in JOBS_DIR.iterdir() if (d / "job.json").exists()]
    return sorted(jobs, key=lambda j: j["created"], reverse=True)


@app.get("/api/scores/{job_id}")
def get_score(job_id: str):
    return _read(_job_dir(job_id))


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
