from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class KnowledgeDocument:
    title: str
    text: str
    source_path: str
    category: str
    tags: list[str] = field(default_factory=list)
    topic: str | None = None
    content_type: str = "document"
    version: str | None = None
    content_hash: str | None = None
    modified_at: float | None = None


@dataclass
class KnowledgeChunk:
    id: str
    text: str
    document: str
    title: str
    source_path: str
    category: str
    tags: list[str]
    topic: str | None
    content_type: str
    version: str
    content_hash: str
    chunk_index: int
    start_word: int
    end_word: int
    page: int | None = None
    heading: str | None = None
    section: str | None = None
    source_type: str = "knowledge_base"


SUPPORTED_EXTENSIONS = {".txt", ".md", ".markdown", ".json", ".pdf"}


def category_from_path(content_root: Path, file_path: Path) -> str:
    relative = file_path.relative_to(content_root)
    return relative.parts[0] if len(relative.parts) > 1 else "uncategorized"
