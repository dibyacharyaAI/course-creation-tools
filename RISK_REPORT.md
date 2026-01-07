# Risk Report (Retained Items)

The following items were identified as potential cleanup candidates but were **RETAINED** based on the "Conservative Removal" policy.

## 1. Root Scripts
- **`start.sh`**: Referenced in `TROUBLESHOOTING.md`. Likely used by developers for local startup. Removing it would break documented workflows.
- **`services/course-lifecycle/app/verify_e2e_demo.py`**: The "Gold Standard" verification script. Essential for regression testing (used in this session to verify the cleanup).

## 2. `scripts/` Directory
- **Contents**: `dev_bootstrap.sh`, `seed_courses.py`, `generate_manifest.py`, etc.
- **Reason**: While some may be unused, `dev_bootstrap.sh` and `seed_courses.py` are likely critical for new environment setup. `generate_manifest.py` suggests build automation usage. Without a deeper audit of the CI/CD pipeline, deletion carries high risk.

## 3. Inactive Services (Docker-Compose)
- **`assessment`**, **`telemetry-lrs`**, **`hitl-gateway`**:
- **Reason**: These services exist in `docker-compose.yml` (though ports are commented out). Deleting their source code (`services/assessment`, etc.) would break `docker-compose build`. They are effectively "Dark Launched" or internal microservices.

## 4. `services/exporter-validator`
- **Reason**: Mentioned in Phase 10 of `modifications_instructions.txt` ("Implement a real validation service..."). Deleting it now would hinder future implementation mandated by the plan.

## Conclusion
The repository is now cleaner (16 files + 1 major directory removed) but remains safe for development and deployment.
