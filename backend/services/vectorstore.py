import json
import logging
from pathlib import Path

import faiss
import numpy as np

from config.settings import settings
from services.embeddings import get_embedding_dimension

logger = logging.getLogger("services.vectorstore")

class VectorStore:
    def __init__(self, name: str, dimension: int | None = None):
        self.name = name
        self.dimension = dimension or get_embedding_dimension()
        self.index = faiss.IndexFlatIP(self.dimension)
        self.metadata = []
        self.index_dir = Path(settings.KNOWLEDGE_INDEX_DIR) / "session"
        self.index_path = self.index_dir / f"{name}.faiss"
        self.metadata_path = self.index_dir / f"{name}_chunks.json"
        self.load()

    def add_chunks(self, chunks: list[dict], embeddings: list[list[float]]):
        if not chunks or not embeddings:
            return
        embeddings_np = _normalize(np.array(embeddings, dtype=np.float32))
        self._ensure_dimension(embeddings_np.shape[1])
        self.index.add(embeddings_np)
        self.metadata.extend(chunks)
        self.save()

    def search(self, query_embedding: list[float], top_k: int = 5) -> list[dict]:
        if self.index.ntotal == 0:
            return []

        limit = min(max(top_k, settings.FINAL_TOP_K), self.index.ntotal)
        q_emb = _normalize(np.array([query_embedding], dtype=np.float32))
        scores, indices = self.index.search(q_emb, limit)

        results = []
        seen_texts = set()
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1 or idx >= len(self.metadata):
                continue
            confidence = float(max(0.0, min(1.0, score)))
            if confidence < settings.SIMILARITY_THRESHOLD:
                continue

            result = dict(self.metadata[idx])
            fingerprint = _text_fingerprint(result.get("text", ""))
            if settings.ENABLE_DUPLICATE_FILTER and fingerprint in seen_texts:
                continue
            seen_texts.add(fingerprint)

            result["score"] = confidence
            result["similarity_score"] = confidence
            result["confidence"] = confidence
            result["source_type"] = "uploaded_document"
            result["metadata"] = _metadata_for(result)
            results.append(result)
        return results

    def load(self) -> None:
        if not self.index_path.exists() or not self.metadata_path.exists():
            return
        try:
            self.index = faiss.read_index(str(self.index_path))
            self.dimension = self.index.d
            self.metadata = json.loads(self.metadata_path.read_text(encoding="utf-8"))
            logger.info("Loaded %s vector store with %s chunks", self.name, self.index.ntotal)
        except Exception as exc:
            logger.warning("Could not load %s vector store: %s", self.name, exc)
            self.reset(save=False)

    def save(self) -> None:
        self.index_dir.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(self.index_path))
        self.metadata_path.write_text(json.dumps(self.metadata, indent=2), encoding="utf-8")

    def reset(self, save: bool = True):
        self.index = faiss.IndexFlatIP(self.dimension)
        self.metadata = []
        if save:
            self.save()

    def _ensure_dimension(self, dimension: int) -> None:
        if dimension == self.dimension:
            return
        if self.index.ntotal > 0:
            raise ValueError(f"Embedding dimension changed from {self.dimension} to {dimension}. Clear/rebuild the store.")
        self.dimension = dimension
        self.index = faiss.IndexFlatIP(self.dimension)


def _normalize(vectors: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1
    return vectors / norms


def _text_fingerprint(text: str) -> str:
    return " ".join(text.lower().split()[:80])


def _metadata_for(chunk: dict) -> dict:
    metadata = dict(chunk.get("metadata") or {})
    metadata.setdefault("page", chunk.get("page"))
    metadata.setdefault("pages", chunk.get("pages", []))
    metadata.setdefault("heading", chunk.get("heading"))
    metadata.setdefault("section", chunk.get("section"))
    metadata.setdefault("source_document", chunk.get("source_document") or chunk.get("document"))
    return metadata

# Instantiate our stores
single_store = VectorStore("single")
multi_store = VectorStore("multi")
