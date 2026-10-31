#!/bin/zsh
# Batch 24's Spanish and German voice notes for the live cases S1-S4 and G1-G4, pre-registered in
# evidence/batches/24/manifest.md. macOS `say`, voices Mónica (es_ES) and Anna (de_DE), reading invented scripts.
# For runs only: the macOS licence keeps system voices out of the video and any hosted brief (docs/DATA_HANDLING.md).
# Output: evidence/raw/media/public/voice/ (git-ignored), beside U1-U12; rerun this script to rebuild it.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
out=evidence/raw/media/public/voice
mkdir -p "$out"

note() {  # case id, voice, script. Voice Transcribe takes WAV only: mono, 16-bit PCM, 16 kHz, no metadata
  say -v "$2" -o "$out/$1.aiff" "$3"
  ffmpeg -loglevel error -y -i "$out/$1.aiff" -map_metadata -1 -ac 1 -ar 16000 -sample_fmt s16 "$out/$1.wav"
  rm -f "$out/$1.aiff"
  print "$1 $(shasum -a 256 "$out/$1.wav" | cut -c1-16) $(wc -c < "$out/$1.wav" | tr -d ' ') bytes"
}

note S1 Mónica "Tomo Emconcor cinco miligramos una vez al día."
note S2 Mónica "Tomo bisoprolol dos coma cinco miligramos por la mañana."
note S3 Mónica "Tomo Gelocatil de un gramo cuando tengo dolor."
note S4 Mónica "Tomo medio comprimido de Panadol de quinientos."
note G1 Anna "Ich nehme Metoprolol fünfzig Milligramm zweimal täglich."
note G2 Anna "Ich nehme morgens eine halbe Tablette Beloc-Zok hundert Milligramm."
note G3 Anna "Ich nehme Sortis vierzig Milligramm am Abend."
note G4 Anna "Ibuprofen vierhundert habe ich abgesetzt."
