#!/bin/sh
# Fetch the browser libraries from npm into $1 (default app/static/vendor).
set -e
OUT=${1:-app/static/vendor}
TMP=$(mktemp -d)
mkdir -p "$OUT"
cd "$TMP"
npm pack --silent verovio@4.3.1 tone@14.8.49 @tonejs/midi@2.0.28 @audio-samples/piano-mp3-velocity8@1.0.5 >/dev/null
for f in *.tgz; do mkdir -p "${f%.tgz}" && tar -xzf "$f" -C "${f%.tgz}"; done
cd - >/dev/null
cp "$TMP"/verovio-*/package/dist/verovio-toolkit-wasm.js "$OUT/"
cp "$TMP"/tone-*/package/build/Tone.js "$OUT/"
cp "$TMP"/tonejs-midi-*/package/build/Midi.js "$OUT/"
# Salamander Grand Piano (Alexander Holm, CC BY 3.0), one recording every 3 keys.
# Renamed from "D#4v8.mp3" to "Ds4.mp3" so the names are URL-safe.
mkdir -p "$OUT/piano"
for f in "$TMP"/audio-samples-piano-mp3-velocity8-*/package/audio/*.mp3; do
  n=$(basename "$f" .mp3); n=${n%v8}; n=$(echo "$n" | sed 's/#/s/')
  cp "$f" "$OUT/piano/$n.mp3"
done
cp "$TMP"/audio-samples-piano-mp3-velocity8-*/package/LICENSE "$OUT/piano/LICENSE" 2>/dev/null || true
rm -rf "$TMP"
ls -la "$OUT" "$OUT/piano" | tail -n +1 | head -50
