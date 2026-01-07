import logging
from enum import Enum
from typing import Dict, Any, Optional
from shared.llm_clients.gemini_pro import GeminiProClient
from shared.llm_clients.gemini_flash import GeminiFlashClient

logger = logging.getLogger(__name__)

class ModelType(Enum):
    DESIGN = "design"       # Maps to Pro
    TUTORING = "tutoring"   # Maps to Flash

class MCPRouter:
    """
    Model Control Protocol (MCP) Router.
    Routes requests to the appropriate model based on task type.
    """
    def __init__(self, api_key: str):
        self.pro_client = GeminiProClient(api_key)
        self.flash_client = GeminiFlashClient(api_key)
        logger.info("MCP Router initialized")

    async def route_request(self, task_type: ModelType, prompt: str, context: Optional[str] = None) -> Dict[str, Any]:
        """
        Route the request to the appropriate model.
        """
        try:
            if task_type == ModelType.DESIGN:
                logger.info("Routing to Gemini Pro (Design Mode)")
                try:
                    response = await self.pro_client.generate(prompt, context)
                    model_used = self.pro_client.model_name
                except Exception as e:
                    logger.warning(f"⚠️ Primary Model (Pro) failed: {e}. Attempting Fallback to Flash.")
                    response = await self.flash_client.generate(prompt, context)
                    model_used = f"{self.flash_client.model_name} (Fallback)"
            elif task_type == ModelType.TUTORING:
                logger.info("Routing to Gemini Flash (Tutoring Mode)")
                response = await self.flash_client.generate(prompt, context)
                model_used = self.flash_client.model_name
            else:
                raise ValueError(f"Unknown task type: {task_type}")

            return {
                "content": response,
                "model_used": model_used,
                "task_type": task_type.value
            }
        except Exception as e:
            logger.error(f"MCP Routing failed: {e}")
            raise
