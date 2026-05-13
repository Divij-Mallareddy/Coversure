from groq import Groq
from config.settings import settings

def query_rag(query: str, retrieved_chunks: list[dict], mode: str) -> dict:
    if not retrieved_chunks:
        return {"answer": "Not mentioned in the document", "sources": []}

    source_details = [_source_detail(chunk) for chunk in retrieved_chunks]
    sources = sorted({source["label"] for source in source_details})
    context_text = "\n\n".join([_format_context_chunk(chunk) for chunk in retrieved_chunks])
    
    if mode == "knowledge_base":
        prompt = f"""You are an insurance knowledge-base assistant. Answer using ONLY the provided backend knowledge-base context.
Prioritize the retrieved company/policy knowledge over general knowledge.
If the context does not contain the answer, say "Not mentioned in the knowledge base."
Do not invent coverage, exclusions, prices, benefits, or policy rules.

Context:
{context_text}

Question:
{query}
"""
    elif mode == "hybrid":
        prompt = f"""You are an insurance expert. Answer using ONLY the provided context.
Backend knowledge-base context is authoritative. Uploaded session documents may add user-specific context.
If sources disagree, mention the conflict and identify the source.
If the information is missing, say "Not mentioned in the document."

Context:
{context_text}

Question:
{query}
"""
    elif mode == "single":
        prompt = f"""You are an insurance expert. Answer using ONLY the provided context.
If the information is not found in the context, say "Not mentioned in the document."

Context:
{context_text}

Question:
{query}
"""
    else:
        prompt = f"""You are an insurance expert. Answer using ONLY the provided context.
If multiple policies are present, compare them clearly.
Mention which policy each point belongs to.
If information is missing, say "Not mentioned in the document."

Context:
{context_text}

Question:
{query}
"""

    client = Groq(api_key=settings.GROQ_API_KEY)
    
    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0
        )
        answer = completion.choices[0].message.content
    except Exception as e:
        answer = f"Error communicating with LLM: {str(e)}"
        
    return {
        "answer": answer,
        "sources": sources,
        "source_details": source_details,
    }


def _format_context_chunk(chunk: dict) -> str:
    source = chunk.get("source_path") or chunk.get("document") or "Unknown"
    category = chunk.get("category", "session")
    tags = ", ".join(chunk.get("tags", [])) if chunk.get("tags") else "none"
    confidence = chunk.get("confidence")
    confidence_line = f"Confidence: {confidence:.3f}\n" if isinstance(confidence, float) else ""
    return (
        f"Source Type: {chunk.get('source_type', 'unknown')}\n"
        f"Source: {source}\n"
        f"Document: {chunk.get('document', chunk.get('title', 'Unknown'))}\n"
        f"Category: {category}\n"
        f"Tags: {tags}\n"
        f"{confidence_line}"
        f"Text: {chunk.get('text', '')}"
    )


def _source_detail(chunk: dict) -> dict:
    label = chunk.get("source_path") or chunk.get("document") or "Unknown"
    return {
        "label": label,
        "title": chunk.get("title") or chunk.get("document") or label,
        "category": chunk.get("category", "session"),
        "tags": chunk.get("tags", []),
        "source_type": chunk.get("source_type", "unknown"),
        "confidence": chunk.get("confidence"),
        "version": chunk.get("version"),
    }
