FROM python:3.11-slim

# Install system dependencies for WeasyPrint
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    python3-pip \
    python3-setuptools \
    python3-wheel \
    python3-cffi \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy shared libraries
COPY shared /app/shared

# Install dependencies
COPY services/exporter/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY services/exporter/app /app/app
COPY services/exporter/templates /app/templates

# Create exports directory
RUN mkdir -p /app/exports

# Set python path to include root for shared imports
ENV PYTHONPATH=/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
