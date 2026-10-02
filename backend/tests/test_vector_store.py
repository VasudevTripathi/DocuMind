import numpy as np
import pytest
from app.services.vector_store import VectorStore

def test_vector_indexing_and_search(tmp_path):
    """
    Test 3: Vector indexing
    Add test vectors and verify search returns expected chunk.
    """
    store_dir = tmp_path / "vec_store"
    store = VectorStore(vector_store_dir=store_dir, dimension=4)

    # 3 distinct 4D unit vectors
    v1 = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)
    v2 = np.array([0.0, 1.0, 0.0, 0.0], dtype=np.float32)
    v3 = np.array([0.0, 0.0, 1.0, 0.0], dtype=np.float32)

    vectors = np.stack([v1, v2, v3])
    chunk_ids = ["chk-1", "chk-2", "chk-3"]

    added = store.add_document_chunks("doc-1", chunk_ids, vectors)
    assert added == 3
    assert store.count() == 3

    # Query matching v2
    query = np.array([0.0, 0.99, 0.0, 0.0], dtype=np.float32)
    results = store.search(query, top_k=2)

    assert len(results) == 2
    top_chunk_id, score = results[0]
    assert top_chunk_id == "chk-2"
    assert np.isclose(score, 1.0, atol=1e-2)

def test_vector_store_persistence_and_reload(tmp_path):
    """Verify that vector store index and mapping are persisted to disk and survive reload."""
    store_dir = tmp_path / "persist_store"
    store = VectorStore(vector_store_dir=store_dir, dimension=4)

    v1 = np.array([0.707, 0.707, 0.0, 0.0], dtype=np.float32)
    store.add_document_chunks("doc-persist", ["chk-p1"], np.array([v1]))
    assert store.count() == 1

    # Reload store from same directory
    reloaded_store = VectorStore(vector_store_dir=store_dir, dimension=4)
    assert reloaded_store.count() == 1
    assert reloaded_store.records[0]["chunk_id"] == "chk-p1"
    assert reloaded_store.records[0]["document_id"] == "doc-persist"

    results = reloaded_store.search(v1, top_k=1)
    assert len(results) == 1
    assert results[0][0] == "chk-p1"

def test_vector_store_document_removal(tmp_path):
    """Verify removing document vectors updates index and mapping cleanly."""
    store_dir = tmp_path / "removal_store"
    store = VectorStore(vector_store_dir=store_dir, dimension=4)

    vA = np.array([[1.0, 0.0, 0.0, 0.0]], dtype=np.float32)
    vB = np.array([[0.0, 1.0, 0.0, 0.0]], dtype=np.float32)

    store.add_document_chunks("doc-A", ["chk-A1"], vA)
    store.add_document_chunks("doc-B", ["chk-B1"], vB)
    assert store.count() == 2

    # Remove doc-A
    removed = store.remove_document("doc-A")
    assert removed == 1
    assert store.count() == 1
    assert store.records[0]["document_id"] == "doc-B"
    assert store.records[0]["chunk_id"] == "chk-B1"

    # Search for vA should not return chk-A1
    res = store.search(vA[0], top_k=1)
    assert res[0][0] == "chk-B1"
