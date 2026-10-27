# Muse Voice Transcribe

Verified 2026-10-26

Meta's speech-to-text model on Meta Model API. Model id `muse-voice-transcribe-1.0`. Returns transcript text only: no speech synthesis, no word-level timestamps, no sound events, no emotion detection ([models](https://dev.meta.ai/docs/models#muse-voice-transcribe)). Pricing $0.18 per audio hour, billed in whole seconds, same for streaming and file ([pricing](https://dev.meta.ai/docs/pricing-rate-limits)).

## Endpoints

| Endpoint | Use | Auth |
|---|---|---|
| `POST https://api.meta.ai/v1/asr/transcribe` | A recording you already have (multipart upload) | `Authorization: Bearer` header |
| `wss://api.meta.ai/v1/asr/realtime` | Live audio over WebSocket | Key goes in the first JSON frame (`authorization.accessToken = "Bearer <key>"`); the HTTP header is ignored |

Source: [speech to text](https://dev.meta.ai/docs/speech-to-text), [voice API reference](https://dev.meta.ai/docs/api-reference/voice). This is not an OpenAI-SDK call; use `requests`/`curl` or a WebSocket client ([voice cookbook](https://github.com/meta-models/meta-model-cookbook/tree/main/06_muse_voice)).

## Audio formats and limits

- File endpoint: only RIFF/WAVE, mono, 16-bit integer PCM at 16 kHz or 24 kHz. Anything else (m4a, mp3, opus) must be converted first ([speech to text](https://dev.meta.ai/docs/speech-to-text#quickstart-file)):
  `ffmpeg -i input.m4a -ac 1 -ar 24000 -c:a pcm_s16le -map_metadata -1 output.wav`
- File endpoint caps: request body 32 MB (413), audio 10 minutes (400), wrong format (400), rate limit (429), server budget (500).
- Realtime: raw signed 16-bit little-endian mono PCM at 24 kHz (`PCM_24KHZ`, preferred) or 16 kHz (`PCM_16KHZ`). Pace audio in real time, never more than 5 s ahead. Handshake within 10 s. Max session 60 minutes, no resume token.
- Limits: 256 concurrent streams, 16,000 streams per hour, shared by both endpoints. Realtime rejection closes with 1013; file returns 429.

## Minimal file request (from the docs)

```shell
curl --fail-with-body 'https://api.meta.ai/v1/asr/transcribe' \
  -H "Authorization: Bearer $MODEL_API_KEY" -H "Accept: application/json" \
  -F 'request={"model":"muse-voice-transcribe-1.0","audioEncoding":"WAV","mode":"PUSH_TO_TALK"};type=application/json' \
  -F 'audio=@recording.wav;type=audio/wav'
```

Source: [transcribe reference](https://dev.meta.ai/docs/api-reference/voice/transcribe). `Accept` may be `application/json` (default), `text/event-stream`, or `text/plain`; anything else returns 406. `sessionId` query parameter is optional; keep it for support tickets.

## Modes, timestamps, diarization

- `mode`: `PUSH_TO_TALK` (default, one turn, `turns` array empty), `ENDPOINTING` (model finds turn boundaries), `DIARIZATION` (turns plus speaker labels). Fixed for the session ([speech to text](https://dev.meta.ai/docs/speech-to-text#modes)).
- Timestamp granularity: turn level only. JSON `turns[]` has `turnId`, `startMs`, `endMs`, `transcript`, `speaker`; `audioDurationMs` for the whole clip. "Word-level timestamps are not available" ([STT](https://dev.meta.ai/docs/speech-to-text)). `audioProcessedMs` in events is progress, not a word time.
- Confidence scores: not available ([STT](https://dev.meta.ai/docs/speech-to-text)). The plan's idea of gating on ASR confidence has no API support.
- Diarization: yes, labels `A`, `B` (session-scoped, not verified identities); the model page claims 20+ speakers ([model page](https://dev.meta.ai/models/muse-voice-transcribe)). DIARIZATION is not tuned for low latency.
- Partials: `transcript` events with `final` flag (`partialMode` `CUMULATIVE` default, `DELTA` for SSE file responses). In ENDPOINTING/DIARIZATION the text arrives in `speechComplete`, and turns can overlap: key on `turnId`.

## Languages

25 supported languages with code-switching: Arabic, Bengali, Dutch, English, French, German, Hebrew, Hindi, Indonesian, Italian, Japanese, Kannada, Korean, Malay, Mandarin Chinese, Marathi, Polish, Portuguese, Spanish, Tagalog, Tamil, Telugu, Thai, Turkish, Vietnamese ([STT](https://dev.meta.ai/docs/speech-to-text#language-biasing)). So Arabic, Spanish and German are all covered. The models page calls them "evaluated languages" ([models](https://dev.meta.ai/docs/models)).

- Arabic dialects (for example Egyptian), per-language accuracy, and medical vocabulary accuracy: Not documented.
- `languageBias`: list of language names such as `["Arabic", "English"]`; a hint, not a force. Omit it to auto-detect. Fixed once the session starts.
- `keywords`: list of terms to bias toward (use for drug names). Biases but does not guarantee spelling ([STT](https://dev.meta.ai/docs/speech-to-text#keywords)).

## Translation

Not documented. The model "returns transcript text" and no translate parameter exists in the request schema ([voice schemas](https://dev.meta.ai/docs/api-reference/voice/schemas)). Do translation in a second step with Muse Spark or another LLM, and keep the raw transcript.

## Related

- Handshake fields: `authorization`, `audioEncoding`, `model`, `mode`, `partialMode`, `emitAudioProgress`, `languageBias`, `keywords` ([realtime reference](https://dev.meta.ai/docs/api-reference/voice/realtime)).
- Muse Code has `muse voice transcribe <FILE>` ("any wav", local `muse voice transcribe --help`). Which backend it calls is Not documented. Voice dictation in Muse Code's TUI is a separate feature ([interactive](https://dev.meta.ai/docs/muse-code/interactive#voice)).
- Spark can also transcribe audio, but Spark 1.3 audio is degraded: [muse-spark.md](muse-spark.md).
- Cookbook recipe: [voice API fundamentals](https://dev.meta.ai/docs/cookbook/voice-api-fundamentals).
