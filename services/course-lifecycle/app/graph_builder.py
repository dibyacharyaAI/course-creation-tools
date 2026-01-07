from typing import List, Dict, Optional, Any
import logging
from .graph_schema import CourseGraph, ModuleNode, TopicNode, SubtopicNode, SlideNode, ApprovalStatus
from .models import Course, TopicGenerationJob
from .concept_extractor import ConceptExtractor
import uuid

logger = logging.getLogger(__name__)

class GraphBuilder:
    """
    Builds the CourseGraph structure deterministically from Blueprint.
    Implements STRICT MERGE:
    - Existing graph nodes are preserved (ID, approval, manual edits).
    - New content from Jobs is merged in only if node is missing.
    - Deterministic ID generation for stability.
    """
    def __init__(self, course: Course, topic_jobs: List[TopicGenerationJob]):
        self.course = course
        # Source of Truth for *generated* content is the Job
        # But Source of Truth for *structure/state* is the Graph (if exists)
        self.jobs_map = {
            f"{j.module_id}::{j.topic_id}": j 
            for j in topic_jobs if j.status in ["GENERATED", "VERIFIED", "APPROVED"]
        }
        self.existing_graph = course.course_graph or {"children": []}
        
        # Build lookup maps for preservation
        self.existing_modules = {} # normalized_name -> node
        self.existing_topics = {}  # normalized_name -> node (scoped by module)
        self.global_slide_map = {} # stable_key -> slide_node
        self.claimed_ids = set()   # IDs matched by ANY job
        
        self._index_existing_graph()
        self._index_all_slides()
        self._precalculate_claims()
        
        self.extractor = ConceptExtractor()
        
        # Load Existing KG
        self.concepts = {c.get("id"): c for c in self.existing_graph.get("concepts", [])}
        self.relations = {f"{r.get('source_id')}-{r.get('target_id')}": r for r in self.existing_graph.get("relations", [])}

    def _index_existing_graph(self):
        """Index existing nodes to preserve IDs and Metadata"""
        if not self.existing_graph:
            return

        children = self.existing_graph.get("children", [])
        for m in children:
            # key by name/title
            m_key = self._normalize(m.get("name"))
            self.existing_modules[m_key] = m
            
            for t in m.get("children", []):
                t_key = f"{m_key}::{self._normalize(t.get('title'))}"
                self.existing_topics[t_key] = t
                
    def _index_all_slides(self):
        """Build global index of all existing slides by stable_key"""
        if not self.existing_graph: return
        
        for m in self.existing_graph.get("children", []):
            for t in m.get("children", []):
                for sub in t.get("children", []):
                    for s in sub.get("children", []):
                        tags = s.get("tags", {})
                        s_key = tags.get("stable_key")
                        if s_key:
                            if isinstance(s_key, list): s_key = s_key[0]
                            self.global_slide_map[str(s_key)] = s

    def _precalculate_claims(self):
        """Pre-calculate which existing IDs will be claimed by Jobs (Global Scope)"""
        for key, job in self.jobs_map.items():
            if not job.slides_json: continue
            
            # Replicate key generation logic
            raw_slides = job.slides_json.get("slides", [])
            # Grouping/Flattening logic replication not strictly needed IF we just iterate list
            # The key logic is: {module_id}::{topic_id}::slide::{index} where index is 0..N of raw list
            
            for idx, s in enumerate(raw_slides):
                stable_key = f"{job.module_id}::{job.topic_id}::v{job.version}::slide::{idx}"
                
                # Check Global Index
                if stable_key in self.global_slide_map:
                    existing_s = self.global_slide_map[stable_key]
                    self.claimed_ids.add(existing_s.get("id"))

    def _normalize(self, text: str) -> str:
        return str(text).strip().lower()

    def build(self) -> (CourseGraph, dict):
        """
        Builds the CourseGraph structure deterministically from Blueprint.
        """
        blueprint = self.course.blueprint or {}
        new_children: List[ModuleNode] = []
        
        bp_modules = blueprint.get("modules", [])
        
        stats = {
            "modules_created": 0, 
            "topics_created": 0, 
            "slides_linked": 0, 
            "approvals_preserved": 0,
            "edits_preserved": 0
        }

        for i, mod_data in enumerate(bp_modules):
            m_title = mod_data.get("title", f"Module {i+1}")
            m_key = self._normalize(m_title)
            
            # --- 1. Module Node Resolution ---
            existing_mod = self.existing_modules.get(m_key)
            if existing_mod:
                m_node = ModuleNode(
                    id=existing_mod.get("id"),
                    order=existing_mod.get("order", i+1),
                    name=m_title,
                    module_id=str(mod_data.get("id")),
                    ncrf_level=existing_mod.get("ncrf_level")
                )
            else:
                m_node = ModuleNode(
                    order=i+1,
                    name=m_title,
                    module_id=str(mod_data.get("id"))
                )
                stats["modules_created"] += 1

            # --- 2. Topic Node Resolution ---
            bp_topics = mod_data.get("topics", [])
            for j, top_data in enumerate(bp_topics):
                t_title = top_data.get("name", f"Topic {j+1}")
                t_key = f"{m_key}::{self._normalize(t_title)}"
                
                existing_top = self.existing_topics.get(t_key)
                
                # Resolve Approval Status
                # Rule: Graph Approval > Job Approval (if PENDING)
                final_approval = None
                
                # Check Job first (for fallback)
                job_key = f"{m_node.module_id}::{str(top_data.get('id'))}"
                job = self.jobs_map.get(job_key)
                
                # Debug Logging (TEMPORARY)
                if not job:
                    # logger.info(f"GraphBuilder: No job match for key='{job_key}'. Available keys: {list(self.jobs_map.keys())}")
                    pass
                else:
                    pass
                    # logger.info(f"GraphBuilder: Match found for key='{job_key}'")
                
                if existing_top and existing_top.get("approval"):
                     # Preserve Graph Approval
                     final_approval = ApprovalStatus(**existing_top.get("approval"))
                     stats["approvals_preserved"] += 1
                elif job and job.approval_status in ["APPROVED", "REJECTED"]:
                     # Initialize from Job if Graph has none
                     final_approval = ApprovalStatus(
                         status=job.approval_status,
                         timestamp=job.approved_at.isoformat() if job.approved_at else None,
                         comment=job.rejection_reason or job.reviewer_notes
                     )

                if existing_top:
                    t_node = TopicNode(
                        id=existing_top.get("id"),
                        order=existing_top.get("order", j+1),
                        title=t_title,
                        topic_id=str(top_data.get("id")),
                        approval=final_approval,
                        outcome=top_data.get("topic_outcome") or top_data.get("topic_outcome")
                    )
                else:
                    t_node = TopicNode(
                        order=j+1,
                        title=t_title,
                        topic_id=str(top_data.get("id")),
                        approval=final_approval,
                        outcome=top_data.get("topic_outcome") or top_data.get("topic_outcome")
                    )
                    stats["topics_created"] += 1

                # --- 3. Content Merge (Slides) ---
                
                if job and job.slides_json:
                    # We have a generation source. Use it, but MERGE with existing.
                    raw_slides = job.slides_json.get("slides", [])
                    children, count = self._merge_slides_content(raw_slides, existing_top, m_node.module_id, t_node.topic_id, stats, job_version=job.version)
                    t_node.children = children

                elif existing_top and existing_top.get("children"):
                    # No job source, but graph has content (e.g. manually added or orphaned job). Keep it.
                    # BUT: Must inspect if any children were claimed by other topics?
                    # Since existing_top is processed here, we essentially own it. 
                    # If global claims exist, it means a NEW job elsewhere claimed it. 
                    # If so, we should probably remove it?
                    # The Orphan Rescue logic inside `_merge_slides_content` handles filtering by claimed_ids.
                    # So we should reuse that or replicate filter?
                    # Reusing `_merge_slides_content` with empty job_slides triggers Orphan Logic.
                    children, count = self._merge_slides_content([], existing_top, m_node.module_id, t_node.topic_id, stats)
                    t_node.children = children
                    # stats["edits_preserved"] += len(t_node.children) # Handled inside

                m_node.children.append(t_node)

            new_children.append(m_node)

        # Version handling
        current_ver = self.course.course_graph_version or 0
        
        return CourseGraph(
            course_id=self.course.id,
            version=current_ver + 1,
            children=new_children,
            concepts=list(self.concepts.values()),
            relations=list(self.relations.values())
        ), stats

    def _merge_slides_content(self, job_slides: List[dict], existing_topic: dict, module_id: str, topic_id: str, stats: dict, job_version: int = 1) -> List[SubtopicNode]:
        """
        Merges Job Slides into Graph Structure, preserving existing IDs and edits.
        Matching Strategy (in order):
        1. Match by stable_key (GLOBAL) - primary identity
        2. Match by content fingerprint (for non-edited slides) - robust fallback
        3. Order-based matching ONLY as last resort for new slides
        """
        import hashlib
        
        # --- Index existing slides by multiple strategies ---
        # 1. By stable_key (already in global_slide_map, but index locally too for topic scope)
        existing_slides_by_stable_key = {}
        # 2. By content fingerprint (for non-edited slides only)
        existing_slides_by_fingerprint = {}
        # 3. By order (last resort, scoped to topic)
        existing_slides_by_order = {}
        
        def _normalize_content(text):
            """Normalize text for fingerprinting"""
            return str(text).strip().lower() if text else ""
        
        def _compute_fingerprint(slide):
            """Compute content fingerprint: title + bullets"""
            title = _normalize_content(slide.get("title", ""))
            bullets = slide.get("bullets", [])
            bullets_str = "|".join([_normalize_content(b) for b in bullets])
            content_str = f"{title}|{bullets_str}"
            return hashlib.sha1(content_str.encode()).hexdigest()
        
        if existing_topic:
            for sub in existing_topic.get("children", []):
                for s in sub.get("children", []):
                    # Index by stable_key
                    tags = s.get("tags", {})
                    s_key = tags.get("stable_key")
                    if s_key:
                        if isinstance(s_key, list): s_key = s_key[0]
                        existing_slides_by_stable_key[str(s_key)] = s
                    
                    # Index by fingerprint (only for non-edited slides)
                    edited_flag = tags.get("edited_by_user")
                    is_edited = False
                    if str(edited_flag).lower() == "true" or (isinstance(edited_flag, list) and "true" in [str(x).lower() for x in edited_flag]):
                        is_edited = True
                    
                    if not is_edited:
                        fingerprint = _compute_fingerprint(s)
                        # Only index if not already claimed (avoid duplicates)
                        if fingerprint not in existing_slides_by_fingerprint:
                            existing_slides_by_fingerprint[fingerprint] = s
                    
                    # Index by order (last resort)
                    o_key = s.get("order")
                    if o_key is not None:
                        existing_slides_by_order[o_key] = s

        # Group Job Slides by Subtopic
        grouped_slides = {} # subtopic_title -> list of slides
        subtopic_order = []
        default_subtopic = "Content"
        
        global_idx = 0
        
        for js in job_slides:
            sub_title = js.get("subtopic") or default_subtopic
            if sub_title not in grouped_slides:
                grouped_slides[sub_title] = []
                subtopic_order.append(sub_title)
            
            stable_key = f"{module_id}::{topic_id}::v{job_version}::slide::{global_idx}"
            js["_stable_key"] = stable_key
            global_idx += 1
            
            grouped_slides[sub_title].append(js)

        # --- Extractor Check ---
        if job_slides:
            new_concepts, new_rels, slide_concept_map = self.extractor.extract(job_slides)
            for c in new_concepts:
                if c.id not in self.concepts: self.concepts[c.id] = c.model_dump()
            for r in new_rels:
                key = f"{r.source_id}-{r.target_id}"
                if key not in self.relations: self.relations[key] = r.model_dump()
        else:
             slide_concept_map = {}

        final_subtopics = []
        course_id_str = str(self.course.id)
        
        matched_locally_ids = set()

        for idx_sub, sub_title in enumerate(subtopic_order):
            s_slides = grouped_slides[sub_title]
            
            # Resolve Subtopic Node
            existing_sub_node = None
            if existing_topic:
                 for cand in existing_topic.get("children", []):
                     if cand.get("title") == sub_title:
                         existing_sub_node = cand
                         break
            
            if existing_sub_node:
                sub_id = existing_sub_node.get("id")
            else:
                sub_seed = f"{course_id_str}:{module_id}:{topic_id}:sub:{sub_title}"
                sub_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, sub_seed))
            
            sub_node = SubtopicNode(
                id=sub_id,
                title=sub_title,
                order=idx_sub + 1,
                children=[]
            )

            for js in s_slides:
                order = js.get("order", js.get("slide_no", 0))
                stable_key = js.get("_stable_key")
                
                # --- MATCHING STRATEGY (Priority Order) ---
                # 1. Match by Stable Key (GLOBAL) - Primary identity
                matched_s = self.global_slide_map.get(stable_key)
                if not matched_s:
                    matched_s = existing_slides_by_stable_key.get(stable_key)
                
                # 2. Match by Content Fingerprint (for non-edited slides) - Robust fallback
                if not matched_s:
                    js_fingerprint = _compute_fingerprint(js)
                    matched_s = existing_slides_by_fingerprint.get(js_fingerprint)
                
                # 3. Match by Order (LAST RESORT - only if no content match found)
                # This handles truly new slides that don't match any existing content
                if not matched_s:
                    matched_s = existing_slides_by_order.get(order)
                
                if matched_s:
                    matched_locally_ids.add(matched_s.get("id"))
                    
                    # CHECK EDIT STATUS
                    tags = matched_s.get("tags", {})
                    edited_flag = tags.get("edited_by_user")
                    is_edited = False
                    if str(edited_flag).lower() == "true" or (isinstance(edited_flag, list) and "true" in [str(x).lower() for x in edited_flag]):
                        is_edited = True
                    
                    if is_edited:
                        # RULE: PRESERVE CONTENT
                        stats["edits_preserved"] += 1
                        slide_node = self._parse_slide(matched_s)
                        if not slide_node.tags: slide_node.tags = {}
                        slide_node.tags["stable_key"] = [stable_key]
                    else:
                        # RULE: UPDATE CONTENT, KEEP ID
                        new_tags = tags.copy()
                        new_tags["source"] = ["job_generation"]
                        new_tags["stable_key"] = [stable_key]
                        
                        slide_node = SlideNode(
                            id=matched_s.get("id"),
                            title=js.get("title", "Untitled"),
                            bullets=js.get("bullets", []),
                            speaker_notes=js.get("speaker_notes", ""),
                            illustration_prompt=js.get("illustration_prompt", ""),
                            order=order,
                            tags=new_tags
                        )
                else:
                    # NEW SLIDE
                    stable_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, stable_key))
                    slide_node = SlideNode(
                        id=stable_id,
                        title=js.get("title", "Untitled"),
                        bullets=js.get("bullets", []),
                        speaker_notes=js.get("speaker_notes", ""),
                        illustration_prompt=js.get("illustration_prompt", ""),
                        order=order,
                        tags={ 
                            "source": ["job_generation"],
                            "stable_key": [stable_key]
                        }
                    )
                    stats["slides_linked"] += 1

                # Restore Concept Linking
                try:
                    js_idx = job_slides.index(js) + 1
                    c_ids = slide_concept_map.get(str(js_idx), [])
                    if c_ids:
                         if not slide_node.tags: slide_node.tags = {}
                         slide_node.tags["concept_ids"] = c_ids
                except ValueError:
                    pass
                
                sub_node.children.append(slide_node)
            
            final_subtopics.append(sub_node)
            
        # --- ORPHAN RESCUE STRATEGY ---
        orphans = []
        
        if existing_topic:
            for sub in existing_topic.get("children", []):
                for s in sub.get("children", []):
                    s_id = s.get("id")
                    
                    # 1. If used in THIS topic update, skip (already added)
                    if s_id in matched_locally_ids:
                        continue
                        
                    # 2. If claimed by ANY OTHER job, skip (it moved)
                    if s_id in self.claimed_ids:
                        continue

                    # 3. Else, check if edited (Rescue)
                    tags = s.get("tags", {})
                    edited_flag = tags.get("edited_by_user")
                    is_edited = False
                    if str(edited_flag).lower() == "true" or (isinstance(edited_flag, list) and "true" in [str(x).lower() for x in edited_flag]):
                        is_edited = True
                    
                    if is_edited:
                        orphans.append(self._parse_slide(s))
        
        if orphans:
            logger.info(f"GraphBuilder: Rescuing {len(orphans)} orphaned edited slides")
            preserved_sub = SubtopicNode(
                id=str(uuid.uuid4()),
                title="Preserved User Content",
                order=999,
                children=orphans
            )
            final_subtopics.append(preserved_sub)
            stats["edits_preserved"] += len(orphans)

        return final_subtopics, stats["slides_linked"]

    def _parse_subtopic_or_slide(self, data: dict):
        try:
            return SubtopicNode(**data)
        except:
             return data

    def _parse_slide(self, data: dict) -> SlideNode:
        return SlideNode(**data)
