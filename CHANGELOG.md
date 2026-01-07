# Changelog

## [Client Demo Perfect] - 2026-01-05

### Major Features
- **True Graph SoT (Single Source of Truth) - Strict Mode**:
    - **Edit Protection**: `GraphBuilder` now respects user edits (`edited_by_user` tag).
        - **Edited Slides**: Content is PRESERVED exactly during sync/rebuild.
        - **Unedited Slides**: Content updates from new Jobs (Regeneration supported).
    - **Stability**: Slide IDs are deterministic (primary = existing ID, secondary = Order). Bullet text is NEVER used for identity.
    - **Approvals**: Topic Approval status is preserved across rebuilds.

- **Safety & Compliance**:
    - **Pydantic Hardening**: Fixed multiple mutable defaults (`[]`, `{}`) in `contracts.py`, `graph_schema.py`, and `validator.py` to prevention pollution in threaded envs.
    - **Export Gates**: PPT/PDF exports now blocked (422) if topics are not APPROVED.
    - **Telemetry**: Full audit logging for Approval and Export actions.

- **UX Polish**:
    - **Step 6 Review**: Improved module/topic labels, verified badges, and inline validation.
    - **Exports**: Buttons use GET endpoints for direct download flux.

### Verification
- **New Master Script**: `scripts/verify_all.py` runs the full suite.
- **Strict Logic**: `scripts/verify_client_demo_flow.py` now exits on ANY error (Fail Fast).
- **Mixed State Test**: `scripts/verify_graph_merge_preserves_edits.py` proves granular merge (Edited slides stay, Unedited slides update).
