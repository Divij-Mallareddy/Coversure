import hashlib
import re

from config.settings import settings

from .models import KnowledgeChunk, KnowledgeDocument


def chunk_document(document: KnowledgeDocument) -> list[KnowledgeChunk]:
    blocks = _split_blocks(document.text)
    chunks = []
    chunk_index = 0
    current_blocks = []
    current_words = 0

    for block in blocks:
        block_words = _word_count(block["text"])
        should_flush = (
            current_blocks
            and current_words + block_words > settings.KNOWLEDGE_CHUNK_SIZE
            and not _should_keep_together(block["text"])
        )
        if should_flush:
            chunks.append(_build_chunk(document, current_blocks, chunk_index))
            current_blocks = _overlap_blocks(current_blocks)
            current_words = sum(_word_count(item["text"]) for item in current_blocks)
            chunk_index += 1

        current_blocks.append(block)
        current_words += block_words

    if current_blocks:
        chunks.append(_build_chunk(document, current_blocks, chunk_index))

    return chunks


def _build_chunk(document: KnowledgeDocument, blocks: list[dict], chunk_index: int) -> KnowledgeChunk:
    chunk_text = "\n".join(block["text"] for block in blocks).strip()
    chunk_id = _chunk_id(document.source_path, document.content_hash or "", chunk_index)
    pages = [block["page"] for block in blocks if block.get("page")]
    headings = [block["heading"] for block in blocks if block.get("heading")]
    heading = headings[-1] if headings else None
    start_word = min(block["start_word"] for block in blocks)
    end_word = max(block["end_word"] for block in blocks)

    return KnowledgeChunk(
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
        start_word=start_word,
        end_word=end_word,
        page=pages[0] if pages else None,
        heading=heading,
        section=heading,
    )


def _chunk_id(source_path: str, content_hash: str, chunk_index: int) -> str:
    raw_id = f"{source_path}:{content_hash}:{chunk_index}"
    return hashlib.sha256(raw_id.encode("utf-8")).hexdigest()


def _split_blocks(text: str) -> list[dict]:
    raw_blocks = re.split(r"\n\s*\n|(?=\[Page \d+\])", text)
    blocks = []
    page = None
    word_offset = 0

    for raw_block in raw_blocks:
        block = raw_block.strip()
        if not block:
            continue
        page_match = re.match(r"\[Page (\d+)\]\s*(.*)", block, flags=re.DOTALL)
        if page_match:
            page = int(page_match.group(1))
            block = page_match.group(2).strip()
            if not block:
                continue

        for part in _split_long_block(block):
            word_count = _word_count(part)
            blocks.append(
                {
                    "text": part,
                    "page": page,
                    "heading": _detect_heading(part),
                    "start_word": word_offset,
                    "end_word": word_offset + word_count,
                }
            )
            word_offset += word_count

    return blocks


def _split_long_block(block: str) -> list[str]:
    if _word_count(block) <= settings.KNOWLEDGE_CHUNK_SIZE:
        return [block]

    sentences = re.split(r"(?<=[.;:?!])\s+(?=[A-Z0-9])", block)
    parts = []
    current = []
    current_words = 0
    for sentence in sentences:
        sentence_words = _word_count(sentence)
        if current and current_words + sentence_words > settings.KNOWLEDGE_CHUNK_SIZE:
            parts.append(" ".join(current).strip())
            current = []
            current_words = 0
        current.append(sentence)
        current_words += sentence_words
    if current:
        parts.append(" ".join(current).strip())
    return parts or [block]


def _overlap_blocks(blocks: list[dict]) -> list[dict]:
    overlap = []
    total_words = 0
    for block in reversed(blocks):
        overlap.insert(0, block)
        total_words += _word_count(block["text"])
        if total_words >= settings.KNOWLEDGE_CHUNK_OVERLAP:
            break
    return overlap


def _detect_heading(text: str) -> str | None:
    first_line = text.splitlines()[0].strip()
    if len(first_line) > 120:
        return None
    if re.match(r"^(\d+(\.\d+)*\.?\s+|[A-Z][A-Z\s/&-]{5,}$)", first_line):
        return first_line
    return None


def _should_keep_together(text: str) -> bool:
    lowered = text.lower()
    return (
        "exclusion" in lowered
        or bool(re.match(r"^\s*(\d+(\.\d+)*|[a-z]\))\s+", lowered))
        or "|" in text
    )


def _word_count(text: str) -> int:
    return len(text.split())
