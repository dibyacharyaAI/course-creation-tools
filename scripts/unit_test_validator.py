import unittest
import sys
import os

# Fix paths for hyphenated dir import
sys.path.append(os.path.join(os.getcwd(), 'services/course-lifecycle'))

from app.graph_schema import CourseGraph, ModuleNode, TopicNode, SubtopicNode, SlideNode
from app.graph.validator import GraphValidator, ValidationReport

# Helpers to build graph nodes
def create_slide(id="s1", title="Title", bullets=["b1"], illustration="prompt"):
    return SlideNode(
        id=id,
        title=title,
        bullets=bullets,
        speaker_notes="notes",
        illustration_prompt=illustration,
        order=1
    )

class TestGraphValidator(unittest.TestCase):
    def test_valid_graph(self):
        # Create a topic with 8 slides (min req)
        slides = [create_slide(id=f"s{i}") for i in range(8)]
        
        graph = CourseGraph(
            course_id=1,
            children=[
                ModuleNode(id="m1", name="Module 1", children=[
                    TopicNode(
                        id="t1", 
                        title="Topic 1", 
                        children=[
                            SubtopicNode(id="st1", title="Sub", children=slides)
                        ]
                    )
                ])
            ]
        )
        
        validator = GraphValidator(graph.dict())
        report = validator.validate()
        self.assertTrue(report.valid)
        self.assertEqual(len(report.errors), 0)

    def test_insufficient_slides(self):
        # Topic with 1 slide
        slides = [create_slide()]
        graph = CourseGraph(
            course_id=1,
            children=[
                ModuleNode(id="m1", name="Module 1", children=[
                    TopicNode(
                        id="t1", 
                        title="Topic 1", 
                        children=[
                            SubtopicNode(id="st1", title="Sub", children=slides)
                        ]
                    )
                ])
            ]
        )
        validator = GraphValidator(graph.dict())
        report = validator.validate()
        self.assertFalse(report.valid)
        self.assertTrue(any("minimum 8 required" in e.message for e in report.errors))

    def test_missing_content(self):
        # Slide missing title and illustration
        bad_slide = create_slide(title="", illustration="")
        # Need 8 slides to pass slide count check, but one bad one to fail content check
        slides = [create_slide(id=f"ok{i}") for i in range(7)] + [bad_slide]
        
        graph = CourseGraph(
            course_id=1,
            children=[
                ModuleNode(id="m1", name="Module 1", children=[
                    TopicNode(
                        id="t1", 
                        title="Topic 1", 
                        children=[
                            SubtopicNode(id="st1", title="Sub", children=slides)
                        ]
                    )
                ])
            ]
        )
        validator = GraphValidator(graph.dict())
        report = validator.validate()
        self.assertFalse(report.valid)
        self.assertTrue(any("missing title" in e.message for e in report.errors))
        self.assertTrue(any("missing illustration" in e.message for e in report.errors))

if __name__ == '__main__':
    unittest.main()
