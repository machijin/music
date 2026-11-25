# Sheet Music

A self-hosted service that turns scanned or photographed sheet music into **MusicXML** (`.mxl`), the open "epub for music": it reflows to any screen, plays back, and opens in MuseScore, Finale, Dorico and most music apps.

Upload a PDF or a photo of a printed score. [Audiveris](https://github.com/Audiveris/audiveris) reads it, then the page shows the score, plays it, and offers `.mxl` and MIDI downloads.

## Using it

- **Library:** upload by tapping the box or dropping a file on it. Each score gets a card with a picture of its first page. Search filters by title and composer. The ⋯ button renames a score, adds the composer, downloads the original or the `.mxl`, shows the Audiveris log, or deletes it.
- **Reader:** tap a card. Each screen is one page. Tap the right two thirds of the page to turn forward and the left third to go back. Arrow and Page Up/Down keys work too, so Bluetooth page-turn pedals do as well.
  - **A− / A+** changes the size, **♭ / ♯** transposes by a semitone, and the slider sets the speed (40–150%). These are saved per score on the server, so the tablet and phone match.
  - **🔁 Loop:** tap the first bar, then the last. Play repeats those bars. Tap the button again to clear the loop.
  - **▶ Play** plays the score with the current notes highlighted, turning pages as it goes. Space starts and stops playback.
  - **🎹 Piano / 〰️ Simple** picks the sound: recordings of a real grand piano (the default), or the light built-in synth for slow devices. The choice is remembered per device. The piano's recordings (5.5 MB) load the first time you press Play.
  - **⛶** goes full screen and hides the controls; ☰ in the corner brings them back. The screen only stays awake over HTTPS (browser rule), so on plain `http://` set the tablet's auto-lock to "never" while practicing.

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

- `app/main.py`: FastAPI. `POST /api/scores` stores the upload in `data/jobs/<id>/`, makes `thumb.png` (pdftoppm or Pillow), and runs `Audiveris -batch -export` in the background, one job at a time. `GET /api/scores` lists jobs; `PATCH /api/scores/<id>` changes `title`, `composer` or reader `settings`; `DELETE` removes a score. Files: `score.mxl`, `thumb.png`, `original`, `log`.
- `app/static/index.html`: library (`#`) and reader (`#score/<id>`). Verovio draws the score page by page, transposes, makes the MIDI and the timing map used for looping and following along; Tone.js plays it.
- The browser libraries are fetched from npm at build time (`tools/vendor.sh`), so nothing loads from a CDN at runtime. For local development without Docker, run `sh tools/vendor.sh` once.

## Credits

- Piano sound: [Salamander Grand Piano V3](https://archive.org/details/SalamanderGrandPianoV3) by Alexander Holm, [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/), via the npm package `@audio-samples/piano-mp3-velocity8`.
- [Audiveris](https://github.com/Audiveris/audiveris) (AGPL-3.0), [Verovio](https://www.verovio.org) (LGPL-3.0), [Tone.js](https://tonejs.github.io) (MIT), [@tonejs/midi](https://github.com/Tonejs/Midi) (MIT).

## Plan

1. Upload, view, play and download (built).
2. Library: titles, thumbnails, search, delete (built).
3. Reader mode for a tablet on the piano stand: page turns, transpose, tempo, loop a section (built).
4. Corrections (upload a fixed `.mxl`) and a link to the kidhub 🎹 Piano tab.
