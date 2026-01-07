FROM python:3.11-slim

WORKDIR /app

# Copy shared libraries
COPY shared /app/shared

# Install dependencies
COPY services/course-lifecycle/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY services/course-lifecycle/app /app/app

# Copy data folder for seeding
# Copy minimal data structures (templates/manifests)
COPY data/templates /app/data/templates
COPY data/manifests /app/data/manifests
# COPY data/README.md /app/data/README.md

# Set python path to include root for shared imports
ENV PYTHONPATH=/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
