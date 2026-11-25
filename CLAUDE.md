# Sheet Music

Self-hosted service: upload a sheet music PDF or photo, Audiveris (optical music recognition) turns it into MusicXML (`.mxl`), the browser shows, plays and downloads it. Runs in Docker on Robert's home server next to kidhub (which uses 8091/8092); this one is on **8093**.

## Current state
- Slice 1 code done: `app/main.py` (FastAPI, jobs on disk in `data/jobs/<id>/job.json`, one Audiveris run at a time) and `app/static/index.html` (upload, list, Verovio viewer, Tone.js playback, `.mxl` and MIDI download).
- `Dockerfile` builds Audiveris 5.9.0 from source (needs Java 25; both stages pinned to `eclipse-temurin:25-*-noble`, Ubuntu 24.04 / Python 3.12, because the plain `25-jre` tag moved to Ubuntu 26.04 / Python 3.14 and broke the pip install), fetches the browser libraries from npm (`tools/vendor.sh`), and runs uvicorn.
- Slice 2 code done: library grid with first-page thumbnails (`thumb.png` from pdftoppm/Pillow), search, edit dialog (title, composer, downloads, log, delete). `PATCH`/`DELETE /api/scores/<id>`; job.json writes go through `_edit_lock` / `_update()` so a running conversion doesn't undo a rename.
- Slice 3 code done: reader at `#score/<id>`, one page per screen (Verovio `pageHeight` = stage height), tap zones and arrow/Page keys (Bluetooth pedals), zoom, transpose (semitones, reloads the score), speed, loop bars (from `renderToTimemap` measure times), follow-along highlight and page turns during playback (`getElementsAtTime`), full screen + wake lock (HTTPS only). Zoom/transpose/tempo saved in `job.settings`; the loop isn't saved.
- Deployed (Nov 2026) as a Portainer **Repository** stack from `main` (`docker-compose.yml`, GitHub fine-grained read-only token). Data lives on the server in `/home/docker/rvmusic` (`MUSIC_DIR`). The Audiveris build works there; Robert uploaded a score and played it back. Still to check: how accurate conversions are (clean PDF vs phone photo) and the reader on a real tablet.

## Plan
Build one slice at a time; get each working before starting the next.
1. Upload, view, play, download — works on the server
2. Library: titles, thumbnails, search, delete — code done, waiting on a server test
3. Reader mode for a tablet on the piano stand (page turns, transpose, tempo, loop) — code done, waiting on a tablet test
4. Upload corrected `.mxl`; link from kidhub's Piano tab

## Conventions
- American spelling in all copy.
- No CDNs at runtime; vendor browser libraries at build time.
- Never commit `data/` (uploads may be copyrighted scores).
