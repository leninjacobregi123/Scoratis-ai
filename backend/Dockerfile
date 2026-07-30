# Scoratis Backend - serves both the FastAPI API and the Celery worker
# (including real video rendering: Manim + ffmpeg + edge-tts) from one image.
#
# An earlier version of this Dockerfile (removed) based itself on a
# CUDA/pytorch image. That GPU base is unnecessary here: Manim rendering,
# ffmpeg muxing, and edge-tts narration are all CPU-only in this codebase -
# GPU is only used for local Ollama/embeddings, which production doesn't use
# (see config.py's DEFAULT_LLM_PROVIDER, meant to point at a cloud provider
# in production). A slim base keeps the image smaller and avoids paying for
# GPU-instance pricing with no GPU workload to justify it.

FROM python:3.11-slim

WORKDIR /app

# System dependencies:
# - ffmpeg: video/audio muxing (tasks_pkg/video_tasks.py)
# - libcairo2-dev, libpango1.0-dev, libglib2.0-dev, pkg-config: Manim's 2D rendering backend
# - gfortran, libopenblas-dev, liblapack-dev: numpy/scipy build deps
# - libmagic1, poppler-utils, tesseract-ocr: document ingestion (services/ingestion_service.py)
# - texlive-*: Manim's Tex()/MathTex() (LaTeX equation rendering) - confirmed
#   missing from the orphaned reference Dockerfile, a real gap since any
#   math-heavy generated scene would fail without it
# - curl: container healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    ffmpeg \
    libcairo2-dev \
    libpango1.0-dev \
    libglib2.0-dev \
    pkg-config \
    gfortran \
    libopenblas-dev \
    liblapack-dev \
    libmagic1 \
    poppler-utils \
    tesseract-ocr \
    texlive-latex-base \
    texlive-latex-extra \
    texlive-fonts-recommended \
    texlive-science \
    cm-super \
    dvisvgm \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# sentence-transformers pulls in torch transitively; PyPI's default Linux wheel
# bundles the full CUDA toolkit (cudnn/cublas/nccl/etc, several GB) even though
# this container is CPU-only (GPU is local-Ollama-only, see comment above).
# Installing the CPU-only build first satisfies that dependency without pulling
# any of it.
RUN pip install --no-cache-dir --timeout 120 --retries 10 torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir --timeout 120 --retries 10 -r requirements.txt

# Pre-download the embedding model during build so the first request doesn't
# pay for it (and so it's cached in the image layer, not re-fetched per boot)
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

COPY . .

RUN mkdir -p generated_videos uploads audio_cache
RUN chmod +x docker-entrypoint.sh

EXPOSE 8000

# 127.0.0.1, not localhost - avoids a wasted IPv6 attempt-then-fallback on
# every check (uvicorn --host 0.0.0.0 only binds IPv4); curl falls back to
# IPv4 fine either way, unlike the frontend's busybox wget.
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://127.0.0.1:8000/health || exit 1

# docker-entrypoint.sh runs migrations (only when RUN_MIGRATIONS=true, set by
# the `backend` service in docker-compose.prod.yml) before handing off to CMD.
ENTRYPOINT ["./docker-entrypoint.sh"]

# Default process is the API. The worker service (see fly.toml/docker-compose.prod.yml)
# overrides this with: celery -A celery_app worker -Q default,ingestion,video --concurrency=2
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
