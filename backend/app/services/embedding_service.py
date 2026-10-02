import logging
from functools import lru_cache
from typing import List

logger = logging.getLogger("documind.embeddings")

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def get_embedding_model():
    """Load the local sentence-transformer model lazily and cache it in-process."""
    from sentence_transformers import SentenceTransformer

    logger.info("Loading local embedding model: %s", MODEL_NAME)
    return SentenceTransformer(MODEL_NAME)


def embed_texts(texts: List[str]) -> List[List[float]]:
    if not texts:
        return []

    model = get_embedding_model()
    vectors = model.encode(
        texts,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    return vectors.tolist()


def embed_query(query: str) -> List[float]:
    if not query or not query.strip():
        return []

    vectors = embed_texts([query.strip()])
    return vectors[0] if vectors else []
