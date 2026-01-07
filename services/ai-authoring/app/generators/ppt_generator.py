import json
import os
import logging
from pptx import Presentation
from pptx.util import Inches, Pt

logger = logging.getLogger(__name__)

class PptGenerator:
    def __init__(self, gemini_client):
        self.gemini_client = gemini_client
        # Patch for local execution: use relative path if /app is not writable or doesn't exist
        base_dir = "/app/generated_data" if os.path.exists("/app/generated_data") else "generated_data"
        self.output_dir = f"{base_dir}/generated_ppts"
        os.makedirs(self.output_dir, exist_ok=True)

    async def generate_slide_plan(self, prompt_text: str, blueprint: dict) -> dict:
        """
        Generate a JSON SlidePlan using the LLM.
        """
        # Augment prompt with JSON enforcement if not present (the upstream prompt builder should do this, but safe to add)
        system_instruction = """
        IMPORTANT: Output ONLY valid JSON.
        STRICT RULES:
        1.  Generate EXACTLY 8 slides for this topic. No less.
        2.  Each slide MUST include an 'illustration_prompt' field with a descriptive prompt for an image/diagram.
        3.  Content per slide: Max 12 lines, approx 15 words per line.
        
        Format:
        {
          "slides": [
            {
              "subtopic": "Subtopic Title (e.g. Introduction, Key Concepts)",
              "title": "Slide Title",
              "bullets": ["Bullet 1", "Bullet 2"],
              "speaker_notes": "Detailed speaker notes...",
              "illustration_prompt": "A diagram showing..." 
            }
          ]
        }
        """
        full_prompt = f"{prompt_text}\n\n{system_instruction}"
        
        logger.info("Generating SlidePlan JSON...")
        slide_plan = await self.gemini_client.generate_json(full_prompt)
        
        # Normalize Keys (Legacy Support -> Canonical)
        normalized_slides = []
        raw_slides = slide_plan.get("slides", [])
        if not raw_slides:
             # Handle flat list input if LLM messes up structure
             if isinstance(slide_plan, list): raw_slides = slide_plan
             
        for s in raw_slides:
            norm = {
                "subtopic": s.get("subtopic", "General"),
                "title": s.get("title") or s.get("slide_title") or "Untitled",
                "bullets": s.get("bullets", []),
                "speaker_notes": s.get("speaker_notes") or s.get("notes") or "",
                "illustration_prompt": s.get("illustration_prompt") or s.get("illustration") or "Visual description placeholder"
            }
            normalized_slides.append(norm)
            
        slide_plan["slides"] = normalized_slides
        return slide_plan

    async def render_pptx(self, slide_plan: dict, course_id: int) -> str:
        """
        Request Node.js ppt-renderer to create PPTX.
        Returns absolute path to generated file.
        """
        try:
            import aiohttp
            
            output_dir = "/app/generated_data/ppt"
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, f"course_{course_id}_preview.pptx")
            
            payload = {
                "slide_plan": slide_plan,
                "course_id": course_id,
                "output_path": output_path
            }
            
            # Call Node service
            # Assuming hostname 'ppt-renderer' and port 3000 from docker-compose
            ppt_service_url = os.getenv("PPT_RENDERER_URL", "http://ppt-renderer:3000/render")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(ppt_service_url, json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        logger.info(f"PPT Generated via Node: {data.get('path')}")
                        return data.get('path')
                    else:
                        text = await resp.text()
                        logger.error(f"PPT Renderer failed: {text}")
                        raise RuntimeError(f"PPT Renderer failed: {text}")
            
        except Exception as e:
            logger.error(f"PPT Rendering failed: {e}")
            raise
