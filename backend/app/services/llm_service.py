import logging
import os
from typing import Dict, List, Any, Optional

from app.core.config import settings
from app.services.llm_provider import (
    BaseLLMProvider,
    GroqProvider,
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
    - Resolves active provider (GroqProvider by default if API key is present and functional)
    - Automatically falls back to HeuristicFallbackProvider on any error, timeout, or missing key
    - Produces GenerationResult containing provider telemetry without breaking string contracts
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        primary_provider: Optional[BaseLLMProvider] = None,
        fallback_provider: Optional[BaseLLMProvider] = None,
        provider_type: Optional[str] = None
    ):
        configured_provider = (
            provider_type
            or ("gemini" if api_key and "gemini" in api_key.lower() else None)
            or getattr(settings, "LLM_PROVIDER", None)
            or os.environ.get("LLM_PROVIDER")
            or "groq"
        ).strip().lower()

        self.provider_type = configured_provider
        self._fallback_provider = fallback_provider or HeuristicFallbackProvider()
        self._primary_provider = primary_provider

        if self.provider_type == "gemini":
            self.api_key = (
                api_key
                or settings.GEMINI_API_KEY
                or os.environ.get("GEMINI_API_KEY")
            )
            raw_model = (
                model
                or getattr(settings, "GEMINI_MODEL", None)
                or os.environ.get("GEMINI_MODEL")
                or "gemini-2.5-flash"
            )
            self.model = "gemini-2.5-flash" if raw_model in ("gemini-flash-latest", "gemini-flash", "gemini-1.5-flash") else raw_model
            if self._primary_provider is None and self.has_active_api_key:
                self._primary_provider = GeminiProvider(
                    api_key=self.api_key,
                    model=self.model,
                    timeout=30.0,
                    max_retries=getattr(settings, "GEMINI_MAX_RETRIES", 2),
                    initial_backoff=getattr(settings, "GEMINI_INITIAL_BACKOFF", 1.0)
                )
        else:
            # Default: Groq
            self.api_key = (
                api_key
                or settings.GROQ_API_KEY
                or os.environ.get("GROQ_API_KEY")
                or settings.OPENAI_API_KEY
                or os.environ.get("OPENAI_API_KEY")
            )
            self.model = (
                model
                or getattr(settings, "GROQ_MODEL", None)
                or os.environ.get("GROQ_MODEL")
                or getattr(settings, "LLM_MODEL", None)
                or os.environ.get("LLM_MODEL")
                or "llama-3.3-70b-versatile"
            )
            if self._primary_provider is None and self.has_active_api_key:
                self._primary_provider = GroqProvider(
                    api_key=self.api_key,
                    model=self.model,
                    timeout=30.0,
                    max_retries=getattr(settings, "GROQ_MAX_RETRIES", 2),
                    initial_backoff=getattr(settings, "GROQ_INITIAL_BACKOFF", 1.0)
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
        if not self.api_key or not self.api_key.strip():
            return False
        k = self.api_key.strip().lower()
        if (
            "your_groq_api_key" in k
            or "your_gemini_api_key" in k
            or "your_api_key" in k
            or "placeholder" in k
            or k.startswith("your_")
        ):
            return False
        return True

    @property
    def active_provider_name(self) -> str:
        if self.has_active_api_key and self._primary_provider:
            return getattr(self._primary_provider, "provider_name", self.provider_type)
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
                logger.info(f"[LLMService] Generating answer via {self.active_provider_name} ({self.model})...")
                return self._primary_provider.generate_answer(question, context)
            except Exception as e:
                logger.warning(
                    f"[LLMService] {self.active_provider_name} generation encountered an error ({e}). "
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
                logger.info(f"[LLMService] Generating conversational answer via {self.active_provider_name} ({self.model})...")
                return self._primary_provider.generate_conversational_answer(question, context, history)
            except Exception as e:
                logger.warning(
                    f"[LLMService] {self.active_provider_name} conversational generation failed ({e}). "
                    f"Degrading to heuristic fallback.",
                    exc_info=False
                )

        logger.info("[LLMService] Utilizing deterministic heuristic conversational answering.")
        return self._fallback_provider.generate_conversational_answer(question, context, history)

    def analyze_document(self, text: str) -> Dict[str, Any]:
        """
        Extracts summary, key findings, and named entities.
        Falls back to rule-based heuristic extraction if provider call fails.
        Explicitly tags quota_exceeded and provider status if 429 quota exhaustion occurs.
        """
        if self.has_active_api_key and self._primary_provider:
            try:
                res = self._primary_provider.analyze_document(text)
                res["provider"] = getattr(self._primary_provider, "provider_name", self.provider_type)
                res["quota_exceeded"] = False
                return res
            except Exception as e:
                err_str = str(e)
                is_quota = "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "ratelimit" in err_str.lower()
                logger.warning(f"[LLMService] {self.active_provider_name} document analysis failed ({e}). Employing fallback.")
                fallback = self._fallback_provider.analyze_document(text)
                fallback["provider"] = "quota_exhausted" if is_quota else "heuristic_fallback"
                fallback["quota_exceeded"] = is_quota
                if is_quota:
                    provider_label = self.active_provider_name.title()
                    notice = f"⚠️ [Notice: {provider_label} API quota/rate limit reached. The following summary was extracted using offline heuristics instead of LLM generation.]\n\n"
                    fallback["summary"] = notice + fallback.get("summary", "")
                    fallback["warning"] = f"{provider_label} API rate limit / quota reached. Showing offline extractive analysis until quota resets."
                return fallback

        fallback = self._fallback_provider.analyze_document(text)
        fallback["provider"] = "heuristic_fallback"
        fallback["quota_exceeded"] = False
        return fallback

    def explain_comparison(
        self,
        doc_a_name: str,
        doc_b_name: str,
        differences_data: Dict[str, Any]
    ) -> GenerationResult:
        """
        Synthesizes an executive summary of detected differences between Document A and Document B.
        Attempts LLM synthesis if available; seamlessly falls back to heuristic summary on error or offline mode.
        """
        if self.has_active_api_key and self._primary_provider:
            try:
                logger.info(f"[LLMService] Synthesizing comparison explanation via {self.active_provider_name} ({self.model})...")
                return self._primary_provider.explain_comparison(doc_a_name, doc_b_name, differences_data)
            except Exception as e:
                logger.warning(
                    f"[LLMService] {self.active_provider_name} comparison explanation failed ({e}). "
                    f"Employing deterministic heuristic fallback.",
                    exc_info=False
                )

        logger.info("[LLMService] Utilizing deterministic heuristic comparison explanation.")
        return self._fallback_provider.explain_comparison(doc_a_name, doc_b_name, differences_data)


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
