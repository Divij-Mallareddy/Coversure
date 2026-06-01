from config.settings import settings
import hashlib
import re

def chunk_text(text: str, document_name: str) -> list[dict]:
    blocks = _split_into_blocks(text)
    chunks = []
    current_blocks = []
    current_words = 0
    chunk_index = 0

    for block in blocks:
        block_words = _word_count(block["text"])
        should_flush = (
            current_blocks
            and current_words + block_words > settings.CHUNK_SIZE
            and not _should_keep_together(block["text"])
        )
        if should_flush:
            chunks.append(_build_chunk(current_blocks, document_name, chunk_index))
            current_blocks = _overlap_blocks(current_blocks)
            current_words = sum(_word_count(item["text"]) for item in current_blocks)
            chunk_index += 1

        current_blocks.append(block)
        current_words += block_words

    if current_blocks:
        chunks.append(_build_chunk(current_blocks, document_name, chunk_index))

    return chunks


def _split_into_blocks(text: str) -> list[dict]:
    normalized = re.sub(r"\r\n?", "\n", text)
    raw_blocks = re.split(r"\n\s*\n|(?=\[Page \d+\])", normalized)
    blocks = []
    page = None

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
            heading = _detect_heading(part)
            blocks.append({"text": part, "page": page, "heading": heading})

    return blocks


def _split_long_block(block: str) -> list[str]:
    words = block.split()
    if len(words) <= settings.CHUNK_SIZE:
        return [block]

    sentences = re.split(r"(?<=[.;:?!])\s+(?=[A-Z0-9])", block)
    parts = []
    current = []
    current_words = 0

    for sentence in sentences:
        sentence_words = _word_count(sentence)
        if current and current_words + sentence_words > settings.CHUNK_SIZE:
            parts.append(" ".join(current).strip())
            current = []
            current_words = 0
        current.append(sentence)
        current_words += sentence_words

    if current:
        parts.append(" ".join(current).strip())
    return parts or [block]


def _build_chunk(blocks: list[dict], document_name: str, chunk_index: int) -> dict:
    chunk_text_value = "\n".join(block["text"] for block in blocks).strip()
    pages = [block["page"] for block in blocks if block.get("page")]
    chunk_id = hashlib.sha256(f"{document_name}:{chunk_index}:{chunk_text_value[:120]}".encode("utf-8")).hexdigest()
    headings = [block["heading"] for block in blocks if block.get("heading")]
    heading = headings[-1] if headings else None
    return {
        "id": chunk_id,
        "text": chunk_text_value,
        "document": document_name,
        "source_document": document_name,
        "metadata": {
            "page": pages[0] if pages else None,
            "pages": sorted(set(pages)),
            "heading": heading,
            "section": heading,
            "source_document": document_name,
        },
        "page": pages[0] if pages else None,
        "pages": sorted(set(pages)),
        "heading": heading,
        "section": heading,
        "chunk_index": chunk_index,
    }


def _overlap_blocks(blocks: list[dict]) -> list[dict]:
    overlap = []
    total_words = 0
    for block in reversed(blocks):
        overlap.insert(0, block)
        total_words += _word_count(block["text"])
        if total_words >= settings.CHUNK_OVERLAP:
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
        or bool(re.match(r"^\s*(\d+(\.\d+)*|[a-z]\))\s+", text.lower()))
        or "|" in text
    )


def _word_count(text: str) -> int:
    return len(text.split())
