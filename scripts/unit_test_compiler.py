import unittest
import sys
import os

# Fix paths for hyphenated dir import
sys.path.append(os.path.join(os.getcwd(), 'services/course-lifecycle'))

from app.graph_schema import CourseGraph, ModuleNode, TopicNode, SubtopicNode, SlideNode
from app.graph.compiler import GraphCompiler

# Helpers
def create_slide(id="s1", title="Title"):
    return SlideNode(
        id=id,
        title=title,
        bullets=["b1"],
        speaker_notes="notes",
        illustration_prompt="prompt",
        order=1
    )

class TestGraphCompiler(unittest.TestCase):
    def setUp(self):
        self.slides_t1 = [create_slide("t1_s1", "Topic 1 Slide 1")]
        self.slides_t2 = [create_slide("t2_s1", "Topic 2 Slide 1")]
        
        self.graph = CourseGraph(
            course_id=1,
            children=[
                ModuleNode(id="m1", name="Module 1", children=[
                    TopicNode(
                        id="t1", 
                        title="Topic 1", 
                        children=[SubtopicNode(id="st1", title="Sub", children=self.slides_t1)]
                    ),
                    TopicNode(
                        id="t2", 
                        title="Topic 2", 
                        children=[SubtopicNode(id="st2", title="Sub", children=self.slides_t2)]
                    )
                ])
            ]
        )
        self.compiler = GraphCompiler(self.graph.dict())

    def test_full_compile(self):
        plan = self.compiler.compile(topic_id=None)
        self.assertEqual(len(plan.slides), 2)
        self.assertEqual(plan.slides[0].title, "Topic 1 Slide 1")
        self.assertEqual(plan.slides[1].title, "Topic 2 Slide 1")

    def test_topic_scope_compile(self):
        plan = self.compiler.compile(topic_id="t2")
        self.assertEqual(len(plan.slides), 1)
        self.assertEqual(plan.slides[0].title, "Topic 2 Slide 1")

    def test_unknown_topic(self):
        plan = self.compiler.compile(topic_id="unknown")
        self.assertEqual(len(plan.slides), 0)

if __name__ == '__main__':
    unittest.main()
