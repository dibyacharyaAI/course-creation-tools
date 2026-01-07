from typing import List, Dict, Optional, Any
import logging
from ..graph_schema import CourseGraph, ModuleNode, TopicNode, SubtopicNode, SlideNode
from ..contracts import SlideStructure, SlideContent

logger = logging.getLogger(__name__)

class GraphCompiler:
    def __init__(self, course_graph: Dict[str, Any]):
        self.graph = CourseGraph(**course_graph)
    
    def compile(self, topic_id: Optional[str] = None) -> SlideStructure:
        """
        Compiles Graph to SlidePlan.
        If topic_id is provided, scopes to that topic.
        Otherwise compiles full course.
        """
        all_slides: List[SlideContent] = []
        
        for module in self.graph.children:
            # Add Module Title Slide?
            if not topic_id:
                # Optional: Add module intro slide if full course export
                pass
            
            for topic in module.children:
                # Check scope
                if topic_id and (topic.topic_id != topic_id and topic.id != topic_id):
                    continue
                
                # Add content
                for subtopic in topic.children:
                    for slide in subtopic.children:
                        # Map SlideNode to SlideContent contract
                        content = SlideContent(
                            id=slide.id,
                            title=slide.title,
                            bullets=slide.bullets,
                            speaker_notes=slide.speaker_notes,
                            illustration_prompt=slide.illustration_prompt,
                            topic_id=topic.topic_id or topic.id,
                            subtopic_id=subtopic.id,
                            tags=slide.tags
                        )
                        all_slides.append(content)
                
                if topic_id: break # Found specific topic
            
            if topic_id and all_slides: break # Stop if found
            
        return SlideStructure(slides=all_slides)
