import logging
import os
from typing import Dict, List, Any, Optional

from app.core.config import settings
from app.services.llm_provider import (
    BaseLLMProvider,
    GeminiProvider,
    OpenAIProvider,
    HeuristicFallbackProvider,
    GenerationResult
)

logger = logging.getLogger("documind.llm")

MAX_LLM_INPUT_WORDS = 2500

class LLMServiceError(Exception):
    """Raised when LLM analysis fails."""
    pass

class LLMService:
    """
    Coordinates LLM answer generation and document analysis:
    - Resolves active provider (GeminiProvider if API key is present and functional)
    - Automatically falls back to HeuristicFallbackProvider on any error, timeout, or missing key
    - Produces GenerationResult containing provider telemetry without breaking string contracts
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        primary_provider: Optional[BaseLLMProvider] = None,
        fallback_provider: Optional[BaseLLMProvider] = None
    ):
        if api_key is not None:
            self.api_key = api_key
        else:
            self.api_key = (
                settings.GEMINI_API_KEY
                or os.environ.get("GEMINI_API_KEY")
                or settings.OPENAI_API_KEY
                or os.environ.get("OPENAI_API_KEY")
            )
        self.model = model or settings.LLM_MODEL or "gemini-2.5-flash"
        self._fallback_provider = fallback_provider or HeuristicFallbackProvider()
        self._primary_provider = primary_provider
        if self._primary_provider is None and self.api_key:
            self._primary_provider = GeminiProvider(
                api_key=self.api_key,
                model=self.model,
                timeout=15.0,
                max_retries=2
            )

    @property
    def client(self):
        if self._primary_provider and hasattr(self._primary_provider, "client"):
            return self._primary_provider.client
        return getattr(self, "_client", None)

    @client.setter
    def client(self, val):
        self._client = val
        if hasattr(self, "_primary_provider") and self._primary_provider:
            self._primary_provider._client = val

    def __setattr__(self, name, value):
        super().__setattr__(name, value)
        if name in ("_client", "client") and hasattr(self, "_primary_provider") and self._primary_provider:
            self._primary_provider._client = value

    @property
    def has_active_api_key(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    @property
    def active_provider_name(self) -> str:
        if self.has_active_api_key and self._primary_provider:
            return getattr(self._primary_provider, "provider_name", "gemini")
        return "heuristic_fallback"

    def answer_question(self, question: str, context: str) -> GenerationResult:
        """
        Generates a factual, grounded answer to the question using ONLY the retrieved context.
        Attempts Gemini generation if configured; falls back to deterministic extraction on failure.
        """
        if not context or not context.strip():
            return GenerationResult(
                text="The answer could not be found in the provided documents.",
                provider=self.active_provider_name,
                model=self.model if self.has_active_api_key else "extractive-rules"
            )

        if self.has_active_api_key and self._primary_provider:
            try:
                logger.info(f"[LLMService] Generating answer via Gemini ({self.model})...")
                return self._primary_provider.generate_answer(question, context)
            except Exception as e:
                logger.warning(
                    f"[LLMService] Gemini generation encountered an error ({e}). "
                    f"Seamlessly degrading to deterministic heuristic fallback.",
                    exc_info=False
                )

        logger.info("[LLMService] Utilizing deterministic heuristic fallback answering.")
        return self._fallback_provider.generate_answer(question, context)

    def answer_conversational_question(
        self,
        question: str,
        context: str,
        history: Optional[List[Dict[str, str]]] = None
    ) -> GenerationResult:
        """
        Generates a conversational answer incorporating bounded dialogue turns.
        Preserves the strict boundary where document context is authoritative evidence.
        """
        if not context or not context.strip():
            return GenerationResult(
                text="The answer could not be found in the provided documents.",
                provider=self.active_provider_name,
                model=self.model if self.has_active_api_key else "extractive-rules"
            )

        if self.has_active_api_key and self._primary_provider:
            try:
                logger.info(f"[LLMService] Generating conversational answer via Gemini ({self.model})...")
                return self._primary_provider.generate_conversational_answer(question, context, history)
            except Exception as e:
                logger.warning(
                    f"[LLMService] Gemini conversational generation failed ({e}). "
                    f"Degrading to heuristic fallback.",
                    exc_info=False
                )

        logger.info("[LLMService] Utilizing deterministic heuristic conversational answering.")
        return self._fallback_provider.generate_conversational_answer(question, context, history)

    def analyze_document(self, text: str) -> Dict[str, Any]:
        """
        Extracts summary, key findings, and named entities.
        Falls back to rule-based heuristic extraction if Gemini call fails.
        """
        if self.has_active_api_key and self._primary_provider:
            try:
                return self._primary_provider.analyze_document(text)
            except Exception as e:
                logger.warning(f"[LLMService] Gemini document analysis failed ({e}). Employing fallback.")

        return self._fallback_provider.analyze_document(text)

    # Backward compatibility helper
    def prepare_representative_text(self, text: str, max_words: int = MAX_LLM_INPUT_WORDS) -> str:
        words = text.split()
        if len(words) <= max_words:
            return text
        head_count = int(max_words * 0.6)
        mid_count = int(max_words * 0.2)
        tail_count = int(max_words * 0.2)
        mid_start = (len(words) // 2) - (mid_count // 2)
        mid_end = mid_start + mid_count
        return (
            " ".join(words[:head_count]) + "\n\n[...]\n\n" +
            " ".join(words[mid_start:mid_end]) + "\n\n[...]\n\n" +
            " ".join(words[-tail_count:])
        )

llm_service = LLMService()
