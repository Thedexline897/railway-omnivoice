# OmniVoice Persian TTS API (Railway)

Free, unlimited Persian voice-cloning text-to-speech, deployed on Railway.
It clones a voice from a short reference audio (3–10 s) and speaks any
Persian text in that voice. Model: `k2-fsa/OmniVoice` (+
`openai/whisper-large-v3-turbo`, used internally at generate time).

## Endpoints

- `GET /health` → `{"status": "ok", "model_loaded": false}` (model loads lazily)
- `POST /generate` → multipart form with:
  - `text` — the text to speak (Persian; add Arabic diacritics ـ for correct
    pronunciation, e.g. `سَلام بابِه!`)
  - `ref_audio` — a short voice sample file (3–10 s, wav/mp3/flac)
  - Returns: a WAV file (24 kHz, mono) of the cloned voice speaking the text.

## Call it

```bash
# Health check
curl https://<your-service>.up.railway.app/health

# Generate (replace the URL and the ref file)
curl -X POST https://<your-service>.up.railway.app/generate \
  -F "text=سَلام بابِه! این یِه تِستِ صِداست." \
  -F "ref_audio=@/path/to/ref.wav" \
  -o out.wav
```

Telegram bot: POST the same multipart request from the bot and send the
returned WAV back as a voice/audio message.

## Notes

- **First request is slow.** The model (~5 GB: 2.4 GB main + 769 MB audio
  tokenizer + 1.54 GB Whisper) downloads from Hugging Face into the
  container's HF cache on first use, then loads into RAM. Expect several
  minutes for the first `/generate`; later requests reuse the loaded model.
  If the container restarts, the cache is gone and it re-downloads.
- **RAM matters.** The model needs several GB of RAM. Railway's smallest
  instance may run out of memory and crash on the first `/generate`. If
  that happens, raise the service memory in the Railway dashboard (costs
  more credit). Keep the service asleep / scale-to-zero when idle if
  Railway offers it, so the $5 trial credit lasts.
- **Cost.** This is a trial deployment on the user's 30-day Railway trial
  ($5 credit). Do not upgrade the plan. Watch usage in the Railway
  dashboard; a big always-on instance will burn the $5 fast.
- **Privacy.** Do not store users' reference voices. The API only uses the
  uploaded `ref_audio` for that one request and deletes the temp file.
- **Local run (for testing):**
  ```bash
  pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
  pip install -r requirements.txt
  uvicorn app:app --host 0.0.0.0 --port 8000
  ```
