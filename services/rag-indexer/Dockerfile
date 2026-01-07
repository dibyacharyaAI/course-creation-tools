# Use official python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/rag-indexer/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared code
COPY shared /app/shared

# Copy app code
COPY services/rag-indexer/app /app/app

# Set python path
ENV PYTHONPATH=/app

# Command to run the indexer script
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
