from sqlalchemy import text
from app.main import engine, logger

def migrate_telemetry():
    with engine.connect() as conn:
        logger.info("⚡ Running Telemetry & HITL Migration...")
        
        # 1. Add columns to topic_generation_jobs if missing
        # We need check if columns exist first to avoid errors
        # Simplified: We attempt ADD COLUMN and ignore failure if exists (or check info schema)
        
        # Check 'approval_status'
        res = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='topic_generation_jobs' AND column_name='approval_status'"))
        if not res.fetchone():
            logger.info("Adding HITL columns to topic_generation_jobs...")
            conn.execute(text("ALTER TABLE topic_generation_jobs ADD COLUMN approval_status VARCHAR DEFAULT 'PENDING'"))
            conn.execute(text("ALTER TABLE topic_generation_jobs ADD COLUMN approved_at TIMESTAMP WITH TIME ZONE"))
            conn.execute(text("ALTER TABLE topic_generation_jobs ADD COLUMN reviewer_id VARCHAR"))
            conn.execute(text("ALTER TABLE topic_generation_jobs ADD COLUMN rejection_reason TEXT"))
            conn.commit()

        # 2. Create JobRuns table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS job_runs (
                id SERIAL PRIMARY KEY,
                course_id INTEGER,
                topic_id VARCHAR,
                job_type VARCHAR, -- GENERATE, BUILD, VALIDATE, EXPORT
                status VARCHAR, -- RUNNING, COMPLETED, FAILED
                started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                ended_at TIMESTAMP WITH TIME ZONE,
                duration_ms INTEGER,
                error_details TEXT
            )
        """))
        conn.commit()
        
        # 3. Create AuditEvents table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS audit_events (
                id SERIAL PRIMARY KEY,
                course_id INTEGER,
                topic_id VARCHAR,
                action VARCHAR, -- APPROVE, REJECT, MODIFY
                actor_id VARCHAR,
                comment TEXT,
                timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """))
        conn.commit()
        logger.info("✅ Telemetry & HITL Migration Complete.")

if __name__ == "__main__":
    migrate_telemetry()
