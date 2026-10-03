import re
import logging
from typing import List, Dict, Any, Set, Optional, Tuple
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
    Deterministic lightweight multi-signal reranker (Phase 8.3).
    Combines:
      1. Semantic similarity (from FAISS cosine similarity)
      2. Lexical overlap (unigram token overlap ratio)
      3. Exact phrase / n-gram overlap (exact string match and bigram/trigram overlap)
      4. Query term coverage (ratio of unique query terms present)
      5. Context signal (source indicator: direct FAISS match vs context expansion neighbor)

    Score formula:
        rerank_score = (
            semantic_weight * semantic_score +
            lexical_weight * lexical_score +
            phrase_weight * phrase_score +
            coverage_weight * coverage_score +
            context_weight * context_score
        )

    Tie-breaking:
    1. final score (rerank_score) descending
    2. semantic_score descending
    3. chunk_index ascending
    """

    def __init__(
        self,
        semantic_weight: Optional[float] = None,
        lexical_weight: Optional[float] = None,
        phrase_weight: Optional[float] = None,
        coverage_weight: Optional[float] = None,
        context_weight: Optional[float] = None,
        context_discount: Optional[float] = None,
        stopwords: Set[str] = DEFAULT_STOPWORDS
    ):
        # Backward compatibility: if caller explicitly supplied 2 weights without Phase 8.3 weights
        if (
            phrase_weight is None
            and coverage_weight is None
            and context_weight is None
            and (semantic_weight is not None or lexical_weight is not None)
        ):
            self.semantic_weight = semantic_weight if semantic_weight is not None else 0.75
            self.lexical_weight = lexical_weight if lexical_weight is not None else 0.25
            self.phrase_weight = 0.0
            self.coverage_weight = 0.0
            self.context_weight = 0.0
        else:
            self.semantic_weight = (
                semantic_weight if semantic_weight is not None else settings.RAG_SEMANTIC_WEIGHT
            )
            self.lexical_weight = (
                lexical_weight if lexical_weight is not None else settings.RAG_LEXICAL_WEIGHT
            )
            self.phrase_weight = (
                phrase_weight if phrase_weight is not None else settings.RAG_PHRASE_WEIGHT
            )
            self.coverage_weight = (
                coverage_weight if coverage_weight is not None else settings.RAG_COVERAGE_WEIGHT
            )
            self.context_weight = (
                context_weight if context_weight is not None else settings.RAG_CONTEXT_WEIGHT
            )

        self.context_discount = (
            context_discount if context_discount is not None else settings.RAG_CONTEXT_DISCOUNT
        )
        self.stopwords = stopwords

    def tokenize(self, text: str) -> List[str]:
        """Extracts normalized alphanumeric tokens (min length 2, lowercased, stopwords excluded)."""
        if not text:
            return []
        tokens = re.findall(r"\b[a-zA-Z0-9_-]+\b", text.lower())
        return [t for t in tokens if len(t) >= 2 and t not in self.stopwords]

    def _normalize_clean_text(self, text: str) -> str:
        """Lowercases and collapses non-alphanumeric punctuation to single spaces."""
        if not text:
            return ""
        cleaned = re.sub(r"[^\w\s]", " ", text.lower())
        return " ".join(cleaned.split())

    def compute_lexical_score(self, query_tokens: List[str], chunk_text: str) -> float:
        """
        Calculates normalized lexical unigram overlap ratio in [0.0, 1.0].
        If query contains no meaningful tokens, returns 0.0.
        """
        if not query_tokens or not chunk_text:
            return 0.0

        chunk_tokens = set(self.tokenize(chunk_text))
        if not chunk_tokens:
            return 0.0

        unique_query_tokens = set(query_tokens)
        matched_tokens = unique_query_tokens & chunk_tokens
        return min(1.0, max(0.0, len(matched_tokens) / len(unique_query_tokens)))

    def compute_phrase_score(self, query: str, chunk_text: str) -> float:
        """
        Calculates exact phrase and n-gram overlap score in [0.0, 1.0].
        Supports:
          - Exact normalized multi-word phrase matching (score = 1.0)
          - Bigram overlap
          - Trigram overlap
        """
        if not query or not chunk_text:
            return 0.0

        clean_q = self._normalize_clean_text(query)
        clean_c = self._normalize_clean_text(chunk_text)

        if not clean_q or not clean_c:
            return 0.0

        # Exact multi-token substring match receives full score
        q_words = clean_q.split()
        if len(q_words) >= 2 and clean_q in clean_c:
            return 1.0

        # Token-based n-gram matching on non-stopword tokens
        tokens_q = self.tokenize(query)
        tokens_c = self.tokenize(chunk_text)

        if not tokens_q or not tokens_c:
            return 0.0

        if len(tokens_q) == 1:
            return 1.0 if tokens_q[0] in tokens_c else 0.0

        # Bigram overlap
        bigrams_q = set(zip(tokens_q, tokens_q[1:]))
        bigrams_c = set(zip(tokens_c, tokens_c[1:]))

        if not bigrams_q:
            return 0.0

        bigram_ratio = len(bigrams_q & bigrams_c) / len(bigrams_q)

        # Trigram overlap if query has >= 3 tokens
        if len(tokens_q) >= 3:
            trigrams_q = set(zip(tokens_q, tokens_q[1:], tokens_q[2:]))
            trigrams_c = set(zip(tokens_c, tokens_c[1:], tokens_c[2:]))
            trigram_ratio = len(trigrams_q & trigrams_c) / len(trigrams_q) if trigrams_q else 0.0
            phrase_score = (0.60 * bigram_ratio) + (0.40 * trigram_ratio)
        else:
            phrase_score = bigram_ratio

        return min(1.0, max(0.0, phrase_score))

    def compute_coverage_score(self, query_tokens: List[str], chunk_text: str) -> float:
        """
        Calculates query term coverage in [0.0, 1.0].
        Measures the fraction of unique non-stopword query terms present in chunk.
        """
        if not query_tokens or not chunk_text:
            return 0.0

        unique_q_terms = set(query_tokens)
        if not unique_q_terms:
            return 0.0

        chunk_tokens = set(self.tokenize(chunk_text))
        matched = unique_q_terms & chunk_tokens
        return min(1.0, max(0.0, len(matched) / len(unique_q_terms)))

    def compute_context_score(self, candidate: Dict[str, Any]) -> float:
        """
        Calculates context signal in [0.0, 1.0].
        Direct FAISS matches receive 1.0.
        Context expansion neighbors receive a discounted score (e.g. 0.80).
        """
        is_expanded = candidate.get("is_expanded", False)
        if not is_expanded:
            return 1.0

        distance = int(candidate.get("context_distance", 1))
        return min(1.0, max(0.0, self.context_discount ** max(1, distance)))

    def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Reranks candidates deterministically using enhanced multi-signal scoring.
        Preserves original semantic similarity scores while attaching lexical_score,
        phrase_score, coverage_score, context_score, and rerank_score.
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

            # 1. Semantic score
            raw_semantic = float(
                item.get("semantic_score",
                item.get("similarity_score",
                item.get("score", 0.0)))
            )
            semantic_score = min(1.0, max(0.0, raw_semantic))

            chunk_text = item.get("text", "")

            # 2. Lexical score (unigram)
            lexical_score = self.compute_lexical_score(query_tokens, chunk_text)

            # 3. Phrase score (exact phrase / n-grams)
            phrase_score = self.compute_phrase_score(query, chunk_text)

            # 4. Coverage score (query term coverage)
            coverage_score = self.compute_coverage_score(query_tokens, chunk_text)

            # 5. Context score (source indicator: direct vs expanded)
            context_score = self.compute_context_score(item)

            # Combined weighted score
            rerank_score = (
                (self.semantic_weight * semantic_score) +
                (self.lexical_weight * lexical_score) +
                (self.phrase_weight * phrase_score) +
                (self.coverage_weight * coverage_score) +
                (self.context_weight * context_score)
            )

            item["semantic_score"] = round(semantic_score, 4)
            item["similarity_score"] = round(semantic_score, 4)
            item["lexical_score"] = round(lexical_score, 4)
            item["phrase_score"] = round(phrase_score, 4)
            item["coverage_score"] = round(coverage_score, 4)
            item["context_score"] = round(context_score, 4)
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
