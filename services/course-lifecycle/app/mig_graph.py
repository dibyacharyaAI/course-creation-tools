from sqlalchemy import create_engine, text
from .settings import settings
import logging

logger = logging.getLogger(__name__)

def migrate():
    print(f"Connecting to {settings.DATABASE_URL}...")
    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        print("Checking for column 'course_graph' in 'courses' table...")
        
        result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='courses' AND column_name='course_graph'"))
        if result.fetchone():
            print("Column 'course_graph' already exists.")
        else:
            print("Adding column 'course_graph'...")
            conn.execute(text("ALTER TABLE courses ADD COLUMN course_graph JSONB"))
            conn.execute(text("ALTER TABLE courses ADD COLUMN course_graph_version INTEGER DEFAULT 1"))
            conn.commit()
            print("Columns added successfully.")

if __name__ == "__main__":
    migrate()
