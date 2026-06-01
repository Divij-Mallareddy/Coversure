import logging
import time

from groq import Groq
from config.settings import settings

logger = logging.getLogger("services.rag")

def query_rag(query: str, retrieved_chunks: list[dict], mode: str) -> dict:
    if not retrieved_chunks:
        return {
            "answer": "Not mentioned in document",
            "confidence": 0.0,
            "sources": [],
            "retrieved_chunks": [],
            "retrieval_scores": [],
        }

    start = time.perf_counter()
    source_details = [_source_detail(chunk) for chunk in retrieved_chunks]
    sources = sorted({source["label"] for source in source_details})
    context_text = "\n\n".join([_format_context_chunk(chunk) for chunk in retrieved_chunks])
    prompt = _build_prompt(query, context_text, mode)
    logger.info(
        "Prompt build: chunks=%s sources=%s prompt_chars=%s sample_chunk_keys=%s",
        len(retrieved_chunks),
        len(sources),
        len(prompt),
        sorted(retrieved_chunks[0].keys()) if retrieved_chunks else [],
    )

    if settings.LLM_MODEL == "dummy_llm":
        answer = "LLM model is configured as dummy_llm. Set LLM_MODEL in config/settings.py or .env to generate grounded answers."
    else:
        client = Groq(api_key=settings.GROQ_API_KEY)
        try:
            logger.info("Calling Groq model=%s", settings.LLM_MODEL)
            completion = client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a careful insurance policy QA assistant. Ground every answer in the supplied context.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,
            )
            answer = _extract_answer(completion)
            logger.info("Groq response received: answer_chars=%s", len(answer))
        except Exception:
            logger.exception("Groq request failed")
            raise

    confidence = _overall_confidence(retrieved_chunks)
    logger.info(
        "LLM response generated in %.3fs with confidence %.3f and %s sources",
        time.perf_counter() - start,
        confidence,
        len(sources),
    )

    return {
        "answer": answer,
        "confidence": confidence,
        "sources": sources,
        "source_details": source_details,
        "retrieved_chunks": [_retrieved_chunk_summary(chunk) for chunk in retrieved_chunks],
        "retrieval_scores": [_retrieval_score(chunk) for chunk in retrieved_chunks],
    }


def _format_context_chunk(chunk: dict) -> str:
    metadata = chunk.get("metadata") or {}
    source = chunk.get("source_path") or chunk.get("document") or "Unknown"
    category = chunk.get("category", "session")
    tags = ", ".join(chunk.get("tags", [])) if chunk.get("tags") else "none"
    confidence = chunk.get("confidence")
    confidence_line = f"Confidence: {confidence:.3f}\n" if isinstance(confidence, float) else ""
    return (
        "<chunk>\n"
        f"<source_type>{chunk.get('source_type', 'unknown')}</source_type>\n"
        f"<source>{source}</source>\n"
        f"<document>{chunk.get('document', chunk.get('title', 'Unknown'))}</document>\n"
        f"<page>{metadata.get('page') or chunk.get('page') or ''}</page>\n"
        f"<heading>{metadata.get('heading') or chunk.get('heading') or chunk.get('section') or ''}</heading>\n"
        f"<section>{metadata.get('section') or chunk.get('section') or ''}</section>\n"
        f"<category>{category}</category>\n"
        f"<tags>{tags}</tags>\n"
        f"{confidence_line}"
        f"<text>{chunk.get('text', '')}</text>\n"
        "</chunk>"
    )


def _source_detail(chunk: dict) -> dict:
    metadata = chunk.get("metadata") or {}
    label = chunk.get("source_path") or chunk.get("document") or "Unknown"
    return {
        "label": label,
        "title": chunk.get("title") or chunk.get("document") or label,
        "category": chunk.get("category", "session"),
        "tags": chunk.get("tags", []),
        "source_type": chunk.get("source_type", "unknown"),
        "confidence": chunk.get("confidence"),
        "page": metadata.get("page") or chunk.get("page"),
        "heading": metadata.get("heading") or chunk.get("heading") or chunk.get("section"),
        "version": chunk.get("version"),
    }


def _build_prompt(query: str, context_text: str, mode: str) -> str:
    return f"""<task>
Answer the user's insurance policy question using ONLY <retrieved_context>.
If the answer is absent, reply exactly: Not mentioned in document
Never invent coverage, exclusions, prices, benefits, waiting periods, or policy rules.
Quote short clauses when useful.
Mention the source document for important facts.
If sources conflict, explain the conflict and name the documents.
For comparisons, separate points by policy/document.
</task>

<retrieval_mode>{mode}</retrieval_mode>

<retrieved_context>
{context_text}
</retrieved_context>

<question>
{query}
</question>
"""


def _overall_confidence(chunks: list[dict]) -> float:
    if not chunks:
        return 0.0
    scores = [float(chunk.get("confidence") or 0.0) for chunk in chunks]
    top_scores = sorted(scores, reverse=True)[:3]
    return round(sum(top_scores) / len(top_scores), 3)


def _retrieved_chunk_summary(chunk: dict) -> dict:
    metadata = chunk.get("metadata") or {}
    return {
        "text": chunk.get("text", "")[:700],
        "metadata": metadata,
        "source_document": metadata.get("source_document") or chunk.get("source_document") or chunk.get("source_path") or chunk.get("document"),
        "page": metadata.get("page") or chunk.get("page"),
        "heading": metadata.get("heading") or chunk.get("heading") or chunk.get("section"),
        "source_type": chunk.get("source_type"),
        "confidence": chunk.get("confidence"),
    }


def _retrieval_score(chunk: dict) -> dict:
    return {
        "source": chunk.get("source_path") or chunk.get("document"),
        "similarity_score": chunk.get("similarity_score") or chunk.get("score"),
        "rerank_score": chunk.get("rerank_score"),
        "confidence": chunk.get("confidence"),
    }


def _extract_answer(completion) -> str:
    choices = getattr(completion, "choices", None)
    if not choices:
        raise ValueError("Groq returned no choices")
    message = getattr(choices[0], "message", None)
    answer = getattr(message, "content", None)
    if not answer:
        raise ValueError("Groq returned an empty message content")
    return answer
