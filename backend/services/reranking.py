import logging
import re
import time

from sentence_transformers import CrossEncoder

from config.settings import settings

logger = logging.getLogger("services.reranking")

_reranker: CrossEncoder | None = None


def rerank_chunks(query: str, chunks: list[dict], top_k: int | None = None) -> list[dict]:
    if not chunks:
        return []

    start = time.perf_counter()
    limit = top_k or settings.FINAL_TOP_K
    _validate_chunks(chunks)
    logger.info(
        "Rerank input: chunks=%s top_k=%s sample_keys=%s",
        len(chunks),
        limit,
        sorted(chunks[0].keys()) if chunks else [],
    )

    if not settings.ENABLE_RERANKING:
        reranked = sorted(
            chunks,
            key=lambda chunk: float(chunk.get("confidence") or chunk.get("score") or 0.0),
            reverse=True,
        )[:limit]
    elif settings.RERANKER_MODEL == "dummy_reranker":
        reranked = _lexical_rerank(query, chunks, limit)
    else:
        reranked = _model_rerank(query, chunks, limit)

    logger.info(
        "Reranked %s chunks to %s in %.3fs",
        len(chunks),
        len(reranked),
        time.perf_counter() - start,
    )
    return reranked


def _model_rerank(query: str, chunks: list[dict], limit: int) -> list[dict]:
    global _reranker
    if _reranker is None:
        logger.info("Loading reranker model: %s", settings.RERANKER_MODEL)
        try:
            _reranker = CrossEncoder(settings.RERANKER_MODEL)
        except Exception:
            logger.exception("Failed to load reranker model '%s'", settings.RERANKER_MODEL)
            raise

    pairs = [(query, chunk.get("text", "")) for chunk in chunks]
    logger.info("Reranker pairs prepared: %s", len(pairs))
    try:
        raw_scores = _reranker.predict(pairs)
    except Exception:
        logger.exception("Reranker prediction failed")
        raise

    scored_chunks = []
    for chunk, raw_score in zip(chunks, raw_scores):
        rerank_score = _sigmoid(float(raw_score))
        if rerank_score < settings.RERANK_THRESHOLD:
            continue
        scored_chunks.append(_with_scores(chunk, rerank_score))
    return sorted(scored_chunks, key=lambda item: item["confidence"], reverse=True)[:limit]


def _lexical_rerank(query: str, chunks: list[dict], limit: int) -> list[dict]:
    query_terms = set(_terms(query))
    scored_chunks = []
    for chunk in chunks:
        chunk_terms = set(_terms(chunk.get("text", "")))
        overlap = len(query_terms & chunk_terms)
        lexical_score = overlap / max(1, len(query_terms))
        base_score = float(chunk.get("confidence") or chunk.get("score") or 0.0)
        rerank_score = max(lexical_score, base_score * 0.85)
        if rerank_score < settings.RERANK_THRESHOLD and base_score < settings.SIMILARITY_THRESHOLD:
            continue
        scored_chunks.append(_with_scores(chunk, rerank_score))
    return sorted(scored_chunks, key=lambda item: item["confidence"], reverse=True)[:limit]


def _with_scores(chunk: dict, rerank_score: float) -> dict:
    item = dict(chunk)
    base_score = float(item.get("similarity_score") or item.get("score") or item.get("confidence") or 0.0)
    confidence = (base_score * 0.45) + (rerank_score * 0.55)
    item["rerank_score"] = float(rerank_score)
    item["confidence"] = float(max(0.0, min(1.0, confidence)))
    return item


def _terms(text: str) -> list[str]:
    return [_normalize_term(term) for term in re.findall(r"[a-zA-Z0-9]{3,}", text.lower())]


def _normalize_term(term: str) -> str:
    for suffix in ("ing", "ed", "es", "s"):
        if len(term) > len(suffix) + 3 and term.endswith(suffix):
            return term[: -len(suffix)]
    return term


def _sigmoid(value: float) -> float:
    return 1.0 / (1.0 + pow(2.718281828, -value))


def _validate_chunks(chunks: list[dict]) -> None:
    for index, chunk in enumerate(chunks):
        if not isinstance(chunk, dict):
            raise TypeError(f"Reranker expected dict chunk at index {index}, got {type(chunk).__name__}")
        if not chunk.get("text"):
            raise ValueError(f"Reranker chunk at index {index} is missing non-empty 'text'")
