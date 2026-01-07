import logging
import httpx
from typing import List, Dict, Any
from .contracts import EvidenceItem, EvidenceSourceType
from .settings import settings

logger = logging.getLogger(__name__)

async def retrieve_evidence(course_id: int, topic_ids: List[Dict[str, str]], k: int = 3) -> Dict[str, List[Dict[str, Any]]]:
    """
    Retrieves evidence snippets for each topic from the RAG Indexer Service.
    """
    try:
        # Construct Request Payload
        payload = {
            "course_id": course_id,
            "topic_ids": topic_ids, # [{"topic_id":..., "topic_name":...}] matches API model
            "k": k
        }
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{settings.RAG_INDEXER_URL}/retrieve",
                json=payload,
                timeout=30.0
            )
            resp.raise_for_status()
            results_map = resp.json()
            
            # Post-process if needed to ensure EvidenceItem compatibility
            # API returns dicts that look like EvidenceItems, so we might pass them through
            # or minimally validate.
            
            # Ensure return type matches Dict[str, List[Dict]]
            return results_map

    except Exception as e:
        logger.error(f"Error retrieving evidence from RAG service: {e}")
        # Return empty map on failure to avoid blocking generation
        return {t["topic_id"]: [] for t in topic_ids}

def retrieve_evidence_sync(course_id: int, query: str, k: int = 3) -> list:
    """
    Synchronous version of retrieve_evidence for use in deterministic generators.
    """
    url = f"{settings.RAG_INDEXER_URL}/retrieve"
    # Note: RAG Indexer /retrieve expects {"query":...} for simpler endpoint or we adapt?
    # RAG Indexer ONLY has /retrieve which calls `indexer.retrieve` which takes `query`.
    # Wait, `course-lifecycle/evidence_retriever` calls `retrieve_evidence` which sends `topic_ids`?
    # Let's check `rag-indexer/main.py`.
    # User requested REAL RAG reachable.
    
    # Assuming RAG Indexer has a new /retrieve endpoint that takes Query string?
    # The current `retrieve_evidence` sends `topic_ids` to... where?
    # Let's check rag-indexer endpoints in Phase 2.
    
    # FIX: Adaptation to match `rag-indexer` RetrieveRequest contract
    # Convert single query to list of topic requests
    # Use "manual_query" as topic_id to distinguish
    payload = {
        "course_id": course_id,
        "topic_ids": [{"topic_id": "manual_query", "topic_name": query}],
        "k": k
    }
    
    try:
        # Use a new client sync
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(url, json=payload)
            if resp.status_code == 200:
                # Expecting Dict[str, List[EvidenceItem]]
                # We extract the list for our "manual_query" topic
                data = resp.json()
                return data.get("manual_query", [])
            else:
                logger.warning(f"RAG Sync Retrieve failed: {resp.status_code} - {resp.text}")
                return []
    except Exception as e:
        logger.error(f"RAG Sync Retrieve Exception: {e}")
        return []
