# Data Pack (External)

This repository contains only minimal templates and manifests required for the application to boot. The full client data pack (raw materials, heavy PDFs/ZIPs) should be provided externally during development and deployment.

## Setup Instructions

1.  **Mount External Data**: 
    If you have the full data pack, mount it to `/app/data` in docker-compose:
    ```yaml
    volumes:
      - ./path/to/full_data:/app/data
    ```

2.  **Required Structure (Minimal)**:
    Even without the full pack, the app expects:
    - `data/templates/` : JSON templates (blueprint schemas).
    - `data/manifests/` : CSV manifests (e.g., `courses_manifest.csv`).
    - `data/generated/` : (Gitignored) Output folder for generated content.

3.  **Heavy Data (Ignored)**:
    Do not commit large files (ZIPs, PDFs, extracted folders) into `data/raw` or `data/catalog`. These are ignored by `.gitignore`.

## Folder Structure
- `raw/` : (Ignored) Place exact client-provided zips here locally.
- `catalog/` : (Partial) Project-ready organized files. Large materials are ignored.
- `templates/` : Core templates (Committed).
- `manifests/` : Core manifests (Committed).
