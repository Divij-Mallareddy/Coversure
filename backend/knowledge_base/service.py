import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from config.settings import settings
from services.embeddings import get_embeddings

from .chunking import chunk_document
from .loaders import file_fingerprint, load_document
from .models import SUPPORTED_EXTENSIONS
from .vector_index import KnowledgeVectorIndex

logger = logging.getLogger("knowledge_base")


class KnowledgeBaseService:
    def __init__(self):
        self.content_root = Path(settings.KNOWLEDGE_BASE_DIR)
        self.index_dir = Path(settings.KNOWLEDGE_INDEX_DIR)
        self.vector_index = KnowledgeVectorIndex(self.index_dir)
        self._last_scan_at = 0.0

    def sync(self, force: bool = False, use_cache: bool = True) -> dict:
        self.content_root.mkdir(parents=True, exist_ok=True)
        self.index_dir.mkdir(parents=True, exist_ok=True)

        if not force and use_cache and not self._scan_cache_expired():
            return self.status()

        current_manifest = self._build_manifest()
        previous_manifest = self.vector_index.read_manifest()
        self._last_scan_at = time.time()

        if not force and self._manifests_match(previous_manifest, current_manifest):
            return self.status()

        return self.rebuild(current_manifest)

    def rebuild(self, manifest: dict | None = None) -> dict:
        self.content_root.mkdir(parents=True, exist_ok=True)
        manifest = manifest or self._build_manifest()

        documents = []
        for file_info in manifest["files"]:
            file_path = self.content_root / file_info["path"]
            document = load_document(file_path, self.content_root)
            if document:
                documents.append(document)

        chunks = []
        for document in documents:
            chunks.extend(chunk_document(document))

        embeddings = get_embeddings([chunk.text for chunk in chunks]) if chunks else []
        manifest.update(
            {
                "indexed_at": datetime.now(timezone.utc).isoformat(),
                "document_count": len(documents),
                "chunk_count": len(chunks),
            }
        )
        self.vector_index.replace(chunks, embeddings, manifest)

        logger.info(
            "Knowledge base rebuilt: %s documents, %s chunks",
            len(documents),
            len(chunks),
        )
        return self.status()

    def retrieve(self, query: str, selected_docs: list[str] | None = None, top_k: int | None = None) -> list[dict]:
        self.sync()
        if self.vector_index.is_empty:
            return []

        query_embedding = get_embeddings([query])[0]
        selected_doc_ids = {doc for doc in selected_docs or [] if doc}
        search_top_k = self.vector_index.index.ntotal if selected_doc_ids else top_k
        results = self.vector_index.search(query_embedding, top_k=search_top_k)
        if selected_doc_ids:
            results = [
                result
                for result in results
                if result.get("source_path") in selected_doc_ids
            ][: top_k or settings.KNOWLEDGE_TOP_K]
        if results:
            source_log = [
                {
                    "source": result["source_path"],
                    "title": result["title"],
                    "confidence": round(result["confidence"], 3),
                }
                for result in results
            ]
            logger.info("Retrieved knowledge sources: %s", source_log)
        return results

    def documents(self) -> list[dict]:
        self.sync()
        manifest = self.vector_index.read_manifest()
        docs = []

        for file in manifest.get("files", []):
            path = file.get("path")
            if not path:
                continue

            name = Path(path).stem
            title = (
                name.replace("-", " ")
                .replace("_", " ")
                .title()
            )

            docs.append(
                {
                    "id": path.replace("\\", "/"),
                    "title": title,
                }
            )

        return docs

    def status(self) -> dict:
        manifest = self.vector_index.read_manifest()
        return {
            "content_root": str(self.content_root),
            "index_dir": str(self.index_dir),
            "indexed": not self.vector_index.is_empty,
            "documents": manifest.get("document_count", 0),
            "chunks": manifest.get("chunk_count", self.vector_index.index.ntotal),
            "indexed_at": manifest.get("indexed_at"),
            "index_version": manifest.get("index_version", settings.KNOWLEDGE_INDEX_VERSION),
            "supported_extensions": sorted(SUPPORTED_EXTENSIONS),
            "files": manifest.get("files", []),
        }

    def _build_manifest(self) -> dict:
        files = []
        for file_path in sorted(self.content_root.rglob("*")):
            if not file_path.is_file() or file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue
            files.append(file_fingerprint(file_path, self.content_root))

        return {
            "index_version": settings.KNOWLEDGE_INDEX_VERSION,
            "embedding_model": settings.EMBEDDING_MODEL,
            "chunk_size": settings.KNOWLEDGE_CHUNK_SIZE,
            "chunk_overlap": settings.KNOWLEDGE_CHUNK_OVERLAP,
            "files": files,
        }

    def _manifests_match(self, previous: dict, current: dict) -> bool:
        fields = ("index_version", "embedding_model", "chunk_size", "chunk_overlap", "files")
        return all(previous.get(field) == current.get(field) for field in fields)

    def _scan_cache_expired(self) -> bool:
        return (time.time() - self._last_scan_at) >= settings.KNOWLEDGE_SCAN_CACHE_SECONDS


knowledge_base = KnowledgeBaseService()
