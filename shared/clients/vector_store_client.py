
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy import create_engine, text, Column, Integer, String, JSON, func
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy import Index
from pgvector.sqlalchemy import Vector

logger = logging.getLogger(__name__)

Base = declarative_base()

class Embedding(Base):
    __tablename__ = 'embeddings'

    id = Column(Integer, primary_key=True)
    content = Column(String)
    embedding = Column(Vector(768))
    source = Column(String)
    metadata_json = Column("metadata", JSON, nullable=True)
    search_text = Column(TSVECTOR) # For keyword search

    __table_args__ = (
        Index('ix_embeddings_search_text', 'search_text', postgresql_using='gin'),
    )

class PGVectorClient:
    """
    Vector Store Client using PostgreSQL + pgvector.
    """
    def __init__(self, database_url: str):
        self.engine = create_engine(database_url)
        self.Session = sessionmaker(bind=self.engine)
        
        # Ensure extension exists
        with self.engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
            
        # Create tables
        Base.metadata.create_all(self.engine)
        logger.info("PGVectorClient initialized")

    def add_documents(self, texts: List[str], embeddings: List[List[float]], metadatas: Optional[List[Dict[str, Any]]] = None):
        """
        Add documents and their embeddings to the store.
        """
        session = self.Session()
        try:
            for i, text_content in enumerate(texts):
                meta = metadatas[i] if metadatas else {}
                embedding_vector = embeddings[i]
                
                doc = Embedding(
                    content=text_content,
                    embedding=embedding_vector,
                    source=meta.get('source', 'unknown'),
                    metadata_json=meta,
                    search_text=func.to_tsvector('english', text_content)
                )
                session.add(doc)
            session.commit()
            logger.info(f"Added {len(texts)} documents to vector store")
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to add documents: {e}")
            raise
        finally:
            session.close()

    def search(self, query_vector: List[float], top_k: int = 5, threshold: float = 0.5, filter: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Search for similar documents using cosine similarity.
        Supports filtering by metadata fields (exact match).
        """
        session = self.Session()
        try:
            query = session.query(
                Embedding,
                Embedding.embedding.cosine_distance(query_vector).label('distance')
            )
            
            # Apply metadata filters
            if filter:
                logger.info(f"🔎 Applying Vector Filter: {filter}")
                for key, value in filter.items():
                    query = query.filter(func.json_extract_path_text(Embedding.metadata_json, key) == str(value))
            else:
                 logger.info("🔎 No Vector Filter applied")

            results = query.order_by(
                Embedding.embedding.cosine_distance(query_vector)
            ).limit(top_k).all()
            
            logger.info(f"🔎 Found {len(results)} raw results (before threshold)")
            
            formatted_results = []
            for doc, distance in results:
                similarity = 1 - distance
                if similarity >= threshold:
                    formatted_results.append({
                        'content': doc.content,
                        'metadata': doc.metadata_json,
                        'score': similarity
                    })
            
            return formatted_results
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
        finally:
            session.close()

    def search_keyword(self, query_text: str, top_k: int = 5, filter: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Full-text search using Postgres TSVECTOR.
        """
        session = self.Session()
        try:
            # Prepare TSQUERY
            ts_query = func.plainto_tsquery('english', query_text)
            
            query = session.query(
                Embedding, 
                func.ts_rank(Embedding.search_text, ts_query).label('rank')
            ).filter(Embedding.search_text.op('@@')(ts_query))

            if filter:
                 for key, value in filter.items():
                    query = query.filter(func.json_extract_path_text(Embedding.metadata_json, key) == str(value))
            
            results = query.order_by(text('rank DESC')).limit(top_k).all()
            
            formatted_results = []
            for doc, rank in results:
                formatted_results.append({
                    'content': doc.content,
                    'metadata': doc.metadata_json,
                    'score': float(rank),
                     'id': doc.id
                })
            return formatted_results
        except Exception as e:
            logger.error(f"Keyword search failed: {e}")
            return []
        finally:
            session.close()
