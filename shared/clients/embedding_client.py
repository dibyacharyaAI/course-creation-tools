"""
Embedding Client Abstraction Layer

Provides unified interface for generating embeddings for vector search and RAG.
Supports metadata enrichment for course content indexing.
"""

import logging
import asyncio
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

import google.generativeai as genai


logger = logging.getLogger(__name__)


@dataclass
class EmbeddingMetadata:
    """Metadata associated with an embedding"""
    course_id: int
    course_code: Optional[str] = None
    module_id: Optional[str] = None
    lesson_id: Optional[str] = None
    bloom_level: Optional[str] = None
    co_mapping: Optional[List[str]] = None
    content_type: Optional[str] = None  # 'lesson', 'slide', 'summary', 'outcome'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            'course_id': self.course_id,
            'course_code': self.course_code,
            'module_id': self.module_id,
            'lesson_id': self.lesson_id,
            'bloom_level': self.bloom_level,
            'co_mapping': self.co_mapping,
            'content_type': self.content_type
        }


@dataclass
class EmbeddingResult:
    """Result of an embedding operation"""
    text: str
    embedding: List[float]
    metadata: Optional[EmbeddingMetadata] = None


class EmbeddingClient(ABC):
    """Abstract base class for embedding clients"""
    
    @abstractmethod
    async def embed(self, text: str, task_type: str = "retrieval_document") -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Input text to embed
            task_type: Type of task (retrieval_document or retrieval_query)
            
        Returns:
            Embedding vector as list of floats
        """
        pass
    
    @abstractmethod
    async def embed_batch(
        self,
        texts: List[str],
        metadata: Optional[List[EmbeddingMetadata]] = None
    ) -> List[EmbeddingResult]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of input texts
            metadata: Optional metadata for each text
            
        Returns:
            List of embedding results with metadata
        """
        pass
    
    @abstractmethod
    def get_model_name(self) -> str:
        """Return the embedding model identifier"""
        pass


class GeminiEmbeddingClient(EmbeddingClient):
    """
    Embedding client using Gemini text-embedding-004 model.
    
    Optimized for:
    - Lesson text embeddings
    - Slide bullet points
    - Course outcomes (CLO/CO/PO)
    - Summaries and canonical content
    """
    
    def __init__(self, api_key: str, model_name: str = "models/text-embedding-004"):
        if not api_key:
            raise ValueError("GEMINI_API_KEY is required")
        
        genai.configure(api_key=api_key)
        self.model_name = model_name
        logger.info(f"Initialized GeminiEmbeddingClient with model: {model_name}")
    
    async def embed(self, text: str, task_type: str = "retrieval_document") -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Input text to embed
            task_type: Task type for Gemini (retrieval_document or retrieval_query)
            
        Returns:
            768-dimensional embedding vector
        """
        try:
            response = await asyncio.to_thread(
                genai.embed_content,
                model=self.model_name,
                content=text,
                task_type=task_type
            )
            
            embedding = response['embedding']
            logger.debug(f"Generated embedding for text (length: {len(text)} chars, dim: {len(embedding)})")
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise Exception(f"Embedding generation failed: {e}")
    
    async def embed_batch(
        self,
        texts: List[str],
        metadata: Optional[List[EmbeddingMetadata]] = None
    ) -> List[EmbeddingResult]:
        """
        Generate embeddings for multiple texts with metadata.
        
        Args:
            texts: List of input texts
            metadata: Optional metadata for each text (must match length of texts)
            
        Returns:
            List of embedding results with metadata
        """
        if metadata and len(metadata) != len(texts):
            raise ValueError("Metadata list must match length of texts list")
        
        results = []
        
        # Process in batches to avoid overwhelming the API
        batch_size = 100
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            batch_metadata = metadata[i:i + batch_size] if metadata else None
            
            try:
                # Generate embeddings for batch
                embeddings = await asyncio.gather(
                    *[self.embed(text) for text in batch_texts]
                )
                
                # Combine with metadata
                for j, (text, embedding) in enumerate(zip(batch_texts, embeddings)):
                    meta = batch_metadata[j] if batch_metadata else None
                    results.append(EmbeddingResult(
                        text=text,
                        embedding=embedding,
                        metadata=meta
                    ))
                
                logger.info(f"Generated embeddings for batch {i // batch_size + 1} ({len(batch_texts)} items)")
                
            except Exception as e:
                logger.error(f"Failed to generate embeddings for batch: {e}")
                raise
        
        logger.info(f"✅ Successfully generated {len(results)} embeddings")
        return results
    
    def get_model_name(self) -> str:
        return self.model_name
    
    async def embed_course_content(
        self,
        course_id: int,
        course_code: str,
        modules: List[Dict[str, Any]]
    ) -> List[EmbeddingResult]:
        """
        Helper method to embed all content from a course structure.
        
        Args:
            course_id: Course database ID
            course_code: Course code (e.g., "EE101")
            modules: List of module dictionaries with lessons
            
        Returns:
            List of embedding results for all lessons and slides
        """
        texts = []
        metadata_list = []
        
        for module in modules:
            module_code = module.get('code', '')
            
            for lesson in module.get('lessons', []):
                lesson_code = lesson.get('code', '')
                lesson_body = lesson.get('body', '')
                bloom_level = lesson.get('bloom_level', '')
                co_mapping = lesson.get('co_mapping', [])
                
                # Embed lesson body
                if lesson_body:
                    texts.append(lesson_body)
                    metadata_list.append(EmbeddingMetadata(
                        course_id=course_id,
                        course_code=course_code,
                        module_id=module_code,
                        lesson_id=lesson_code,
                        bloom_level=bloom_level,
                        co_mapping=co_mapping,
                        content_type='lesson'
                    ))
                
                # Embed slide bullets
                slide_outline = lesson.get('slide_outline', {})
                for slide_idx, slide in enumerate(slide_outline.get('slides', [])):
                    slide_text = f"{slide.get('title', '')}\n" + "\n".join(slide.get('bullets', []))
                    if slide_text.strip():
                        texts.append(slide_text)
                        metadata_list.append(EmbeddingMetadata(
                            course_id=course_id,
                            course_code=course_code,
                            module_id=module_code,
                            lesson_id=f"{lesson_code}_slide_{slide_idx + 1}",
                            bloom_level=bloom_level,
                            co_mapping=co_mapping,
                            content_type='slide'
                        ))
        
        logger.info(f"Preparing to embed {len(texts)} content items for course {course_code}")
        return await self.embed_batch(texts, metadata_list)
