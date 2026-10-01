from typing import Dict, List, Any, Optional

def chunk_document(
    document_id: str,
    parsed_data: Dict[str, Any],
    chunk_size_words: int = 1000,
    overlap_words: int = 150
) -> List[Dict[str, Any]]:
    """
    Deterministic document chunking.
    Splits document into semantic chunks of approximately 800–1200 words (default 1000)
    with a configurable sliding window overlap (default 150 words).

    Preserves:
    - document_id
    - chunk_index
    - text
    - page_number (inferred from page data when available)
    - word_count
    """
    pages = parsed_data.get("pages", [])
    chunks: List[Dict[str, Any]] = []

    # If document has distinct page structure, build word-to-page mappings
    word_page_tuples: List[tuple[str, Optional[int]]] = []

    if pages:
        for page_info in pages:
            p_num = page_info.get("page")
            p_text = page_info.get("text", "")
            for word in p_text.split():
                if word:
                    word_page_tuples.append((word, p_num))
    else:
        full_text = parsed_data.get("text", "")
        for word in full_text.split():
            if word:
                word_page_tuples.append((word, 1))

    total_words = len(word_page_tuples)
    if total_words == 0:
        return []

    # If document is smaller than target chunk size, return single chunk
    if total_words <= chunk_size_words:
        chunk_text = " ".join(w for w, _ in word_page_tuples)
        page_num = word_page_tuples[0][1] if word_page_tuples else 1
        return [{
            "document_id": document_id,
            "chunk_index": 0,
            "text": chunk_text,
            "page_number": page_num,
            "word_count": total_words
        }]

    step_size = max(1, chunk_size_words - overlap_words)
    chunk_idx = 0

    for start_idx in range(0, total_words, step_size):
        end_idx = min(start_idx + chunk_size_words, total_words)
        chunk_slice = word_page_tuples[start_idx:end_idx]

        if not chunk_slice:
            break

        chunk_text = " ".join(w for w, _ in chunk_slice)
        # Determine dominant or starting page number for this chunk
        primary_page = chunk_slice[0][1]

        chunks.append({
            "document_id": document_id,
            "chunk_index": chunk_idx,
            "text": chunk_text,
            "page_number": primary_page,
            "word_count": len(chunk_slice)
        })
        chunk_idx += 1

        # If we reached the end of the text, stop
        if end_idx >= total_words:
            break

    return chunks
