# OmniVoice Persian voice-cloning TTS API (CPU-only).
# The ~5 GB of model files are NOT baked into the image; they download from
# Hugging Face into the HF cache on first use (see app.py lazy loading).

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/app/.hf-cache \
    HF_HUB_DISABLE_SYMLINKS_WARNING=1

WORKDIR /app

# System deps: ffmpeg + libsndfile (soundfile), git/curl for diagnostics.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg libsndfile1 git curl \
    && rm -rf /var/lib/apt/lists/*

# CPU-only torch + torchaudio FIRST (from the PyTorch CPU index), so that
# installing `omnivoice` afterwards does not pull the multi-GB CUDA builds.
RUN pip install --no-cache-dir torch torchaudio \
    --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

# Railway injects $PORT; uvicorn binds to it.
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}"]
