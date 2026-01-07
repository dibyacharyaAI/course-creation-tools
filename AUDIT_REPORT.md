# Repository Audit Report

## 1. Architecture & Port Compliance
- **Requirement**: SINGLE EXTERNAL PORT (User opens one URL).
- **Finding**:
    - `infra/docker-compose.yml` defines `gateway` service causing port 3000 to be exposed.
    - `postgres`, `kafka`, and other backend services have no host port mappings. **COMPLIANT**.
    - `frontend` service is internal.
    - `gateway` (Nginx) proxies `/` to `frontend:3000` and `/api/*` to respective backend services. **COMPLIANT**.
- **Action**: No architectural changes needed for port mappings.

## 2. Frontend Configuration
- **Unreachable / White Page Risk**:
    - `frontend/vite.config.js` sets `server: { port: 3000 }` and `hmr: { clientPort: 3000 }`. This is correct for gateway access on port 3000.
    - `frontend/Dockerfile` uses `npm run dev -- --host`, exposing it on 0.0.0.0. **correct**.
    - `src/api/client.js` uses relative paths (`/api/lifecycle`, etc.) which correctly route through Nginx. **COMPLIANT**.

## 3. Phase 1 & 2 Feature Status
- **Phase 1 (Syllabus -> Blueprint)**:
    - Endpoints in `course-lifecycle` need verification (`/syllabus/templates`, `/syllabus/upload`). I will verify their existence in code.
    - Frontend `Step1Selection` and `Step2Blueprint` generally exist.
- **Phase 2 (Input -> Final)**:
    - **Scope Tagging**: `Step3References.jsx` implements Scope (Course/Module/Topic) selection. **PARTIALLY IMPLEMENTED**.
    - **Prompt Builder**: `Step5Prompt.jsx` (based on file list mapping) needs verification.
    - **HITL Integration**: `approvePPT` in `client.js` calls `/ppt/approve_v2`. Need to verify backend handler.

## 4. Missing / Risks
- **Frontend Stability**: "White page" reports suggest runtime crashes. I will wrap the main App or Steps in an `ErrorBoundary` to prevent full crash.
- **Data1 Loader**: Need to verify `catalog_loader.py` correctly loads `manifest.json`.
- **RAG Filters**: Need to verify if `ai-authoring` or `rag-indexer` respects the scope tags sent by frontend.

## 5. Next Steps
1.  Implement `ErrorBoundary` in Frontend.
2.  Verify and fix `catalog_loader.py`.
3.  End-to-End verify the flow.
