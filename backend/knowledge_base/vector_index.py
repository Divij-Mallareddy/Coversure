import json
from dataclasses import asdict
from pathlib import Path

import faiss
import numpy as np

from config.settings import settings
from services.embeddings import get_embedding_dimension


class KnowledgeVectorIndex:
    def __init__(self, index_dir: Path, dimension: int | None = None):
        self.index_dir = index_dir
        self.dimension = dimension or get_embedding_dimension()
        self.index_path = index_dir / "knowledge.faiss"
        self.metadata_path = index_dir / "chunks.json"
        self.manifest_path = index_dir / "manifest.json"
        self.index = faiss.IndexFlatIP(self.dimension)
        self.metadata: list[dict] = []
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.load()

    @property
    def is_empty(self) -> bool:
        return self.index.ntotal == 0

    def load(self) -> None:
        if not self.index_path.exists() or not self.metadata_path.exists():
            self.reset()
            return

        self.index = faiss.read_index(str(self.index_path))
        self.dimension = self.index.d
        self.metadata = json.loads(self.metadata_path.read_text(encoding="utf-8"))

    def save(self, manifest: dict | None = None) -> None:
        faiss.write_index(self.index, str(self.index_path))
        self.metadata_path.write_text(json.dumps(self.metadata, indent=2), encoding="utf-8")
        if manifest is not None:
            self.manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    def reset(self) -> None:
        self.index = faiss.IndexFlatIP(self.dimension)
        self.metadata = []

    def replace(self, chunks: list, embeddings: list[list[float]], manifest: dict) -> None:
        self.reset()
        if chunks:
            vectors = _normalize(np.array(embeddings, dtype=np.float32))
            self._ensure_dimension(vectors.shape[1])
            self.index.add(vectors)
            self.metadata = [asdict(chunk) for chunk in chunks]
        self.save(manifest)

    def search(self, query_embedding: list[float], top_k: int | None = None) -> list[dict]:
        if self.is_empty:
            return []

        limit = top_k or settings.KNOWLEDGE_TOP_K
        query_vector = _normalize(np.array([query_embedding], dtype=np.float32))
        scores, indices = self.index.search(query_vector, min(limit, self.index.ntotal))

        results = []
        for score, index in zip(scores[0], indices[0]):
            if index == -1 or index >= len(self.metadata):
                continue
            confidence = float(max(0.0, min(1.0, score)))
            if confidence < settings.KNOWLEDGE_MIN_CONFIDENCE:
                continue
            item = dict(self.metadata[index])
            item["score"] = confidence
            item["similarity_score"] = confidence
            item["confidence"] = confidence
            item["metadata"] = {
                "page": item.get("page"),
                "heading": item.get("heading"),
                "section": item.get("section"),
                "source_document": item.get("source_path") or item.get("document"),
            }
            results.append(item)
        return results

    def read_manifest(self) -> dict:
        if not self.manifest_path.exists():
            return {}
        return json.loads(self.manifest_path.read_text(encoding="utf-8"))

    def _ensure_dimension(self, dimension: int) -> None:
        if dimension == self.dimension:
            return
        if self.index.ntotal > 0:
            raise ValueError(f"Embedding dimension changed from {self.dimension} to {dimension}. Rebuild the knowledge index.")
        self.dimension = dimension
        self.index = faiss.IndexFlatIP(self.dimension)


def _normalize(vectors: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1
    return vectors / norms
