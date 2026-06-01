import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):

    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

    EMBEDDING_MODEL: str = "BAAI/bge-large-en-v1.5"

    RERANKER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    LLM_MODEL: str = "llama-3.3-70b-versatile"

    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 100

    TOP_K_RETRIEVAL: int = 15
    FINAL_TOP_K: int = 5

    KNOWLEDGE_BASE_DIR: str = "knowledge_base/content"
    KNOWLEDGE_INDEX_DIR: str = "knowledge_base/index"

    KNOWLEDGE_CHUNK_SIZE: int = 450
    KNOWLEDGE_CHUNK_OVERLAP: int = 75

    KNOWLEDGE_TOP_K: int = 6
    KNOWLEDGE_MIN_CONFIDENCE: float = 0.22

    SIMILARITY_THRESHOLD: float = 0.30
    RERANK_THRESHOLD: float = 0.35

    ENABLE_RERANKING: bool = False
    ENABLE_CACHE: bool = True
    ENABLE_DUPLICATE_FILTER: bool = True

    KNOWLEDGE_SCAN_CACHE_SECONDS: int = 15

    KNOWLEDGE_INDEX_VERSION: str = "2"

    class Config:
        env_file = ".env"

settings = Settings()
