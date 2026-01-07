# Knowledge Graph Migration Plan

## 1. Current Architecture Map

### Services & Endpoints
*   **Course Lifecycle Service** (`services/course-lifecycle`)
    *   Orchestrates course creation.
    *   Stores `blueprint`, `content`, `slide_plan` in `courses` table (JSONB).
    *   *Endpoints*: `POST /courses`, `GET /courses/{id}`.
*   **AI Authoring Service** (`services/ai-authoring`)
    *   Generates content using Gemini.
    *   *Endpoints*: `POST /prompts/build`, `POST /generate-content`.
    *   *Logic*: Produces flat JSON structure for modules/lessons.
*   **Exporter Service** (`services/exporter`)
    *   Renders final artifacts (PDF, PPTX) from `courses` table.
    *   *Endpoints*: `POST /courses/{id}/export/pdf`, `POST /courses/{id}/export/pptx`.
*   **RAG Indexer** (`services/rag-indexer`)
    *   Ingests reference materials.
    *   *Endpoints*: `POST /ingest`.

### Data Storage (Postgres: `obe_platform`)
*   **Table `courses`**:
    *   `content` (JSON): The massive JSON blob containing modules, lessons, and topics. **Current interaction point.**
    *   `slide_plan` (JSON): Generated structure for slides.
    *   `blueprint` (JSON): Initial syllabus structure.
    *   `generation_spec` (JSON): User constraints.

### PPT Generation Flow (Current)
1.  **Trigger**: User requests generation or preview.
2.  **Generation**: `ai-authoring` generates `slide_plan` (JSON) based on `blueprint` + `prompt`.
3.  **Storage**: `slide_plan` stored in `Course.slide_plan`.
4.  **Rendering (Two Paths)**:
    *   *Path A (Preview)*: `ai-authoring` calls `ppt_generator.render_pptx` internally, saves to disk, updates `Course.ppt_artifact`.
    *   *Path B (Export)*: `exporter` fetches `Course.content` (for PDF) or `Course.content` (for PPT) and renders on demand.
    *   *Note*: `exporter/app/pptx_generator.py` iterates `content->modules->lessons`.

### GEMINI_API_KEY Usage
*   `services/course-lifecycle/app/settings.py` (Config)
*   `services/ai-authoring/app/main.py` (Startup check, `GeminiClient` init)
*   `services/rag-indexer/app/main.py` (Likely for embeddings, via `shared`)
*   `shared/clients/llm_client.py`: key class `GeminiFlashLiteClient` etc. uses `genai.configure(api_key=...)`.

---

## 2. Gaps to Implement KG-as-Source-of-Truth

The goal is to move from `Course.content` (JSON blob) to a granular Knowledge Graph (Nodes/Edges) that can be edited granularly and then rendered.

| Gap | Description | Severity |
| :--- | :--- | :--- |
| **No Graph Schema** | Postgres has no tables for `nodes` (Concepts/Topics) or `edges` (Relationships/Prerequisites). | **CRITICAL** |
| **Monolith JSON Dependencies** | `exporter` and `ai-authoring` read/write the full `content` JSON blob. They do not know how to query a graph. | **CRITICAL** |
| **Missing Graph API** | No service exists to perform CRUD on graph nodes (e.g., "Add subtopic", "Link concept"). | **HIGH** |
| **Duplicated Render Logic** | Rendering exists in both `ai-authoring` (for preview?) and `exporter` (for download). Both rely on the JSON shape. | **Medium** |
| **KG-to-Artifact Mapper** | We need a traversal algorithm to convert the Graph (non-linear) back into a linear `Slide Plan` or `Book Structure` (PDF) for rendering. | **HIGH** |

---

## 3. Implementation Plan

### Phase 1: Schema & Migration (P0)
**Goal**: Establish the KG structure in Postgres.

1.  **Create Tables**:
    *   `knowledge_nodes`: `id` (UUID), `course_id`, `type` (MODULE, TOPIC, CONCEPT), `title`, `content_body` (MD), `metadata` (JSON - for taxonomy, time, etc).
    *   `knowledge_edges`: `source_id`, `target_id`, `type` (PARENT_OF, PREREQUISITE_TO, NEXT_IN_FLOW).
2.  **Migration Script**:
    *   Write a script to parse existing `Course.content` JSON and populate `knowledge_nodes/edges`.

### Phase 2: KG Service & Editing (P1)
**Goal**: Allow "Edit" on the KG.

1.  **Update Lifecycle Service**:
    *   Add endpoints: `GET /courses/{id}/graph`, `PATCH /nodes/{id}`, `POST /nodes`.
2.  **Graph Logic**:
    *   Implement "Traversal" logic to fetch the "linear" view of the course from the graph (e.g., specific Edge type 'FLOW').

### Phase 3: Render from KG (P1)
**Goal**: Render outputs exclusively from KG data.

1.  **Refactor Exporter**:
    *   Modify `services/exporter/app/main.py` to `get_course_graph(course_id)` instead of `get_course_data`.
    *   Update `PPTXGenerator` and `PDFGenerator` to accept a **Linearized Graph Object** instead of the legacy `content` dict.
2.  **Deprecate JSON Blob**:
    *   Stop updating `Course.content` on edit. `Course.content` becomes a read-only snapshot or is removed.

---

## 4. Prioritized Task List

### P0: Foundation (Schema)
*   [ ] **Define Schema**: Create SQLAlchemy models for `KnowledgeNode` and `KnowledgeEdge` in `services/course-lifecycle/app/models.py`.
*   [ ] **Migration Tool**: Create `scripts/migrate_json_to_kg.py` to convert one course's JSON content to Graph rows.

### P1: Rendering Integration (The "Render Only" Goal)
*   [ ] **Graph Query**: Implement `GraphTraverser` class in `shared/core` or `exporter` to turn Nodes+Edges into a linear "Content Object" (matching the old shape or better).
*   [ ] **Update Exporter**: Switch `services/exporter` to use `GraphTraverser`.
    *   *Acceptance Criteria*: `POST /export/pdf` produces identical PDF using data fetched from `knowledge_nodes` table.

### P1.5: Editing (The "Edit" Goal)
*   [ ] **Edit API**: Implement `PATCH /api/lifecycle/nodes/{node_id}` to update text/title.
    *   *Acceptance Criteria*: Edits in DB are reflected in next Export immediately.

### P2: Cleanup
*   [ ] **Remove Redundancy**: Delete `render_pptx` from `ai-authoring` and force all previews to use `exporter` service (via internal API call).
