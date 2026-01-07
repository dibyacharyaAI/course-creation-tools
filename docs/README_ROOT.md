# AI-Powered Course Creation & OBE Platform

## Overview
This platform is an event-driven, microservices-based system designed for Outcome-Based Education (OBE). It features AI-assisted authoring, assessment generation, and comprehensive telemetry.

## Architecture
The system is composed of the following microservices:

- **Course Lifecycle**: Manages course definitions, curriculum structure, and workflow state.
- **AI Authoring**: Generates content using RAG and LLMs.
- **Assessment**: Generates Bloom-aligned questions.
- **Exporter & Validator**: Handles SCORM/xAPI export and compliance checks.
- **Telemetry & LRS**: Ingests and processes learning analytics data.
- **HITL Gateway**: Manages human-in-the-loop workflows for AI safety.

## Infrastructure
- **Postgres**: Canonical data store.
- **Kafka**: Event backbone.
- **Docker Compose**: Local orchestration.

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+

### Running the Stack
To start the infrastructure (Postgres, Kafka) and services:

```bash
cd infra
docker-compose up --build
```

### Running a Single Service Locally
To run the `course-lifecycle` service locally:

1.  Install dependencies:
    ```bash
    pip install -r services/course-lifecycle/requirements.txt
    ```
2.  Run the server:
    ```bash
    export PYTHONPATH=$PYTHONPATH:$(pwd)
    uvicorn services.course-lifecycle.app.main:app --reload
    ```

For more detailed instructions, see [Getting Started](docs/getting-started.md).
