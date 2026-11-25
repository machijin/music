# Sheet Music

Self-hosted service: upload a sheet music PDF or photo, Audiveris (optical music recognition) turns it into MusicXML (`.mxl`), the browser shows, plays and downloads it. Runs in Docker on Robert's home server next to kidhub (which uses 8091/8092); this one is on **8093**.

## Current state
- Slice 1 code done: `app/main.py` (FastAPI, jobs on disk in `data/jobs/<id>/job.json`, one Audiveris run at a time) and `app/static/index.html` (upload, list, Verovio viewer, Tone.js playback, `.mxl` and MIDI download).
- `Dockerfile` builds Audiveris 5.9.0 from source (needs Java 25, image `eclipse-temurin:25`), fetches the browser libraries from npm (`tools/vendor.sh`), and runs uvicorn.
- Tested in the Claude sandbox with a stand-in for Audiveris: upload, job status, download and the viewer work. **Not yet tested: the real Audiveris build and a real conversion** (the sandbox couldn't pull Docker images). First thing to check on the server.

## Plan
Build one slice at a time; get each working before starting the next.
1. Upload, view, play, download — code done, waiting on a server test
2. Library: titles, thumbnails, search, delete
3. Reader mode for a tablet on the piano stand (page turns, transpose, tempo, loop)
4. Upload corrected `.mxl`; link from kidhub's Piano tab

## Conventions
- American spelling in all copy.
- No CDNs at runtime; vendor browser libraries at build time.
- Never commit `data/` (uploads may be copyrighted scores).
