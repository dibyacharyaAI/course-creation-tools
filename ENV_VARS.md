# Environment Variables

This project relies on the following environment variables. Ensure they are set in your `.env` file (which should NOT be committed).

## Global
- `GEMINI_API_KEY`: **Required**. API Key for Google Gemini LLM. Used for syllabus extraction, content generation, and embeddings. Get one at [aistudio.google.com](https://aistudio.google.com/).

## Service Specific

### `course-lifecycle`
- `DATABASE_URL`: Connection string for PostgreSQL (e.g., `postgresql://user:password@postgres:5432/obe_platform`).
- `KAFKA_BOOTSTRAP_SERVERS`: Kafka address (e.g., `kafka:29092`).
- `RAG_INDEXER_URL`: URL for the RAG Indexer service (e.g., `http://rag-indexer:8000`).
- `PPT_RENDERER_URL`: URL for the PPT Renderer service (e.g., `http://ppt-renderer:3000/render`).

### `ai-authoring`
- `GEMINI_API_KEY`: **Required**.
- `DATABASE_URL`: Connection string.
- `KAFKA_BOOTSTRAP_SERVERS`: Kafka address.
- `PPT_RENDERER_URL`: URL for the PPT Renderer service.
- `RAG_INDEXER_URL`: URL for the RAG Indexer service.

### `rag-indexer`
- `GEMINI_API_KEY`: **Required**.
- `DATABASE_URL`: Connection string (PostgreSQL with pgvector).
- `ENABLE_OCR`: Set to `true` to enable OCR fallback for scanned PDFs.
- `DEEPSEEK_API_KEY`: API Key for DeepSeek OCR (Required if `ENABLE_OCR=true`).

### `infra` (Docker Compose)
- `GEMINI_API_KEY`: Passed through to containers via `.env` file in `infra/` or root.

## Setup
1. Copy `.env.example` to `.env` (if available, otherwise create `.env`).
2. Add your keys:
   ```bash
   GEMINI_API_KEY=YOUR_KEY_HERE
   ```
3. Never commit `.env` to version control.
