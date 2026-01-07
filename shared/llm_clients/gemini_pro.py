import logging
from typing import Dict, Any, Optional
import os
import google.generativeai as genai

logger = logging.getLogger(__name__)

class GeminiProClient:
    """
    Client for Gemini 2.5 Pro (Design/Planning tasks).
    """
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("API key is required for GeminiProClient")
        genai.configure(api_key=api_key)
        # Using gemini-2.0-pro-exp or updated by env
        self.model_name = os.getenv("ADVANCED_LLM_MODEL", "models/gemini-1.5-pro")
        self.model = genai.GenerativeModel(self.model_name)
        logger.info(f"Initialized GeminiProClient with model: {self.model_name}")

    async def generate(self, prompt: str, context: Optional[str] = None) -> str:
        """
        Generate content using Gemini Pro.
        """
        try:
            full_prompt = prompt
            if context:
                full_prompt = f"Context:\n{context}\n\nTask:\n{prompt}"
            
            logger.info(f"Sending request to {self.model_name}")
            response = await self.model.generate_content_async(full_prompt)
            return response.text
        except Exception as e:
            logger.error(f"Gemini Pro generation failed: {e}")
            raise
