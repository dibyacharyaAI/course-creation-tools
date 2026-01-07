# Deployment & Smoke Test Guide

## 1. Quick Start (Docker)

To run the full stack (Frontend, Backend, DB, Redis):

```bash
# 1. Clean verify
./scripts/clean_docker.sh

# 2. Build and Start
docker compose up --build -d

# 3. Access UI
# Open http://localhost:3000
```

## 2. Access Points

- **Frontend**: [http://localhost:3000](http://localhost:3000)
- **Backend API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Course Lifecycle Service**: [http://localhost:8000](http://localhost:8000)

## 3. Smoke Test (Manual)

1.  **Create Course**: Click "New Course", enter topic (e.g., "Python Basics").
2.  **Blueprint**: Click "Generate Blueprint", wait for syllabus, click "Next".
3.  **Graph (Step 6)**:
    -   Go to Step 6 "Review".
    -   Click "Build Graph" (should see "Sync" spinning).
    -   Verify "Topic Queue" is populated.
4.  **Edit Slide**:
    -   Select a topic.
    -   Click "Edit JSON", change a bullet point.
    -   Click "Save".
    -   Verify change persists in "Preview".
5.  **Validate**: Click "Validate" button in sidebar. Should satisfy constraints.
6.  **Approve**: Click "Approve". Check green badge and timestamp.
7.  **Export**: Click "Preview PDF". Should download PDF.

## 4. Troubleshooting

**"Graph is empty"**:
- Ensure you ran "Generate Content" for at least one topic in Step 5 (or previous steps) OR click "Sync" to pull from Blueprint structure.

**"503 Service Unavailable" on PPT**:
- The `ppt-renderer` service might be offline. Check logs: `docker compose logs ppt-renderer`.

**Logs**:
```bash
docker compose logs -f course-lifecycle
```
