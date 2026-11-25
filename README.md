# Sheet Music

A self-hosted service that turns scanned or photographed sheet music into **MusicXML** (`.mxl`), the open "epub for music": it reflows to any screen, plays back, and opens in MuseScore, Finale, Dorico and most music apps.

Upload a PDF or a photo of a printed score. [Audiveris](https://github.com/Audiveris/audiveris) reads it, then the page shows the score, plays it, and offers `.mxl` and MIDI downloads.

## Run it

```sh
docker compose up -d --build
```

Then open `http://<server>:8093`. The first build takes 5 to 10 minutes because it compiles Audiveris from source (Java 25). Uploaded files and results live in `./data` (set `MUSIC_DIR` to put them elsewhere, for example `/opt/music/data`).

For Portainer: add a **Repository** stack pointing at this repo with `docker-compose.yml`.

## What to expect

- Clean printed scores (PDFs from IMSLP, printed method books) convert well.
- Phone photos work if the page is flat, well lit, and straight on. Dense piano music, handwriting and unusual notation come out with mistakes.
- To fix mistakes: download the `.mxl`, correct it in MuseScore. (Re-uploading the fixed file is a later slice.)
- Audiveris uses 1 to 2 GB of memory while it works. Jobs run one at a time.

## How it works

- `app/main.py`: FastAPI. `POST /api/scores` stores the upload in `data/jobs/<id>/` and runs `Audiveris -batch -export` in the background. `GET /api/scores` lists jobs, `GET /api/scores/<id>/score.mxl` downloads the result, `GET /api/scores/<id>/log` shows the Audiveris log when a job fails.
- `app/static/index.html`: upload, list, and a viewer. Verovio draws the score and makes the MIDI; Tone.js plays it.
- The browser libraries are fetched from npm at build time (`tools/vendor.sh`), so nothing loads from a CDN at runtime. For local development without Docker, run `sh tools/vendor.sh` once.

## Plan

1. Upload, view, play and download (this slice).
2. Library: titles, thumbnails, search, delete.
3. Reader mode for a tablet on the piano stand: big page turns, transpose, tempo, loop a section.
4. Corrections (upload a fixed `.mxl`) and a link to the kidhub 🎹 Piano tab.
