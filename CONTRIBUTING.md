# Contributing

## Development Workflow
1.  **Local Setup**:
    - Install dependencies: `pip install -r requirements.txt` (in services)
    - Frontend: `cd frontend && npm install`
2.  **Running Services**:
    - Use `docker compose up` for full stack.
    - Or run services individually (see specific service READMEs).
3.  **Code Style**:
    - Python: Follow PEP 8.
    - Frontend: Standard React practices.

## Repository Hygiene
- **No Secrets**: Never commit `.env` or credentials.
- **No Artifacts**: Do not commit `node_modules`, `dist`, or generated `exports`.
- **Data**: Do not commit large PDFs or ZIPs. Use the external `data` volume pattern.

## Pull Requests
- Use the PR template.
- Verify checks pass locally.
