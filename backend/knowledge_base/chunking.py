import hashlib

from config.settings import settings

from .models import KnowledgeChunk, KnowledgeDocument


def chunk_document(document: KnowledgeDocument) -> list[KnowledgeChunk]:
    words = document.text.split()
    chunks = []
    start = 0
    chunk_index = 0
    step = max(1, settings.KNOWLEDGE_CHUNK_SIZE - settings.KNOWLEDGE_CHUNK_OVERLAP)

    while start < len(words):
        end = min(start + settings.KNOWLEDGE_CHUNK_SIZE, len(words))
        chunk_text = " ".join(words[start:end])
        chunk_id = _chunk_id(document.source_path, document.content_hash or "", chunk_index)

        chunks.append(
            KnowledgeChunk(
                id=chunk_id,
                text=chunk_text,
                document=document.title,
                title=document.title,
                source_path=document.source_path,
                category=document.category,
                tags=document.tags,
                topic=document.topic,
                content_type=document.content_type,
                version=document.version or (document.content_hash or "")[:12],
                content_hash=document.content_hash or "",
                chunk_index=chunk_index,
                start_word=start,
                end_word=end,
            )
        )

        start += step
        chunk_index += 1

    return chunks


def _chunk_id(source_path: str, content_hash: str, chunk_index: int) -> str:
    raw_id = f"{source_path}:{content_hash}:{chunk_index}"
    return hashlib.sha256(raw_id.encode("utf-8")).hexdigest()
