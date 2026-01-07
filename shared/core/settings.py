from pydantic_settings import BaseSettings
from typing import Optional

class BaseAppSettings(BaseSettings):
    APP_NAME: str = "OBE Platform Service"
    DEBUG: bool = False
    VERSION: str = "0.1.0"
    
    # Database
    DATABASE_URL: Optional[str] = None
    
    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    
    # LLM Configuration
    GEMINI_API_KEY: Optional[str] = None
    PRIMARY_LLM_MODEL: str = "models/gemini-2.0-flash-lite"
    FALLBACK_LLM_MODEL: str = "models/gemini-2.0-flash-exp"
    ADVANCED_LLM_MODEL: str = "models/gemini-2.0-pro-exp"
    ENABLE_LLM_FALLBACK: bool = True
    
    # Embedding Configuration
    EMBEDDING_MODEL: str = "models/text-embedding-004"

    class Config:
        env_file = ".env"
        extra = "ignore"
