# Architecture Gap Analysis

## Executive Summary
**Current Status**: MVP/PoC (Phase 0.5)  
**Architecture Alignment**: ~15% Complete

We have successfully implemented a **working proof-of-concept** that demonstrates the core event-driven architecture and AI-assisted course creation flow. However, the current implementation is missing most of the OBE-specific features, governance controls, and production-ready capabilities outlined in the final architecture.

---

## ✅ What's Implemented (Working)

### 1. Core Event-Driven Architecture
- ✅ **Kafka Event Bus**: CourseCreated and ContentGenerated events
- ✅ **Microservices**: course-lifecycle, ai-authoring (functional)
- ✅ **Postgres**: Canonical Course table with status tracking

### 2. Course Lifecycle (Basic)
- ✅ **Course CRUD**: Create and retrieve courses
- ✅ **Status Tracking**: DRAFT → CONTENT_READY (2 states)
- ✅ **API**: REST endpoints for course management
- ✅ **CORS**: Enabled for frontend integration

### 3. AI Authoring (Mock)
- ✅ **Event Consumer**: Listens to CourseCreated
- ✅ **Content Generation**: Mock RAG with realistic text
- ✅ **Response**: Publishes ContentGenerated event
- ✅ **Structure**: Modules → Lessons (title + body)

### 4. Frontend UI
- ✅ **Course Creation Form**: Title + Description input
- ✅ **Real-time Status**: Polling for updates
- ✅ **Course List**: Sidebar with all created courses
- ✅ **Content Display**: Rich text rendering
- ✅ **Modern Design**: Dark theme with glassmorphism

### 5. Infrastructure
- ✅ **Docker Compose**: Postgres, Kafka, Zookeeper, Services
- ✅ **Shared Libraries**: Settings, Logging, Kafka Client, Event Schemas
- ✅ **Scaffolding**: All 6 services have basic structure

---

## ❌ What's Missing (From Architecture)

### 1. OBE Canonical Model (0% Complete)
- ❌ **CLO/CO/PO/PSO Entities**: Not defined
- ❌ **Bloom Taxonomy**: No tagging or validation
- ❌ **Weightages & Mappings**: CLO→CO, CO→PO missing
- ❌ **Domain Weights**: Knowledge/Skill/Attitude not tracked
- ❌ **Graduate Attributes**: No GA mapping

### 2. Super-Admin & Setup (0% Complete)
- ❌ **Super-Admin Wizard**: Program/Batch/Term setup missing
- ❌ **Learning Regulations**: No policy configuration
- ❌ **Role Management**: RBAC not implemented
- ❌ **Timeline Setup**: No academic calendar

### 3. Full Workflow (30% Complete)
- ⚠️ **Kanban States**: Only 2/5 states (DRAFT, CONTENT_READY)
- ❌ **Missing States**: Submitted, In-Review, Approved, Published
- ❌ **Approval Flow**: No multi-stage approval
- ❌ **Role Gates**: No Publisher/QA/Admin checks

### 4. Versioning & Audit (0% Complete)
- ❌ **In-app Versioning**: No diff/restore functionality
- ❌ **Audit Trail**: No immutable log of changes
- ❌ **Git Integration**: No Git tag mirroring
- ❌ **Provenance**: No model_id, prompt_version tracking

### 5. Assessment Service (0% Complete)
- ❌ **Bloom-aligned QG**: Not implemented
- ❌ **Difficulty Calibration**: Missing
- ❌ **Rubric Grading**: Not available
- ❌ **DKT Integration**: Not planned yet

### 6. Export & Validation (0% Complete)
- ❌ **SCORM XML Export**: Not implemented
- ❌ **xAPI Package**: Not implemented
- ❌ **Validator CLI**: No schema/link/accessibility checks
- ❌ **LMS Adapters**: No Moodle/Canvas/D2L integration

### 7. HITL Gateway (0% Complete)
- ❌ **Risk Detection**: No triggers defined
- ❌ **Approval Queue**: Not implemented
- ❌ **Human Console**: No UI
- ❌ **Decision Flow**: Resume/Abort logic missing
- ❌ **Audit**: No trace_id or decision logging

### 8. Telemetry & Analytics (0% Complete)
- ❌ **LRS Integration**: No xAPI statement ingest
- ❌ **SCORM Summaries**: Not captured
- ❌ **KPIs**: No completion %, attainment tracking
- ❌ **Dashboards**: No role-specific views
- ❌ **Scheduled Reports**: No automation

### 9. Knowledge Graph (0% Complete)
- ❌ **ArangoDB**: Not integrated
- ❌ **CO→PO Traversals**: Not available
- ❌ **GA Mapping**: Missing

### 10. Vector DB & Real RAG (0% Complete)
- ❌ **Chroma/Milvus**: Only placeholder
- ❌ **LlamaIndex**: Not integrated (using mock)
- ❌ **Embeddings**: No actual RAG retrieval
- ❌ **Context Injection**: Not implemented

### 11. Security & Compliance (0% Complete)
- ❌ **RBAC**: No role enforcement
- ❌ **Row-level Security**: Not configured
- ❌ **Vault Secrets**: Using env vars only
- ❌ **Audit Logs**: Not immutable
- ❌ **DLP**: No data loss prevention
- ❌ **2FA**: No emergency bypass

### 12. Automations (0% Complete)
- ❌ **n8n Integration**: Not planned yet
- ❌ **Scheduled Tasks**: No cron jobs
- ❌ **Batch Processing**: Missing
- ❌ **Alert System**: Not implemented

---

## 📊 Completion Matrix

| Component | Status | % Complete | Notes |
|-----------|--------|------------|-------|
| **Microservices Architecture** | ✅ Working | 80% | Structure good, missing features |
| **Kafka Event Bus** | ✅ Working | 70% | Basic events work, missing many topics |
| **Course Lifecycle** | ⚠️ Partial | 30% | CRUD works, missing workflow |
| **AI Authoring** | ⚠️ Mock | 20% | Mock works, need real RAG |
| **Assessment Service** | ❌ Scaffolded | 5% | Only health endpoint |
| **Exporter** | ❌ Scaffolded | 5% | Only health endpoint |
| **Telemetry** | ❌ Scaffolded | 5% | Only health endpoint |
| **HITL Gateway** | ❌ Scaffolded | 5% | Only health endpoint |
| **Frontend UI** | ✅ Working | 60% | Good for demo, missing admin features |
| **OBE Data Model** | ❌ Not Started | 0% | Critical gap |
| **Versioning** | ❌ Not Started | 0% | Critical gap |
| **Security/RBAC** | ❌ Not Started | 0% | Critical gap |
| **Export/SCORM** | ❌ Not Started | 0% | Critical gap |

---

## 🎯 Recommended Next Steps (Priority Order)

### Phase 1A: OBE Foundation (2-3 weeks)
1. **Define OBE Schema**: CLO, CO, PO, PSO, Bloom, Weightages
2. **Update Course Model**: Add CLO/CO mappings
3. **Super-Admin API**: Program/Batch/Term setup endpoints
4. **Bloom Validator**: Tag and validate content

### Phase 1B: Complete Workflow (1-2 weeks)
1. **Add States**: Submitted, In-Review, Approved, Published
2. **Approval API**: Multi-stage approval endpoints
3. **Role-based Gates**: Enforce RBAC on state transitions
4. **UI Updates**: Show workflow status, approval buttons

### Phase 1C: Versioning & Audit (1-2 weeks)
1. **Version Table**: Store diffs for each change
2. **Audit Log**: Immutable action log
3. **Restore API**: Rollback to previous versions
4. **UI**: Show version history

### Phase 2A: Real RAG (2-3 weeks)
1. **Integrate LlamaIndex**: Replace mock generator
2. **Setup Chroma**: Local vector DB
3. **Embedding Pipeline**: Document ingestion
4. **Context Retrieval**: Use RAG for generation

### Phase 2B: SCORM Export (2-3 weeks)
1. **JSON→XML Converter**: SCORM manifest generation
2. **Validator**: Schema + accessibility checks
3. **Package Builder**: Create .zip with assets
4. **LMS Adapter**: Moodle API integration

### Phase 2C: Telemetry (1-2 weeks)
1. **xAPI Consumer**: Ingest statements to LRS
2. **Basic KPIs**: Completion %, time metrics
3. **Dashboard**: Readonly analytics view

### Phase 3: HITL & Production Hardening (3-4 weeks)
1. **HITL Rules Engine**: Define triggers
2. **Approval Queue**: UI for human decisions
3. **Security**: Vault, RBAC, 2FA
4. **Observability**: Traces, metrics, alerts

---

## 💡 Current System's Strengths
1. **Clean Architecture**: Event-driven design is solid
2. **Working PoC**: Basic flow is functional and demoable
3. **Modern Stack**: FastAPI, Kafka, React (Tailwind) UI
4. **Scalable Base**: Easy to add new services
5. **Good Documentation**: README, getting-started guide

## ⚠️ Current System's Limitations
1. **Not OBE-aware**: Missing all OBE entities
2. **No Governance**: No approvals, versioning, or audit
3. **Mock AI**: Not using real LLMs or RAG
4. **No Export**: Can't generate SCORM packages
5. **No Analytics**: No telemetry or insights
6. **No Security**: No RBAC or access control

---

## 🎬 Conclusion

**What you have**: A working MVP that proves the architecture concept.  
**What you need**: Implement 85% of the features to match the full architecture.

**Current system is perfect for**:
- ✅ Demonstrating the event-driven flow to stakeholders
- ✅ Showing AI-assisted content generation (mock)
- ✅ Proving microservices can communicate via Kafka
- ✅ Getting buy-in for the approach

**To reach production, you must add**:
- OBE domain model (CLO/CO/PO/PSO)
- Complete workflow with approvals
- Real RAG with LlamaIndex + Vector DB
- SCORM/xAPI export
- HITL gateway
- Security & RBAC
- Analytics & dashboards

**Estimated effort to production**: 12-16 weeks (Phase 1-3 from roadmap)
