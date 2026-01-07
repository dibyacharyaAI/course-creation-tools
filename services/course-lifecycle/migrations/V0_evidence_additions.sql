-- Migration V0: Evidence and Verification support
-- Apply to 'obe_platform' database

ALTER TABLE courses ADD COLUMN IF NOT EXISTS evidence_map JSONB;
ALTER TABLE courses ADD COLUMN IF NOT EXISTS verifier_report JSONB;
ALTER TABLE courses ADD COLUMN IF NOT EXISTS grounding_strictness VARCHAR(50) DEFAULT 'NORMAL';
ALTER TABLE courses ADD COLUMN IF NOT EXISTS finalization_status VARCHAR(50) DEFAULT 'DRAFT';

-- Index for querying status if needed
CREATE INDEX IF NOT EXISTS idx_courses_finalization_status ON courses(finalization_status);
