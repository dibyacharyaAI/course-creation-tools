FROM python:3.11-slim

WORKDIR /app

# Copy shared libraries
COPY shared /app/shared

# Install dependencies
COPY services/exporter-validator/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY services/exporter-validator/app /app/app

# Set python path to include root for shared imports
ENV PYTHONPATH=/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
