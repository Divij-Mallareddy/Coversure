import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    CHUNK_SIZE: int = 400
    CHUNK_OVERLAP: int = 50
    TOP_K_RETRIEVAL: int = 5
    KNOWLEDGE_BASE_DIR: str = "knowledge_base/content"
    KNOWLEDGE_INDEX_DIR: str = "knowledge_base/index"
    KNOWLEDGE_CHUNK_SIZE: int = 450
    KNOWLEDGE_CHUNK_OVERLAP: int = 75
    KNOWLEDGE_TOP_K: int = 6
    KNOWLEDGE_MIN_CONFIDENCE: float = 0.22
    KNOWLEDGE_SCAN_CACHE_SECONDS: int = 15
    KNOWLEDGE_INDEX_VERSION: str = "1"

    class Config:
        env_file = ".env"

settings = Settings()
