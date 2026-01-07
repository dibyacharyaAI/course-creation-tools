# Deletion Report
**Date:** 2025-12-24
**Executor:** Antigravity (Refactor Engineer)

The following files and directories were removed from the repository. All removals were verified to have zero active references in the codebase (excluding self-references or references in other deleted files).

## 1. Unused Services
- **`services/frontend`**: Confirmed duplicate of root `/frontend`. Contained a stale `Dockerfile` (nginx based) while the active frontend uses Node/Vite. Usage confirmed via `docker-compose.yml` which points to `../frontend`.

## 2. Obsolete Verification Scripts
- **`verify_demo_patch.py`**: Superseded by `verify_e2e_demo.py`.
- **`verify_fix_create_course.py`**: Validated fix for a resolved bug. Redundant.
- **`verify_phases.py`**: Legacy script, no longer referenced.
- **`verify_prompt_builder.py`**: Legacy script, no longer referenced.
- **`verify_real_rag.py`**: Legacy script, no longer referenced.
- **`check_db_schema.py`**: One-off diagnostic script.
- **`fix_db_schema.py`**: One-off fix script (fixes integrated into migration/setup).
- **`dump_evidence_slide.py`**: Unused debug tool.
- **`extract_syllabus.py`**: Unused debug tool.
- **`list_models.py`**: Unused debug tool.
- **`generate_ppt_json.py`**: Unused debug tool.

## 3. Temporary Artifacts & Logs
- **`verify_payload.json`**: Temporary test payload.
- **`openapi_dump.json`**: Temporary schema dump.
- **`ai_auth.log`**: Runtime log file.
- **`lifecycle.log`**: Runtime log file.
- **`debug.sh`**: Ad-hoc debug script.
- **`fix_frontend.sh`**: One-off fix script.

## Verification
Post-deletion, the system was verified using `services/course-lifecycle/app/verify_e2e_demo.py` (running inside the container), which passed all checks for the core Content Creation Flow (Course -> Blueprint -> Prompt -> Artifacts).
