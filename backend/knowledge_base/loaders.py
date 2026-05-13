import hashlib
import json
import re
from pathlib import Path
from typing import Any

import pdfplumber

from .models import KnowledgeDocument, SUPPORTED_EXTENSIONS, category_from_path


def load_document(file_path: Path, content_root: Path) -> KnowledgeDocument | None:
    suffix = file_path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        return None

    if suffix == ".pdf":
        text = _load_pdf(file_path)
        metadata = {}
    elif suffix == ".json":
        text, metadata = _load_json(file_path)
    else:
        text = file_path.read_text(encoding="utf-8")
        metadata = _extract_markdown_metadata(text) if suffix in {".md", ".markdown"} else {}

    cleaned_text = _clean_text(text)
    if not cleaned_text:
        return None

    content_hash = hashlib.sha256(cleaned_text.encode("utf-8")).hexdigest()
    category = str(metadata.get("category") or category_from_path(content_root, file_path))
    tags = _normalize_tags(metadata.get("tags", []))
    relative_path = file_path.relative_to(content_root).as_posix()

    return KnowledgeDocument(
        title=str(metadata.get("title") or file_path.stem.replace("_", " ").replace("-", " ").title()),
        text=cleaned_text,
        source_path=relative_path,
        category=category,
        tags=tags,
        topic=metadata.get("topic"),
        content_type=str(metadata.get("content_type") or category),
        version=str(metadata.get("version") or content_hash[:12]),
        content_hash=content_hash,
        modified_at=file_path.stat().st_mtime,
    )


def file_fingerprint(file_path: Path, content_root: Path) -> dict:
    stat = file_path.stat()
    hasher = hashlib.sha256()
    with file_path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            hasher.update(block)

    return {
        "path": file_path.relative_to(content_root).as_posix(),
        "size": stat.st_size,
        "modified_at": stat.st_mtime,
        "file_hash": hasher.hexdigest(),
    }


def _load_pdf(file_path: Path) -> str:
    text_parts = []
    with pdfplumber.open(file_path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            page_text = page.extract_text()
            if page_text:
                text_parts.append(f"[Page {page_number}]\n{page_text}")
    return "\n\n".join(text_parts)


def _load_json(file_path: Path) -> tuple[str, dict]:
    data = json.loads(file_path.read_text(encoding="utf-8"))
    metadata = data.get("metadata", {}) if isinstance(data, dict) else {}

    if isinstance(data, dict):
        for key in ("title", "category", "tags", "topic", "content_type", "version"):
            if key in data and key not in metadata:
                metadata[key] = data[key]

    return _flatten_json(data), metadata


def _flatten_json(value: Any, prefix: str = "") -> str:
    lines = []

    if isinstance(value, dict):
        for key, item in value.items():
            if key == "metadata":
                continue
            next_prefix = f"{prefix} {key}".strip()
            lines.append(_flatten_json(item, next_prefix))
    elif isinstance(value, list):
        for index, item in enumerate(value, start=1):
            next_prefix = f"{prefix} item {index}".strip()
            lines.append(_flatten_json(item, next_prefix))
    elif value is not None:
        label = f"{prefix}: " if prefix else ""
        lines.append(f"{label}{value}")

    return "\n".join(line for line in lines if line)


def _extract_markdown_metadata(text: str) -> dict:
    match = re.match(r"^---\s*\n(.*?)\n---\s*", text, flags=re.DOTALL)
    if not match:
        return {}

    metadata = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if key == "tags":
            metadata[key] = _normalize_tags(value)
        else:
            metadata[key] = value
    return metadata


def _normalize_tags(tags: Any) -> list[str]:
    if isinstance(tags, str):
        return [tag.strip() for tag in tags.split(",") if tag.strip()]
    if isinstance(tags, list):
        return [str(tag).strip() for tag in tags if str(tag).strip()]
    return []


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()
