# Getting Started

## Environment Setup

1.  **Clone the repository**
2.  **Install Docker and Docker Compose**
3.  **Python 3.11+** is required for local development.

## Configuration

Copy the example environment file (if available) or create a `.env` file in the service directory you are working on.
Shared settings are loaded from `shared/core/settings.py`.

## Running with Docker Compose

To bring up the entire stack (Postgres, Kafka, and eventually services):

```bash
cd infra
docker-compose up --build
```

## Local Development

To run a specific service (e.g., `course-lifecycle`) locally:

1.  Navigate to the repo root.
2.  Install dependencies:
    ```bash
    pip install -r services/course-lifecycle/requirements.txt
    ```
3.  Run the service:
    ```bash
    export PYTHONPATH=$PYTHONPATH:$(pwd)
    uvicorn services.course-lifecycle.app.main:app --reload
    ```

## Project Structure

- `docs/`: Architecture and guides.
- `infra/`: Docker and Kubernetes config.
- `services/`: Microservices source code.
- `shared/`: Shared libraries (DB, Logging, Clients).
- `scripts/`: Utility scripts.
