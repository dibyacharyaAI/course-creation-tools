import sys
import os
import json
import logging

# Setup Paths
sys.path.append(os.getcwd()) # For shared
sys.path.append(os.path.join(os.getcwd(), 'services/course-lifecycle'))

from app.graph_schema import CourseGraph, ModuleNode, TopicNode, SubtopicNode, SlideNode, ApprovalStatus
from app.graph.validator import GraphValidator
from app.graph.compiler import GraphCompiler
from app.pdf_builder import PDFBuilder
from app.graph_builder import GraphBuilder as CourseGraphBuilder
from app.models import Course, TopicGenerationJob

import unittest.mock

# Mock Objects matches models.py
class MockCourse:
    def __init__(self):
        self.id = 1
        self.course_graph = None
        self.course_graph_version = 1
        self.blueprint = {
            "modules": [
                {
                    "id": "m1", "title": "Module 1", 
                    "topics": [{"id": "t1", "name": "Topic 1"}]
                }
            ]
        }

class MockJob:
    def __init__(self, slides):
        self.module_id = "m1"
        self.topic_id = "t1"
        self.status = "GENERATED"
        self.slides_json = {"slides": slides}

def run_verification():
    print("--- 1. Dry Run: Topic Generation Schema Check ---")
    
    # 1. Create Dummy Slides that adhere to Schema
    # Requirement: title, bullets, speaker_notes, illustration (mapped to illustration_prompt)
    valid_slides = []
    for i in range(8): # Min 8 slides
        valid_slides.append({
            "title": f"Slide {i+1}",
            "bullets": ["Bullet 1", "Bullet 2"],
            "speaker_notes": "Notes here.",
            "illustration_prompt": "A diagram of logic.", 
            "slide_no": i+1
        })
        
    print(f"Generated {len(valid_slides)} valid mock slides.")
    
    # 2. Mock DB Objects
    course = MockCourse()
    job = MockJob(valid_slides)
    
    # 3. User GraphBuilder to transform Mock Job -> Graph
    print("Building Graph from Mock Job...")
    builder = CourseGraphBuilder(course, [job])
    graph, stats = builder.build()
    
    print(f"Graph Built: Version {graph.version}")
    
    # 4. Validate Graph (Task 4 check)
    print("Validating Graph Rules...")
    validator = GraphValidator(graph.model_dump())
    report = validator.validate()
    
    if report.valid:
        print("✅ Graph Validation PASSED (>= 8 slides, required fields present).")
    else:
        print("❌ Graph Validation FAILED:")
        for e in report.errors:
            print(f" - {e.message}")
        sys.exit(1)

    # 5. Compile to SlidePlan
    print("Compiling to SlidePlan...")
    compiler = GraphCompiler(graph.model_dump())
    plan = compiler.compile()
    
    if len(plan.slides) == 8:
        print("✅ Compiler produced correct number of slides.")
    else:
        print(f"❌ Compiler produced {len(plan.slides)} slides, expected 8.")
        sys.exit(1)

    # 6. Generate PDF Artifact (Task 4/Final Verification)
    print("Generating PDF Artifact...")
    output_path = "dry_run_handout.pdf"
    builder = PDFBuilder()
    builder.build(plan, output_path)
    
    if os.path.exists(output_path):
        print(f"✅ PDF Artifact created at: {os.path.abspath(output_path)}")
    else:
        print("❌ PDF Artifact not found.")
        sys.exit(1)

if __name__ == "__main__":
    run_verification()
