import numpy as np
import pytest
from app.services.embedding_service import embedding_service

def test_embedding_generation_single_text():
    """Verify that a single text produces an embedding with consistent dimensions and unit normalization."""
    text = "Antigravity AI document retrieval intelligence."
    vec = embedding_service.embed_text(text)

    # 1. Produced
    assert vec is not None
    assert isinstance(vec, np.ndarray)
    assert vec.dtype == np.float32

    # 2. Consistent dimensions
    expected_dim = embedding_service.get_embedding_dimension()
    assert vec.shape == (expected_dim,)
    assert expected_dim == 384

    # 3. Normalized to unit length (L2 norm ≈ 1.0)
    norm = np.linalg.norm(vec)
    assert np.isclose(norm, 1.0, atol=1e-4)

def test_embedding_generation_batch_chunks():
    """Verify batch embedding generation produces 2D normalized array with consistent dimensions."""
    texts = [
        "The transformer architecture uses self-attention.",
        "Quarterly revenue increased by 18 percent.",
        "Tenant agrees to arbitration."
    ]
    vectors = embedding_service.embed_chunks(texts, batch_size=2)

    assert vectors.shape == (3, 384)
    assert vectors.dtype == np.float32

    # Check each vector is normalized
    norms = np.linalg.norm(vectors, axis=1)
    for norm in norms:
        assert np.isclose(norm, 1.0, atol=1e-4)

def test_embedding_empty_input():
    """Verify handling of empty or blank text gracefully."""
    empty_vec = embedding_service.embed_text("")
    assert empty_vec.shape == (384,)

    empty_batch = embedding_service.embed_chunks([])
    assert empty_batch.shape == (0, 384)

    empty_texts = embedding_service.embed_texts([])
    assert empty_texts.shape == (0, 384)

def test_embed_texts_interface():
    """Verify embed_texts interface behaves identically to embed_chunks."""
    samples = ["First test text.", "Second test text."]
    vecs = embedding_service.embed_texts(samples)
    assert vecs.shape == (2, 384)
    assert vecs.dtype == np.float32
