# Scoratis Backend Dockerfile
# Python FastAPI with sentence-transformers for embeddings (GPU-enabled)
# Includes Manim for video generation

FROM pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime

# Set working directory
WORKDIR /app

# Install system dependencies including Manim requirements and scipy build deps
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
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for layer caching
COPY requirements.txt .

# Install Python dependencies
# sentence-transformers will use the pre-installed torch from base image
RUN pip install --no-cache-dir -r requirements.txt

# Install duckduckgo-search for web search
RUN pip install --no-cache-dir duckduckgo-search==4.1.1

# Install Manim and video generation dependencies
RUN pip install --no-cache-dir manim>=0.18.0 pydub>=0.25.0 ffmpeg-python>=0.2.0

# Pre-download the embedding model during build
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
