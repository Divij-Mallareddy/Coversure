import hashlib
import logging
from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer

from config.settings import settings

logger = logging.getLogger("services.embeddings")

_model: SentenceTransformer | None = None
_embedding_dimension = 384


def _load_model() -> SentenceTransformer | None:
    global _model, _embedding_dimension
    if settings.EMBEDDING_MODEL == "dummy_embedding":
        return None
    if _model is None:
        logger.info("Loading embedding model: %s", settings.EMBEDDING_MODEL)
        _model = SentenceTransformer(settings.EMBEDDING_MODEL)
        _embedding_dimension = int(_model.get_sentence_embedding_dimension() or _embedding_dimension)
    return _model


def get_embedding_dimension() -> int:
    _load_model()
    return _embedding_dimension


def get_embeddings(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []

    if settings.ENABLE_CACHE:
        return [_get_embedding_cached(text) for text in texts]

    return _encode_batch(texts)


@lru_cache(maxsize=2048)
def _get_embedding_cached(text: str) -> list[float]:
    return _encode_batch([text])[0]


def _encode_batch(texts: list[str]) -> list[list[float]]:
    model = _load_model()
    if model is None:
        return [_dummy_embedding(text) for text in texts]

    embeddings = model.encode(
        texts,
        batch_size=32,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return embeddings.tolist()


def _dummy_embedding(text: str) -> list[float]:
    """Deterministic local placeholder so V2 runs before real models are configured."""
    vector = np.zeros(_embedding_dimension, dtype=np.float32)
    words = text.lower().split()
    for word in words:
        digest = hashlib.sha256(word.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % _embedding_dimension
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign

    norm = np.linalg.norm(vector)
    if norm > 0:
        vector = vector / norm
    return vector.tolist()
