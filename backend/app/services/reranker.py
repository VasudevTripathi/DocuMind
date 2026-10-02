import re
import logging
from typing import List, Dict, Any, Set
from app.core.config import settings

logger = logging.getLogger("documind.reranker")

# Standard English stopwords for lexical token filtering
DEFAULT_STOPWORDS: Set[str] = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can", "can't", "cannot", "could",
    "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down",
    "during", "each", "few", "for", "from", "further", "had", "hadn't", "has",
    "hasn't", "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her",
    "here", "here's", "hers", "herself", "him", "himself", "his", "how", "how's",
    "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it",
    "it's", "its", "itself", "let's", "me", "more", "most", "mustn't", "my",
    "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other",
    "ought", "our", "ours", "ourselves", "out", "over", "own", "same", "shan't",
    "she", "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such",
    "than", "that", "that's", "the", "their", "theirs", "them", "themselves", "then",
    "there", "there's", "these", "they", "they'd", "they'll", "they're", "they've",
    "this", "those", "through", "to", "too", "under", "until", "up", "very", "was",
    "wasn't", "we", "we'd", "we'll", "we're", "we've", "were", "weren't", "what",
    "what's", "when", "when's", "where", "where's", "which", "while", "who", "who's",
    "whom", "why", "why's", "with", "won't", "would", "wouldn't", "you", "you'd",
    "you'll", "you're", "you've", "your", "yours", "yourself", "yourselves"
}

class RetrievalReranker:
    """
    Deterministic lightweight lexical + semantic reranker.
    Calculates combined evidence score:
        rerank_score = (semantic_weight * semantic_score) + (lexical_weight * lexical_score)

    Tie-breaking:
    1. final score (rerank_score) descending
    2. semantic_score descending
    3. chunk_index ascending
    """

    def __init__(
        self,
        semantic_weight: float = settings.RAG_SEMANTIC_WEIGHT,
        lexical_weight: float = settings.RAG_LEXICAL_WEIGHT,
        stopwords: Set[str] = DEFAULT_STOPWORDS
    ):
        self.semantic_weight = semantic_weight
        self.lexical_weight = lexical_weight
        self.stopwords = stopwords

    def tokenize(self, text: str) -> List[str]:
        """Extracts normalized alphanumeric tokens (min length 2, lowercased, stopwords excluded)."""
        if not text:
            return []
        tokens = re.findall(r"\b[a-zA-Z0-9_-]+\b", text.lower())
        return [t for t in tokens if len(t) >= 2 and t not in self.stopwords]

    def compute_lexical_score(self, query_tokens: List[str], chunk_text: str) -> float:
        """
        Calculates normalized lexical overlap ratio in [0.0, 1.0].
        If query contains no meaningful tokens, returns 0.0.
        """
        if not query_tokens or not chunk_text:
            return 0.0

        chunk_tokens = set(self.tokenize(chunk_text))
        if not chunk_tokens:
            return 0.0

        unique_query_tokens = set(query_tokens)
        matched_tokens = unique_query_tokens & chunk_tokens
        return len(matched_tokens) / len(unique_query_tokens)

    def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Reranks candidates deterministically using combined semantic and lexical scores.
        Preserves original semantic similarity scores while attaching lexical_score and rerank_score.
        Deduplicates by chunk_id keeping the highest scoring instance.
        """
        if not candidates:
            return []

        query_tokens = self.tokenize(query)

        # Deduplicate candidates by chunk_id while preserving highest score
        unique_map: Dict[str, Dict[str, Any]] = {}

        for c in candidates:
            chunk_id = c.get("chunk_id")
            if not chunk_id:
                continue

            item = dict(c)

            # Preserve semantic score
            semantic_score = float(
                item.get("semantic_score",
                item.get("similarity_score",
                item.get("score", 0.0)))
            )

            # Compute lexical overlap score
            lexical_score = self.compute_lexical_score(query_tokens, item.get("text", ""))

            # Calculate combined rerank score
            rerank_score = (self.semantic_weight * semantic_score) + (self.lexical_weight * lexical_score)

            item["semantic_score"] = round(semantic_score, 4)
            item["similarity_score"] = round(semantic_score, 4)
            item["lexical_score"] = round(lexical_score, 4)
            item["rerank_score"] = round(rerank_score, 4)
            item["score"] = round(rerank_score, 4)

            # Deduplication: keep the instance with higher rerank_score
            if chunk_id not in unique_map or item["rerank_score"] > unique_map[chunk_id]["rerank_score"]:
                unique_map[chunk_id] = item

        reranked_list = list(unique_map.values())

        # Deterministic tie-breaking sort:
        # 1. rerank_score descending
        # 2. semantic_score descending
        # 3. chunk_index ascending
        reranked_list.sort(
            key=lambda x: (
                -x["rerank_score"],
                -x["semantic_score"],
                x.get("chunk_index", 0)
            )
        )

        return reranked_list

reranker = RetrievalReranker()
