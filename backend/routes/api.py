from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Body
from pydantic import BaseModel, Field
import logging
import time

from services.pdf import extract_text_from_pdf
from services.chunking import chunk_text
from services.embeddings import get_embeddings
from services.vectorstore import single_store, multi_store
from services.rag import query_rag
from services.reranking import rerank_chunks
from config.settings import settings
from knowledge_base.service import knowledge_base

router = APIRouter()
logger = logging.getLogger("routes.api")


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1)
    selected_docs: list[str] = Field(default_factory=list)

@router.post("/upload/")
async def upload_pdf(file: UploadFile = File(...), append: bool = Form(False)):
    start = time.perf_counter()
    mode = "memory" if append else "single"
    # 1. Extract text
    text = extract_text_from_pdf(file)
    if not text:
        raise HTTPException(status_code=400, detail="Could not extract text from PDF")

    # 2. Chunking
    chunks = chunk_text(text, file.filename)
    logger.info(
        "Chunking stage: file=%s chunks=%s sample=%s",
        file.filename,
        len(chunks),
        _chunk_debug(chunks[0]) if chunks else {},
    )
    
    # 3. Embeddings
    texts = [c["text"] for c in chunks]
    embeddings = get_embeddings(texts)
    logger.info(
        "Embedding stage: file=%s vectors=%s dimension=%s",
        file.filename,
        len(embeddings),
        len(embeddings[0]) if embeddings else 0,
    )

    # 4. Store
    if mode == "single":
        single_store.reset()
        single_store.add_chunks(chunks, embeddings)
        logger.info("Uploaded %s into single store: %s chunks in %.3fs", file.filename, len(chunks), time.perf_counter() - start)
        return {"message": "PDF processed successfully in single mode", "chunks": len(chunks)}
    else:
        multi_store.add_chunks(chunks, embeddings)
        logger.info("Uploaded %s into multi store: %s chunks in %.3fs", file.filename, len(chunks), time.perf_counter() - start)
        return {"message": "PDF processed successfully in multi mode", "chunks": len(chunks)}

@router.post("/ask/")
async def ask_question(chat_request: ChatRequest | None = Body(default=None), query: str | None = None):
    start = time.perf_counter()
    question = query or ""
    try:
        question = (chat_request.question if chat_request else question).strip()
        selected_docs = chat_request.selected_docs if chat_request else []
        if not question:
            raise HTTPException(status_code=400, detail="Question is required")

        stage_one_top_k = max(settings.TOP_K_RETRIEVAL, settings.FINAL_TOP_K)
        knowledge_chunks = knowledge_base.retrieve(
            question,
            selected_docs=selected_docs,
            top_k=max(settings.KNOWLEDGE_TOP_K, settings.FINAL_TOP_K),
        )
        session_chunks = []
        session_mode = "single"

        if multi_store.index.ntotal > 0:
            store = multi_store
            session_mode = "memory"
        else:
            store = single_store

        if store.index.ntotal > 0:
            query_emb = get_embeddings([question])[0]
            session_chunks = store.search(query_emb, top_k=stage_one_top_k)

        logger.info(
            "Retrieval stage: query=%r selected_docs=%s knowledge_chunks=%s session_chunks=%s top_k=%s",
            question,
            selected_docs,
            len(knowledge_chunks),
            len(session_chunks),
            stage_one_top_k,
        )

        if not knowledge_chunks and not session_chunks:
            return {"error": "Knowledge base is empty or no relevant context was found."}

        retrieved_chunks = [_normalize_chunk(chunk) for chunk in knowledge_chunks + session_chunks]
        retrieved_chunks = _deduplicate_chunks(retrieved_chunks)
        logger.info(
            "Post-normalization retrieval: chunks=%s sample=%s",
            len(retrieved_chunks),
            _chunk_debug(retrieved_chunks[0]) if retrieved_chunks else {},
        )

        reranked_chunks = rerank_chunks(question, retrieved_chunks, top_k=settings.FINAL_TOP_K)
        logger.info(
            "Rerank output: chunks=%s scores=%s",
            len(reranked_chunks),
            [
                {
                    "source": chunk.get("source_path") or chunk.get("document"),
                    "similarity": chunk.get("similarity_score"),
                    "rerank": chunk.get("rerank_score"),
                    "confidence": chunk.get("confidence"),
                }
                for chunk in reranked_chunks
            ],
        )
        if not reranked_chunks:
            return {
                "answer": "Not mentioned in document",
                "confidence": 0.0,
                "sources": [],
                "retrieved_chunks": [],
                "retrieval_scores": [],
            }

        if knowledge_chunks and session_chunks:
            mode = "hybrid"
        elif knowledge_chunks:
            mode = "knowledge_base"
        else:
            mode = session_mode

        result = query_rag(question, reranked_chunks, mode)
        result["retrieval"] = {
            "mode": mode,
            "knowledge_chunks": len(knowledge_chunks),
            "session_chunks": len(session_chunks),
            "stage_one_chunks": len(retrieved_chunks),
            "final_chunks": len(reranked_chunks),
            "min_knowledge_confidence": settings.KNOWLEDGE_MIN_CONFIDENCE,
            "latency_seconds": round(time.perf_counter() - start, 3),
        }
        logger.info(
            "Query answered mode=%s stage_one=%s final=%s confidence=%s latency=%.3fs",
            mode,
            len(retrieved_chunks),
            len(reranked_chunks),
            result.get("confidence"),
            time.perf_counter() - start,
        )
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Question pipeline failed for query=%r", question)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@router.post("/clear/")
async def clear_memory():
    single_store.reset()
    multi_store.reset()
    return {"message": "Memory cleared completely"}

@router.get("/knowledge/status")
async def knowledge_status():
    return knowledge_base.status()

@router.get("/knowledge/documents")
def get_documents():
    return knowledge_base.documents()

@router.post("/knowledge/sync")
async def sync_knowledge():
    return knowledge_base.sync(use_cache=False)

@router.post("/knowledge/rebuild")
async def rebuild_knowledge():
    return knowledge_base.sync(force=True)


def _deduplicate_chunks(chunks: list[dict]) -> list[dict]:
    if not settings.ENABLE_DUPLICATE_FILTER:
        return chunks

    deduped = []
    seen = set()
    for chunk in chunks:
        text_key = " ".join(chunk.get("text", "").lower().split()[:80])
        source_key = chunk.get("source_path") or chunk.get("document")
        key = (source_key, text_key)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(chunk)
    return deduped


def _normalize_chunk(chunk: dict) -> dict:
    if not isinstance(chunk, dict):
        raise TypeError(f"Expected retrieved chunk to be dict, got {type(chunk).__name__}")

    text = chunk.get("text") or chunk.get("content")
    if not text:
        raise ValueError(f"Retrieved chunk is missing text. Keys: {sorted(chunk.keys())}")

    normalized = dict(chunk)
    normalized["text"] = text
    metadata = dict(normalized.get("metadata") or {})
    metadata.setdefault("page", normalized.get("page"))
    metadata.setdefault("pages", normalized.get("pages", []))
    metadata.setdefault("heading", normalized.get("heading"))
    metadata.setdefault("section", normalized.get("section"))
    metadata.setdefault(
        "source_document",
        normalized.get("source_document") or normalized.get("source_path") or normalized.get("document"),
    )
    normalized["metadata"] = metadata
    normalized.setdefault("score", normalized.get("confidence") or normalized.get("similarity_score") or 0.0)
    normalized.setdefault("confidence", normalized.get("score") or 0.0)
    return normalized


def _chunk_debug(chunk: dict) -> dict:
    return {
        "keys": sorted(chunk.keys()),
        "metadata": chunk.get("metadata"),
        "text_chars": len(chunk.get("text", "")),
        "score": chunk.get("score"),
        "confidence": chunk.get("confidence"),
    }
