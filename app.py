#!/usr/bin/env python3
"""OmniVoice Persian voice-cloning TTS API.

Endpoints:
  GET  /health    -> {"status": "ok", "model_loaded": bool}
  POST /generate  -> multipart form: text (str) + ref_audio (file).
                     Returns a WAV file of the cloned voice speaking the text.

The model (k2-fsa/OmniVoice + openai/whisper-large-v3-turbo) downloads from
Hugging Face on first use (~5 GB) into the HF cache, and loads lazily on the
first /generate call so the service starts fast and /health stays responsive.
The first /generate call is therefore slow (download + load + generate).
Persian text is passed through unchanged (the caller should add Arabic
diacritics for correct pronunciation).
"""

import io
import logging
import os
import tempfile
import threading

import soundfile as sf
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("omnivoice-api")

app = FastAPI(title="OmniVoice Persian TTS")

_model = None
_model_lock = threading.Lock()


def get_model():
    """Load the OmniVoice model once (thread-safe, lazy)."""
    global _model
    if _model is not None:
        return _model
    with _model_lock:
        if _model is not None:
            return _model
        log.info("Loading OmniVoice model (first run downloads ~5 GB from Hugging Face)...")
        from omnivoice import OmniVoice

        _model = OmniVoice.from_pretrained("k2-fsa/OmniVoice", device_map="cpu")
        log.info("OmniVoice model loaded.")
        return _model


@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": _model is not None}


@app.get("/")
def root():
    return {
        "service": "OmniVoice Persian TTS",
        "endpoints": {
            "GET /health": "liveness check",
            "POST /generate": "multipart: text + ref_audio file -> WAV audio",
        },
    }


@app.post("/generate")
async def generate(text: str = Form(...), ref_audio: UploadFile = File(...)):
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="text must not be empty")
    if not ref_audio.filename:
        raise HTTPException(status_code=400, detail="ref_audio file is required")

    # Save the uploaded reference audio to a temp file.
    suffix = os.path.splitext(ref_audio.filename or "ref.wav")[1] or ".wav"
    if suffix.lower() not in (".wav", ".mp3", ".flac", ".ogg", ".m4a"):
        suffix = ".wav"
    tmp_ref = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        content = await ref_audio.read()
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="ref_audio file is empty")
        tmp_ref.write(content)
        tmp_ref.close()

        model = get_model()
        log.info("Generating: text=%r ref=%s (%d bytes)", text[:80], ref_audio.filename, len(content))
        audio = model.generate(text=text, ref_audio=tmp_ref.name)
        # audio[0] is a numpy array at 24000 Hz.
        out_path = tempfile.mktemp(suffix=".wav")
        sf.write(out_path, audio[0], 24000)
        log.info("Generated %s", out_path)
        return FileResponse(out_path, media_type="audio/wav", filename="omnivoice.wav")
    except HTTPException:
        raise
    except Exception as e:
        log.exception("generate failed")
        raise HTTPException(status_code=500, detail=f"generate failed: {e}")
    finally:
        try:
            os.unlink(tmp_ref.name)
        except OSError:
            pass


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
