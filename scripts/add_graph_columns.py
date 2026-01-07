import sys
import os
from sqlalchemy import create_engine, text

# Add paths to allow importing from 'app' and 'shared'
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
service_dir = os.path.join(repo_root, "services", "course-lifecycle")

sys.path.append(repo_root) # For 'shared'
sys.path.append(service_dir) # For 'app'

from app.settings import settings

def migrate():
    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        print("Checking for column 'course_graph' in 'courses' table...")
        
        # Check if column exists
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
