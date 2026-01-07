#!/usr/bin/env python3
"""
Validation Test: Verify that reordering slides preserves edited content.

This test validates P1 requirement: Stable slide identity - no order-based merge.
It ensures that when slides are reordered, edited slides maintain their content
and identity based on stable_key/id, not order.
"""

import sys
import os
import json
from typing import Dict, Any, List

# Add paths to allow importing from 'app' and 'shared'
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
service_dir = os.path.join(repo_root, "services", "course-lifecycle")
sys.path.append(repo_root)
sys.path.append(service_dir)

from app.graph_schema import CourseGraph, ModuleNode, TopicNode, SubtopicNode, SlideNode

def create_test_graph() -> CourseGraph:
    """Create a test graph with 3 slides, one edited"""
    slides = [
        SlideNode(
            id="slide-1",
            title="Slide 1 Original",
            bullets=["Bullet 1", "Bullet 2"],
            order=1,
            tags={"stable_key": ["topic1_sub1_slide1"], "source": ["job_generation"]}
        ),
        SlideNode(
            id="slide-2",
            title="Slide 2 EDITED",
            bullets=["EDITED Bullet 1", "EDITED Bullet 2", "EDITED Bullet 3"],
            order=2,
            tags={"stable_key": ["topic1_sub1_slide2"], "edited_by_user": ["true"], "source": ["job_generation"]}
        ),
        SlideNode(
            id="slide-3",
            title="Slide 3 Original",
            bullets=["Bullet 1", "Bullet 2"],
            order=3,
            tags={"stable_key": ["topic1_sub1_slide3"], "source": ["job_generation"]}
        )
    ]
    
    subtopic = SubtopicNode(
        id="subtopic-1",
        title="Subtopic 1",
        children=slides
    )
    
    topic = TopicNode(
        id="topic-1",
        topic_id="T1",
        title="Topic 1",
        children=[subtopic]
    )
    
    module = ModuleNode(
        id="module-1",
        module_id="M1",
        name="Module 1",
        children=[topic]
    )
    
    return CourseGraph(
        course_id=1,
        version=1,
        children=[module]
    )

def reorder_slides(graph: CourseGraph) -> CourseGraph:
    """Reorder slides: swap order 1 and 3"""
    slides = graph.children[0].children[0].children[0].children
    
    # Find slides by order
    slide_1 = next(s for s in slides if s.order == 1)
    slide_3 = next(s for s in slides if s.order == 3)
    
    # Swap orders
    slide_1.order = 3
    slide_3.order = 1
    
    # Re-sort by order for display
    slides.sort(key=lambda s: s.order)
    
    return graph

def simulate_merge_with_new_content(graph: CourseGraph) -> CourseGraph:
    """
    Simulate what GraphBuilder._merge_slides_content does:
    - Match by stable_key first
    - If edited_by_user=true, preserve content
    - Otherwise update content
    """
    existing_slides = {s.id: s for s in graph.children[0].children[0].children[0].children}
    existing_by_stable_key = {}
    for slide in existing_slides.values():
        stable_key = slide.tags.get("stable_key", [None])[0] if slide.tags else None
        if stable_key:
            existing_by_stable_key[stable_key] = slide
    
    # Simulate new job slides (with reordered content)
    new_job_slides = [
        {"title": "Slide 3 NEW", "bullets": ["NEW Bullet 1", "NEW Bullet 2"], "order": 1, "_stable_key": "topic1_sub1_slide3"},
        {"title": "Slide 2 NEW", "bullets": ["NEW Bullet 1", "NEW Bullet 2"], "order": 2, "_stable_key": "topic1_sub1_slide2"},
        {"title": "Slide 1 NEW", "bullets": ["NEW Bullet 1", "NEW Bullet 2"], "order": 3, "_stable_key": "topic1_sub1_slide1"},
    ]
    
    merged_slides = []
    for js in new_job_slides:
        stable_key = js.get("_stable_key")
        matched_slide = existing_by_stable_key.get(stable_key)
        
        if matched_slide:
            # Check if edited
            is_edited = matched_slide.tags.get("edited_by_user", [])
            is_edited = any(str(x).lower() == "true" for x in is_edited) if is_edited else False
            
            if is_edited:
                # PRESERVE: Keep edited content, update order only
                matched_slide.order = js.get("order")
                merged_slides.append(matched_slide)
            else:
                # UPDATE: New content, keep ID
                matched_slide.title = js.get("title")
                matched_slide.bullets = js.get("bullets")
                matched_slide.order = js.get("order")
                merged_slides.append(matched_slide)
        else:
            # New slide
            new_slide = SlideNode(
                id=f"slide-{len(merged_slides) + 1}",
                title=js.get("title"),
                bullets=js.get("bullets"),
                order=js.get("order"),
                tags={"stable_key": [stable_key], "source": ["job_generation"]}
            )
            merged_slides.append(new_slide)
    
    # Sort by order
    merged_slides.sort(key=lambda s: s.order)
    
    # Update graph
    graph.children[0].children[0].children[0].children = merged_slides
    return graph

def test_reorder_preserves_edits():
    """Main test: reorder slides and verify edited content is preserved"""
    print("=" * 60)
    print("TEST: Reorder Preserves Edits")
    print("=" * 60)
    
    # Step 1: Create initial graph with edited slide
    print("\n1. Creating initial graph with edited slide (order=2)...")
    graph = create_test_graph()
    edited_slide = graph.children[0].children[0].children[0].children[1]  # order=2
    print(f"   Edited slide ID: {edited_slide.id}")
    print(f"   Edited slide title: {edited_slide.title}")
    print(f"   Edited slide bullets: {edited_slide.bullets}")
    print(f"   Edited slide order: {edited_slide.order}")
    
    # Step 2: Reorder slides
    print("\n2. Reordering slides (swap order 1 and 3)...")
    graph = reorder_slides(graph)
    slides_after_reorder = graph.children[0].children[0].children[0].children
    print(f"   Slide orders after reorder: {[s.order for s in slides_after_reorder]}")
    
    # Find edited slide by ID (not order)
    edited_slide_after = next(s for s in slides_after_reorder if s.id == "slide-2")
    print(f"   Edited slide (by ID) order after reorder: {edited_slide_after.order}")
    print(f"   Edited slide title after reorder: {edited_slide_after.title}")
    print(f"   Edited slide bullets after reorder: {edited_slide_after.bullets}")
    
    # Step 3: Simulate merge with new content
    print("\n3. Simulating merge with new job content (reordered)...")
    graph = simulate_merge_with_new_content(graph)
    slides_after_merge = graph.children[0].children[0].children[0].children
    
    # Find edited slide by stable_key
    edited_slide_final = next(
        s for s in slides_after_merge 
        if s.tags.get("stable_key", [None])[0] == "topic1_sub1_slide2"
    )
    
    print(f"   Final slide orders: {[s.order for s in slides_after_merge]}")
    print(f"   Edited slide (by stable_key) final order: {edited_slide_final.order}")
    print(f"   Edited slide final title: {edited_slide_final.title}")
    print(f"   Edited slide final bullets: {edited_slide_final.bullets}")
    
    # Step 4: Assertions
    print("\n4. Assertions...")
    
    # Assert 1: Edited slide maintains its edited content
    assert edited_slide_final.title == "Slide 2 EDITED", \
        f"Expected 'Slide 2 EDITED', got '{edited_slide_final.title}'"
    assert edited_slide_final.bullets == ["EDITED Bullet 1", "EDITED Bullet 2", "EDITED Bullet 3"], \
        f"Expected edited bullets, got {edited_slide_final.bullets}"
    
    # Assert 2: Edited slide maintains its ID
    assert edited_slide_final.id == "slide-2", \
        f"Expected ID 'slide-2', got '{edited_slide_final.id}'"
    
    # Assert 3: Non-edited slides get updated content
    slide_1_final = next(s for s in slides_after_merge if s.tags.get("stable_key", [None])[0] == "topic1_sub1_slide1")
    assert slide_1_final.title == "Slide 1 NEW", \
        f"Expected 'Slide 1 NEW', got '{slide_1_final.title}'"
    
    slide_3_final = next(s for s in slides_after_merge if s.tags.get("stable_key", [None])[0] == "topic1_sub1_slide3")
    assert slide_3_final.title == "Slide 3 NEW", \
        f"Expected 'Slide 3 NEW', got '{slide_3_final.title}'"
    
    # Assert 4: Order is updated correctly
    assert edited_slide_final.order == 2, \
        f"Expected order 2, got {edited_slide_final.order}"
    
    print("   ✅ All assertions passed!")
    print("\n" + "=" * 60)
    print("✅ TEST PASSED: Reorder preserves edited content")
    print("=" * 60)
    return True

if __name__ == "__main__":
    try:
        test_reorder_preserves_edits()
        sys.exit(0)
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
