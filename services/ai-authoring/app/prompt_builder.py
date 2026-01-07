
import json
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional

def compute_hash(data: Any) -> str:
    """Computes SHA-256 hash of canonical JSON string."""
    encoded = json.dumps(data, sort_keys=True, default=str).encode('utf-8')
    return hashlib.sha256(encoded).hexdigest()

class PromptBuilder:
    def __init__(self, spec: Dict[str, Any], blueprint: Dict[str, Any], 
                 outline: Optional[Dict[str, Any]] = None, 
                 evidence: Optional[Dict[str, Any]] = None,
                 topic_context: Optional[Dict[str, Any]] = None,
                 key_concepts: Optional[list] = None,
                 prerequisites: Optional[list] = None,
                 global_instructions: Optional[str] = None):
        self.spec = spec
        self.blueprint = blueprint
        self.outline = outline or {}
        self.evidence = evidence or {}
        self.topic_context = topic_context or {} 
        self.key_concepts = key_concepts or []
        self.prerequisites = prerequisites or []
        self.global_instructions = global_instructions # {module_id, topic_id, module_title, topic_title}
        
    def build_system_prompt(self) -> str:
        constraints = self.spec.get('output_constraints', {})
        max_slides = constraints.get('max_slides', 15)
        # Fallback to defaults if not present
        font_min = constraints.get('font_size_min', 18)
        word_limit = constraints.get('word_limit', 400)
        
        bloom = self.spec.get('bloom', {})
        bloom_default = bloom.get('default_level', 'Apply')
        
        pedagogy = self.spec.get('pedagogy_checklist', [])
        
        prompt = [
            "Role: Educational Content Architect.",
            "Task: Create strictly structured educational slide content.",
            "--- SYSTEM CONSTRAINTS ---",
            f"1. Max Slides: {max_slides}",
            f"2. Min Font Size Context: {font_min}pt",
            f"3. Max Words per Slide (approx): {word_limit}",
            f"4. Bloom's Taxonomy Level: {bloom_default}",
            "5. Slide Count Rule: EXACTLY 8 slides per topic.",
            "6. Subtopic Rule: At least 1 slide per subtopic.",
            f"7. Visuals: MUST include 'illustration_prompt' field for every slide (Prompt for generating image).",
        ]
        
        if pedagogy:
            prompt.append(f"8. Pedagogy Checklist: {', '.join(pedagogy)}")
            
        strictness = constraints.get('grounding_strictness', 'NORMAL')
        prompt.append(f"9. Grounding Strictness: {strictness}")
        if strictness == "STRICT":
            prompt.append("   - NO ungrounded claims.")
            prompt.append("   - REQUIRE citations if evidence is provided.")
            
        return "\n".join(prompt)

    def build_developer_prompt(self) -> str:
        return """--- DEVELOPER INSTRUCTIONS ---
1. Formatting:
   - Slide Title: Concise, Action-Oriented.
   - Bullets: 3-5 per slide.
   - Speaker Notes: Narrative, engaging script (2-3 paragraphs).
2. Schema:
   - Must output valid JSON matching the 'slides' array structure.
   - Each slide object MUST have a 'subtopic' field (string) to group slides logically.
   - Each slide object MUST have an 'illustration_prompt' field (string).
3. Safety:
   - Do NOT fabricate standards (IS Codes, ASTM) unless evidence is present.
   - If content is unsafe/harmful, refuse to generate."""

    def build_user_prompt(self) -> str:
        # Prefer KG Outline
        if self.outline and self.outline.get("course_title"):
             course_title = self.outline.get("course_title")
        else:
             course_title = self.blueprint.get('course', {}).get('course_title', 'Untitled Course')
        
        prompt = [
            f"--- USER REQUEST ---",
            f"Course Title: {course_title}",
            "Please generate the slide outline and content based on the following inputs.",
            "",
            "--- GENERATION SPECIFICATION ---",
            json.dumps(self.spec, indent=2),
        ]
        
        # Add basic blueprint summary if needed, usually specs are derived from it
        # But user requested "relevant blueprint summary"
        if self.outline and self.outline.get("modules"):
             # Use KG Outline Modules
             modules = self.outline.get("modules", [])
             # Adapt structure if needed. KG modules: {id, title, topics: []}
             # Blueprint modules: {id, title/name, topics: []}
        else:
             modules = self.blueprint.get('modules', [])
             if not modules and 'course' in self.blueprint and 'modules' in self.blueprint['course']:
                  # Handle nested blueprint structure if it exists differently in some payloads
                  modules = self.blueprint['course']['modules']

        mod_list = []
        for m in modules:
            m_title = m.get('module_name') or m.get('title') or m.get('name') or "Untitled"
            mod_list.append(f"- {m_title}")
            
        prompt.append("")
        prompt.append("--- MODULE STRUCTURE ---")
        prompt.append("\n".join(mod_list))
        
        return "\n".join(prompt)

    def build_bundle(self) -> Dict[str, Any]:
        sys_p = self.build_system_prompt()
        dev_p = self.build_developer_prompt()
        usr_p = self.build_topic_prompt() if self.topic_context else self.build_user_prompt()
        
        rendered = f"{sys_p}\n\n{dev_p}\n\n{usr_p}"
        
        return {
            "version": "PB_v1",
            "system_prompt": sys_p,
            "developer_prompt": dev_p,
            "user_prompt": usr_p,
            "rendered_prompt": rendered,
            "metadata": {
                "prompt_hash": compute_hash(rendered),
                "spec_hash": compute_hash(self.spec),
                "blueprint_hash": compute_hash(self.blueprint),
                "created_at": datetime.utcnow().isoformat() + "Z",
                "strictness": self.spec.get('output_constraints', {}).get('grounding_strictness', 'NORMAL'),
                "max_slides": self.spec.get('output_constraints', {}).get('max_slides', 15)
            }
        }

    def build_topic_prompt(self) -> str:
        """Specific prompt for generating slides for a SINGLE topic."""
        if self.outline and self.outline.get("course_title"):
             course_title = self.outline.get("course_title")
        else:
             course_title = self.blueprint.get('course', {}).get('course_title', self.blueprint.get('title', 'Unknown Course'))
        
        mod_title = self.topic_context.get('module_title', 'Unknown Module')
        topic_title = self.topic_context.get('topic_title', 'Unknown Topic')
        
        prompt = [
            f"--- TOPIC GENERATION REQUEST ---",
            f"Course: {course_title}",
            f"Module: {mod_title}",
            f"Topic: {topic_title}",
            "",
            "TASK: Generate structured slide content for THIS SPECIFIC TOPIC.",
            "REQUIREMENTS:",
            "1. Output EXACTLY 8 slides.",
            "2. Ensure flow covers: Introduction -> Key Concepts -> Examples -> Application -> Summary.",
            "3. Each slide gets a visual prompt.",
            "4. Content must be rigorous but accessible.",
        ]
        
        if self.key_concepts:
             prompt.append(f"   - MUST explicitly cover these related concepts: {', '.join(self.key_concepts)}")
        
        if self.prerequisites:
             prompt.append(f"   - Consider these prerequisites for context: {', '.join(self.prerequisites)}")

        prompt.append("")
        prompt.append("--- GENERATION SPECS ---")
        prompt.append(json.dumps(self.spec, indent=2))
        prompt.append("")
        prompt.append("--- REQUIRED JSON OUTPUT FORMAT ---")
        prompt.append("""{
  "slides": [
    {
      "slide_no": 1,
      "subtopic": "Subtopic Name",
      "title": "Slide Title",
      "bullets": ["Bullet 1", "Bullet 2"],
      "speaker_notes": "Notes...",
      "illustration_prompt": "Visual description"
    }
  ]
}""")
        
        if self.global_instructions:
            prompt.append("")
            prompt.append("--- GLOBAL COURSE INSTRUCTIONS ---")
            prompt.append("The following are the master instructions for this course. Adapt them to this specific topic:")
            prompt.append(self.global_instructions)
            
        return "\n".join(prompt)
