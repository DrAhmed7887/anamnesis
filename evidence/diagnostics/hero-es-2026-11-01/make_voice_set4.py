"""The fourth Spanish set's voice note (U13d): set 3's script, read by an ElevenLabs Spanish voice instead of macOS
`say`, so the film may play the note it was tested on (the macOS licence keeps `say` audio out of anything
published). Made like set 3's note apart from the voice: 16 kHz mono 16-bit with no metadata, after 0.8 s of
silence. The key comes from the Keychain (service ELEVENLABS_API_KEY) and is never printed.
    python3 -I evidence/diagnostics/hero-es-2026-11-01/make_voice_set4.py
Writes evidence/raw/media/public/voice/U13d.wav (git-ignored, like every voice note), the voice as returned
(U13d_elevenlabs.mp3) and its word timings (U13d_elevenlabs.words.json), and prints the WAV's sha256."""
import base64
import hashlib
import json
import subprocess
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "evidence" / "raw" / "media" / "public" / "voice"
SCRIPT = "Tomo bisoprolol diez miligramos cada mañana y metoprolol cien miligramos dos veces al día."  # set 3's
VOICE = "ypIbR1aohyRSdDv25DPr"  # "Rosa - Neutral, Calm and Genuine": ElevenLabs voice library, peninsular Spanish, old
MODEL = "eleven_multilingual_v2"
SETTINGS = {"stability": 0.5, "similarity_boost": 0.75, "style": 0.0, "use_speaker_boost": True}


def key() -> str:
    return subprocess.run(["security", "find-generic-password", "-s", "ELEVENLABS_API_KEY", "-w"],
                          capture_output=True, text=True, check=True).stdout.strip()


def words(alignment: dict) -> list[tuple[str, float, float]]:
    """Each word with the times its first character starts and its last character ends."""
    out, word, start, end = [], "", None, None
    for ch, t0, t1 in zip(alignment["characters"], alignment["character_start_times_seconds"],
                          alignment["character_end_times_seconds"]):
        if ch.isalnum():
            if not word:
                start = t0
            word, end = word + ch, t1
        elif word:
            out.append((word, round(start, 3), round(end, 3)))
            word = ""
    if word:
        out.append((word, round(start, 3), round(end, 3)))
    return out


def main() -> None:
    body = {"text": SCRIPT, "model_id": MODEL, "voice_settings": SETTINGS}
    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE}/with-timestamps?output_format=mp3_44100_128",
        data=json.dumps(body).encode(), headers={"xi-api-key": key(), "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as resp:
        reply = json.loads(resp.read())
    raw = OUT / "U13d_elevenlabs.mp3"
    raw.write_bytes(base64.b64decode(reply["audio_base64"]))
    timing = words(reply.get("alignment") or reply["normalized_alignment"])
    (OUT / "U13d_elevenlabs.words.json").write_text(json.dumps(timing, ensure_ascii=False) + "\n", encoding="utf-8")
    wav = OUT / "U13d.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(raw), "-map_metadata", "-1", "-af", "adelay=800:all=1",
                    "-ac", "1", "-ar", "16000", "-sample_fmt", "s16", str(wav)], check=True)
    print(f"{wav.name}: sha256 {hashlib.sha256(wav.read_bytes()).hexdigest()}")
    print(" ".join(f"{w}@{a:.2f}" for w, a, _ in timing))


if __name__ == "__main__":
    main()
