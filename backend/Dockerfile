# Stage 1: Base image
FROM python:3.11-slim-bookworm as base

WORKDIR /app

# Install system dependencies for PDF processing and NLP
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    poppler-utils \
    wkhtmltopdf \
    && rm -rf /var/lib/apt/lists/*

# Stage 2: Dependencies
FROM base as dependencies

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir PyMuPDF

# Download NLP models
RUN python -m spacy download de_core_news_sm && \
    python -c "import stanza; stanza.download('de')"

# Stage 3: Application
FROM dependencies as application

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/storage

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    STANZA_RESOURCES_DIR=/app/stanza_resources

EXPOSE 8000

CMD ["gunicorn", "app.main:app", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "2", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--timeout", "600", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
