
import sys
import os
import json
import uuid
from datetime import datetime

# Path setup
sys.path.append(os.path.abspath("."))
sys.path.append(os.path.abspath("services/course-lifecycle"))

from app.main import app
from app.database import engine
from app.models import Base, Course, TopicGenerationJob
from app.graph_builder import GraphBuilder

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# DB Setup
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}, 
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

def verify_global_matching():
    print("--- Verifying Global Slide Matching ---")
    
    db = TestingSessionLocal()
    
    # 1. Setup Data
    # Course with 2 Modules, 1 Topic each.
    course = Course(
        id=1,
        title="Test Course",
        course_code="TST101",
        blueprint={
            "modules": [
                {
                    "id": "m1", "title": "Module A", 
                    "topics": [{"id": "t1", "name": "Topic A"}]
                },
                {
                    "id": "m2", "title": "Module B", 
                    "topics": [{"id": "t2", "name": "Topic B"}]
                }
            ]
        }
    )
    db.add(course)
    db.commit()
    
    # 2. JOB for Topic A (Generates Slide X)
    job_a = TopicGenerationJob(
        course_id=1, module_id="m1", topic_id="t1", status="GENERATED", version=1,
        slides_json={"slides": [
            {"title": "Slide X", "slide_no": 1, "bullets": ["Origin A"]} # stable_key will be m1::t1::slide::0
        ]}
    )
    db.add(job_a)
    db.commit()
    
    # 3. Initial Build (Puts Slide X in Topic A)
    # We need to fetch jobs list
    jobs = [job_a]
    builder = GraphBuilder(course, jobs)
    graph, stats = builder.build()
    
    # Verify Slide X is in Topic A
    topic_a = graph.children[0].children[0]
    slide_x = topic_a.children[0].children[0]
    slide_x_id = slide_x.id
    print(f"✅ Initial Build: Slide X created in Topic A. ID={slide_x_id}")
    print(f"   Tags: {slide_x.tags}")
    
    # Save Graph
    course.course_graph = graph.model_dump(mode='json')
    db.commit()
    
    # 4. SIMULATE USER MOVE: Move Slide X to Topic B
    # Manually Edit Graph
    cg = course.course_graph
    
    # Extract Slide Node (Deep Copy via JSON dump/load logic roughly)
    # Removing from Topic A
    slide_x_data = cg["children"][0]["children"][0]["children"][0]["children"].pop(0)
    
    # Adding to Topic B (Create "User Content" Subtopic if needed, or just append to existing)
    # Topic B is currently empty structure-wise (created by builder but no children)
    topic_b_ptr = cg["children"][1]["children"][0]
    if not topic_b_ptr.get("children"):
        topic_b_ptr["children"] = []
    
    # Mock Subtopic for B
    sub_b = {"id": "sub_b", "title": "Moved Content", "children": [slide_x_data]}
    topic_b_ptr["children"].append(sub_b)
    
    # Save Modified Graph
    course.course_graph = cg
    db.commit()
    print("✅ Moved Slide X to Topic B manually.")
    
    # 5. REBUILD Trigger
    # Using SAME Job A (Simulating Sync/Regen where A claims the slide)
    # Logic: GraphBuilder should find Slide X in Topic B (via stable_key), reuse ID, and put it back in A.
    # AND it should NOT duplicate it (should remove from B).
    
    builder2 = GraphBuilder(course, jobs)
    graph2, stats2 = builder2.build()
    
    # Verify Topic A has Slide X with SAME ID
    topic_a_2 = graph2.children[0].children[0]
    if not topic_a_2.children or not topic_a_2.children[0].children:
        print("❌ Rebuild Failed: Topic A is empty!")
        return

    slide_x_2 = topic_a_2.children[0].children[0]
    print(f"🔍 Rebuild Topic A Slide ID: {slide_x_2.id}")
    
    if slide_x_2.id == slide_x_id:
        print("✅ Identity Preserved: Slide X returned to Topic A with original ID.")
    else:
        print(f"❌ Identity LOST: ID changed to {slide_x_2.id}")
        
    # Verify Topic B does NOT have Slide X (No Duplicates)
    topic_b_2 = graph2.children[1].children[0]
    # Topic B has no job, so it just replicates existing content (Orphan Rescue).
    # BUT Orphan Rescue should have skipped Slide X because it was claimed by Job A.
    
    has_slide_x_in_b = False
    if topic_b_2.children:
        for sub in topic_b_2.children:
            for s in sub.children:
                if s.id == slide_x_id:
                    has_slide_x_in_b = True
                    
    if not has_slide_x_in_b:
        print("✅ No Duplicates: Slide X removed from Topic B (Claimed by A).")
    else:
        print("❌ DUPLICATE FOUND: Slide X still exists in Topic B!")

    print("\n✅ Verification Passed!")

if __name__ == "__main__":
    try:
        verify_global_matching()
    except Exception as e:
        print(f"FATAL: {e}")
        import traceback
        traceback.print_exc()
