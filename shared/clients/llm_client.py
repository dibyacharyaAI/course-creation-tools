"""
LLM Client Abstraction Layer

Provides a unified interface for LLM interactions with automatic fallback logic.
Supports multiple Gemini models with configurable retry behavior.
"""

import logging
import json
import asyncio
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from enum import Enum

import google.generativeai as genai


logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Base exception for LLM-related errors"""
    pass


class LLMQuotaError(LLMError):
    """Raised when quota/rate limit is exceeded"""
    pass


class LLMTimeoutError(LLMError):
    """Raised when request times out"""
    pass


class LLMClient(ABC):
    """Abstract base class for LLM clients"""
    
    @abstractmethod
    async def generate(self, prompt: str, temperature: float = 0.7) -> str:
        """
        Generate text from a prompt.
        
        Args:
            prompt: The input prompt
            temperature: Sampling temperature (0.0 to 1.0)
            
        Returns:
            Generated text response
            
        Raises:
            LLMError: On generation failure
        """
        pass
    
    @abstractmethod
    def get_model_name(self) -> str:
        """Return the model identifier"""
        pass


class GeminiFlashLiteClient(LLMClient):
    """
    Primary LLM client using Gemini 2.5 Flash Lite.
    Fast and cost-effective for most course generation tasks.
    """
    
    def __init__(self, api_key: str, model_name: str = "models/gemini-2.0-flash-lite"):
        if not api_key:
            raise ValueError("GEMINI_API_KEY is required")
        
        genai.configure(api_key=api_key)
        self.model_name = model_name
        self.model = genai.GenerativeModel(model_name)
        logger.info(f"Initialized GeminiFlashLiteClient with model: {model_name}")
    
    async def generate(self, prompt: str, temperature: float = 0.7) -> str:
        """Generate text using Gemini Flash Lite"""
        try:
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=temperature
                )
            )
            return response.text
        except Exception as e:
            error_msg = str(e).lower()
            
            # Check for quota/rate limit errors
            if "429" in error_msg or "quota" in error_msg or "rate limit" in error_msg:
                raise LLMQuotaError(f"Quota exceeded for {self.model_name}: {e}")
            
            # Check for timeout errors
            if "timeout" in error_msg:
                raise LLMTimeoutError(f"Request timeout for {self.model_name}: {e}")
            
            # Generic error
            raise LLMError(f"Generation failed for {self.model_name}: {e}")
    
    def get_model_name(self) -> str:
        return self.model_name


class GeminiFlashClient(LLMClient):
    """
    Fallback LLM client using Gemini 2.5 Flash.
    More capable than Flash Lite, used when primary model fails.
    """
    
    def __init__(self, api_key: str, model_name: str = "models/gemini-2.0-flash-exp"):
        if not api_key:
            raise ValueError("GEMINI_API_KEY is required")
        
        genai.configure(api_key=api_key)
        self.model_name = model_name
        self.model = genai.GenerativeModel(model_name)
        logger.info(f"Initialized GeminiFlashClient with model: {model_name}")
    
    async def generate(self, prompt: str, temperature: float = 0.7) -> str:
        """Generate text using Gemini Flash"""
        try:
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=temperature
                )
            )
            return response.text
        except Exception as e:
            error_msg = str(e).lower()
            
            if "429" in error_msg or "quota" in error_msg or "rate limit" in error_msg:
                raise LLMQuotaError(f"Quota exceeded for {self.model_name}: {e}")
            
            if "timeout" in error_msg:
                raise LLMTimeoutError(f"Request timeout for {self.model_name}: {e}")
            
            raise LLMError(f"Generation failed for {self.model_name}: {e}")
    
    def get_model_name(self) -> str:
        return self.model_name


class GeminiProClient(LLMClient):
    """
    Advanced LLM client using Gemini 2.5 Pro.
    For high-reasoning tasks like pedagogical planning and OBE design.
    Requires paid tier.
    """
    
    def __init__(self, api_key: str, model_name: str = "models/gemini-2.0-pro-exp"):
        if not api_key:
            raise ValueError("GEMINI_API_KEY is required")
        
        genai.configure(api_key=api_key)
        self.model_name = model_name
        self.model = genai.GenerativeModel(model_name)
        logger.info(f"Initialized GeminiProClient with model: {model_name}")
    
    async def generate(self, prompt: str, temperature: float = 0.7) -> str:
        """Generate text using Gemini Pro"""
        try:
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=temperature
                )
            )
            return response.text
        except Exception as e:
            error_msg = str(e).lower()
            
            if "429" in error_msg or "quota" in error_msg or "rate limit" in error_msg:
                raise LLMQuotaError(f"Quota exceeded for {self.model_name}: {e}")
            
            if "timeout" in error_msg:
                raise LLMTimeoutError(f"Request timeout for {self.model_name}: {e}")
            
            raise LLMError(f"Generation failed for {self.model_name}: {e}")
    
    def get_model_name(self) -> str:
        return self.model_name


class LLMClientWithFallback:
    """
    LLM client wrapper with automatic fallback logic.
    
    Fallback flow:
    1. Try primary client (Flash Lite)
    2. On error (429, timeout, etc.) → Try fallback client (Flash)
    3. If both fail → Raise error with detailed logs
    """
    
    def __init__(
        self,
        primary_client: LLMClient,
        fallback_client: Optional[LLMClient] = None,
        enable_fallback: bool = True
    ):
        self.primary_client = primary_client
        self.fallback_client = fallback_client
        self.enable_fallback = enable_fallback and fallback_client is not None
        
        logger.info(
            f"LLMClientWithFallback initialized - "
            f"Primary: {primary_client.get_model_name()}, "
            f"Fallback: {fallback_client.get_model_name() if fallback_client else 'None'}, "
            f"Enabled: {self.enable_fallback}"
        )
    
    async def generate(self, prompt: str, temperature: float = 0.7) -> str:
        """
        Generate text with automatic fallback.
        
        Args:
            prompt: The input prompt
            temperature: Sampling temperature
            
        Returns:
            Generated text response
            
        Raises:
            LLMError: If both primary and fallback models fail
        """
        # Try primary model first
        try:
            logger.debug(f"Attempting generation with primary model: {self.primary_client.get_model_name()}")
            result = await self.primary_client.generate(prompt, temperature)
            logger.info(f"✅ Successfully generated content with primary model: {self.primary_client.get_model_name()}")
            return result
            
        except (LLMQuotaError, LLMTimeoutError, LLMError) as primary_error:
            logger.warning(
                f"⚠️ Primary model {self.primary_client.get_model_name()} failed: {primary_error}"
            )
            
            # Try fallback if enabled
            if self.enable_fallback and self.fallback_client:
                try:
                    logger.info(f"🔄 Retrying with fallback model: {self.fallback_client.get_model_name()}")
                    result = await self.fallback_client.generate(prompt, temperature)
                    logger.info(
                        f"✅ Successfully generated content with fallback model: {self.fallback_client.get_model_name()}"
                    )
                    return result
                    
                except (LLMQuotaError, LLMTimeoutError, LLMError) as fallback_error:
                    logger.error(
                        f"❌ Fallback model {self.fallback_client.get_model_name()} also failed: {fallback_error}"
                    )
                    raise LLMError(
                        f"Both primary and fallback models failed. "
                        f"Primary ({self.primary_client.get_model_name()}): {primary_error}. "
                        f"Fallback ({self.fallback_client.get_model_name()}): {fallback_error}"
                    )
            else:
                # No fallback available
                logger.error(f"❌ Primary model failed and no fallback configured")
                raise primary_error
    
    def get_model_name(self) -> str:
        """Return info about configured models"""
        if self.fallback_client:
            return f"{self.primary_client.get_model_name()} (fallback: {self.fallback_client.get_model_name()})"
        return self.primary_client.get_model_name()
