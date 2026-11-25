#!/bin/sh
# Fetch the browser libraries from npm into $1 (default app/static/vendor).
set -e
OUT=${1:-app/static/vendor}
TMP=$(mktemp -d)
mkdir -p "$OUT"
cd "$TMP"
npm pack --silent verovio@4.3.1 tone@14.8.49 @tonejs/midi@2.0.28 >/dev/null
for f in *.tgz; do mkdir -p "${f%.tgz}" && tar -xzf "$f" -C "${f%.tgz}"; done
cd - >/dev/null
cp "$TMP"/verovio-*/package/dist/verovio-toolkit-wasm.js "$OUT/"
cp "$TMP"/tone-*/package/build/Tone.js "$OUT/"
cp "$TMP"/tonejs-midi-*/package/build/Midi.js "$OUT/"
rm -rf "$TMP"
ls -la "$OUT"
