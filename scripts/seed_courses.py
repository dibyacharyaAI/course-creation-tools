import os
import sys
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, Text, JSON

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/obe_platform")

Base = declarative_base()

class Course(Base):
    __tablename__ = "courses"
    id = Column(Integer, primary_key=True)
    title = Column(String)
    description = Column(Text)
    course_code = Column(String)
    programme = Column(String)
    semester = Column(String)
    obe_metadata = Column(JSON)

def seed_data():
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        # Check if data exists
        if session.query(Course).count() > 0:
            logger.info("Data already exists. Skipping seed.")
            return

        # Create Courses
        courses = [
            Course(
                title="Introduction to Computer Science",
                description="Foundational concepts of computing.",
                course_code="CS101",
                programme="B.Tech",
                semester="1",
                obe_metadata={
                    "modules": [
                        {"id": 1, "name": "Basics of Programming"},
                        {"id": 2, "name": "Data Structures"}
                    ]
                }
            ),
            Course(
                title="Advanced Machine Learning",
                description="Deep learning and neural networks.",
                course_code="CS402",
                programme="B.Tech",
                semester="7",
                obe_metadata={
                    "modules": [
                        {"id": 3, "name": "Neural Networks"},
                        {"id": 4, "name": "Transformers"}
                    ]
                }
            ),
             Course(
                title="Water Supply Engineering",
                description="Water treatment and distribution systems.",
                course_code="CE301",
                programme="B.Tech",
                semester="5",
                obe_metadata={
                    "modules": [
                        {"id": 5, "name": "Water Quality"},
                        {"id": 6, "name": "Treatment Processes"}
                    ]
                }
            )
        ]

        session.add_all(courses)
        session.commit()
        logger.info("✅ Seeded initial courses successfully.")

    except Exception as e:
        logger.error(f"Seeding failed: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    seed_data()
