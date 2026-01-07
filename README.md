# OBE Course Generation Platform

A comprehensive platform for generating Outcome-Based Education (OBE) course content using Agentic AI and Knowledge Graphs.

## Requirements
- Docker Desktop (active)
- Node.js 18+ (for local frontend dev)
- Python 3.11+ (for local service dev)

## Quick Start
1.  **Clone** the repository.
2.  **Environment**: Copy `env.example` to `.env` and fill in `GEMINI_API_KEY`.
    ```bash
    cp .env.example .env
    ```
3.  **Data Pack**:
    - The repository includes minimal templates.
    - If you have the full client data pack (Raw Materials), place it in a `data` folder at the root.
4.  **Run**:
    ```bash
    docker compose up --build
    ```
5.  **Access**:
    - Frontend: http://localhost:3000
    - API Docs: http://localhost:8000/docs

## Architecture
- **Services**:
    - `course-lifecycle`: Core logic for courses, blueprints, and KG orchestration.
    - `ai-authoring`: LLM-based content generation.
    - `rag-indexer`: Ingestion and retrieval of course materials.
    - `ppt-renderer`: Converts JSON slides to PPTX.
- **Frontend**: React + Vite application.
- **Infra**: Postgres (DB), Kafka (Events), Redis (Queue).

## Contributing
See [CONTRIBUTING.md](CONTRIBUTING.md) for details.
