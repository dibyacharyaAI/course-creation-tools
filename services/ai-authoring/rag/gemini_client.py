import google.generativeai as genai
import json
import logging
import asyncio
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)

class GeminiClient:
    def __init__(self, api_key: str, primary_model: str = "gemini-pro", fallback_model: str = "gemini-pro", enable_fallback: bool = False):
        self.api_key = api_key
        self.primary_model_name = primary_model
        self.fallback_model_name = fallback_model
        self.enable_fallback = enable_fallback
        
        if not api_key:
            logger.warning("Gemini API Key is missing")
        else:
            genai.configure(api_key=api_key)

    async def generate_content(self, prompt: str) -> str:
        return await self._generate(prompt, self.primary_model_name)

    async def generate_json(self, prompt: str) -> Dict[str, Any]:
        text = await self._generate(prompt, self.primary_model_name)
        return self._parse_json(text)

    async def _generate(self, prompt: str, model_name: str) -> str:
        try:
            model = genai.GenerativeModel(model_name)
            loop = asyncio.get_running_loop()
            # method is blocking, run in executor
            response = await loop.run_in_executor(None, lambda: model.generate_content(prompt))
            return response.text
        except Exception as e:
            logger.error(f"Gemini generation failed: {e}")
            # Simple fallback logic could go here
            raise e

    def _parse_json(self, text: str) -> Dict[str, Any]:
        try:
            clean_text = text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}. Text: {text[:200]}")
            return {}

    def retrieve_context(
        self,
        query: str,
        course_id: int = None,
        module_id: str = None,
        limit: int = 5,
        allowed_filenames: List[str] = None
    ):
        # Stub for context retrieval - strictly returns empty list as vector store is not setup here
        return []
