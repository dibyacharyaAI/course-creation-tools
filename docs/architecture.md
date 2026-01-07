# AI-Powered Course Creation & OBE Platform Architecture

## Overview
This platform is an event-driven, microservices-based system designed for Outcome-Based Education (OBE). It features AI-assisted authoring, assessment generation, and comprehensive telemetry.

## Core Characteristics
- **Event-driven, microservices-based**
- **OBE Canonical Data Model**: Course, Module, Lesson, CLO/CO/PO/PSO, etc.
- **AI-Assisted**: RAG + KG for authoring, Bloom-aware Question Generation (QG).
- **Standards Compliant**: SCORM/xAPI export + validation.
- **Telemetry**: LRS & analytics via Kafka.
- **Safety**: Human-in-the-loop (HITL) gateway.
- **Infrastructure**: Kafka backbone, Postgres canonical store, Vector DB, Object store.

## Service Groups

### 1. Course Lifecycle Management
- **Responsibilities**:
  - Super-Admin setup (programs, batches, terms, roles, regulations, PSO).
  - Definitions for Course, Module, Lesson, CLO/CO/PO/PSO.
  - Kanban workflow: Draft → Submitted → In-Review → Approved → Published.
  - In-app versioning & audit trail.

### 2. AI Generation Services
- **Authoring Service (RAG)**:
  - **MCP Router**: Centralized LLM routing.
  - **Models**: Gemini 2.5 Pro (Design), Gemini 2.5 Flash (Tutoring).
  - **RAG**: text-embedding-004 + pgvector.
  - Generates lesson drafts, handouts, Bloom tagging suggestions.
- **Assessment Service**:
  - Bloom-aligned question generation.
  - Difficulty hooks.
- **PPT/Media Service (Optional)**:
  - Slide kits, diagrams, TTS/ASR stubs.

### 3. Export & Validation
- **Internal Format**: JSON canonical OBE model.
- **Exporter**: Converts JSON to SCORM XML / xAPI packages.
- **Validator CLI**: Schema checks, link checks, basic accessibility checks.
- **LMS Adapters**: Stubbed adapters for manual download/API.

### 4. Telemetry & Analytics
- **Ingest**: SCORM summaries / xAPI statements into an LRS.
- **Transport**: Kafka topics for telemetry and KPIs.
- **Analytics**: Minimal placeholders (e.g., KPIs updated event).

### 5. HITL Gateway (Risk Control)
- **Flow**: Agent → Tool Router → HITL queue/notifications → Human Console → Decision → Resume/Abort.
- **Scope**: Data model + API interfaces (no UI).

### 6. Shared Infra & Utilities
- **Event Backbone**: Kafka.
- **Storage**:
  - Postgres (Canonical OBE + versions).
  - Vector DB (pgvector) for RAG.
  - Object Store (S3/MinIO placeholder) for artifacts.
- **Shared Libs**: Settings, logging, typing.

## Technology Stack
- **Language**: Python 3.11+
- **Web Framework**: FastAPI
- **Frontend**: React (JS UI)
- **ORM**: SQLAlchemy
- **Messaging**: Kafka
- **LLM Orchestration**: Custom MCP Router (Model Control Protocol)
- **Models**: Gemini 2.5 Pro, Gemini 2.5 Flash, text-embedding-004
- **Vector DB**: pgvector
- **Config**: Pydantic-based settings
- **Containerization**: Docker + Docker Compose
- **Testing**: pytest
