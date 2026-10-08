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

        self._fallback_provider = fallback_provider or HeuristicFallbackProvider()
        self._primary_provider = primary_provider
        self._secondary_provider = None

        # Resolve available keys
        if api_key is not None:
            self.api_key = api_key
            groq_key = api_key if configured_provider == "groq" or "groq" in api_key.lower() else None
            gemini_key = api_key if configured_provider == "gemini" or "gemini" in api_key.lower() else None
            if self._is_placeholder(api_key):
                groq_key = None
                gemini_key = None
        else:
            groq_key = settings.GROQ_API_KEY or os.environ.get("GROQ_API_KEY")
            if self._is_placeholder(groq_key):
                groq_key = None

            gemini_key = settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY")
            if self._is_placeholder(gemini_key):
                gemini_key = None
            self.api_key = groq_key or gemini_key

        if self._primary_provider is not None:
            self.provider_type = configured_provider
            if api_key is not None:
                self.api_key = api_key
            else:
                self.api_key = groq_key or gemini_key
            self.model = model or getattr(settings, "GROQ_MODEL", None) or "llama-3.3-70b-versatile"
        elif configured_provider == "groq":
            if groq_key:
                self.provider_type = "groq"
                self.api_key = groq_key
                self.model = (
                    model
                    or getattr(settings, "GROQ_MODEL", None)
                    or os.environ.get("GROQ_MODEL")
                    or "llama-3.3-70b-versatile"
                )
                self._primary_provider = GroqProvider(
                    api_key=self.api_key,
                    model=self.model,
                    timeout=30.0,
                    max_retries=getattr(settings, "GROQ_MAX_RETRIES", 2),
                    initial_backoff=getattr(settings, "GROQ_INITIAL_BACKOFF", 1.0)
                )
                if gemini_key:
                    self._secondary_provider = GeminiProvider(
                        api_key=gemini_key,
                        model=getattr(settings, "GEMINI_MODEL", None) or "gemini-2.5-flash"
                    )
            elif gemini_key:
                # Groq key not configured, but Gemini key is available: auto-failover
                logger.info("[LLMService] Groq API key is not configured; auto-failing over to active Gemini API key.")
                self.provider_type = "gemini"
                self.api_key = gemini_key
                self.model = getattr(settings, "GEMINI_MODEL", None) or "gemini-2.5-flash"
                self._primary_provider = GeminiProvider(
                    api_key=self.api_key,
                    model=self.model,
                    timeout=30.0,
                    max_retries=getattr(settings, "GEMINI_MAX_RETRIES", 2),
                    initial_backoff=getattr(settings, "GEMINI_INITIAL_BACKOFF", 1.0)
                )
            else:
                self.provider_type = "groq"
                self.api_key = None
                self.model = model or getattr(settings, "GROQ_MODEL", None) or "llama-3.3-70b-versatile"
                self._primary_provider = None
        else:
            if gemini_key:
                self.provider_type = "gemini"
                self.api_key = gemini_key
                self.model = model or getattr(settings, "GEMINI_MODEL", None) or "gemini-2.5-flash"
                self._primary_provider = GeminiProvider(
                    api_key=self.api_key,
                    model=self.model,
                    timeout=30.0,
                    max_retries=getattr(settings, "GEMINI_MAX_RETRIES", 2),
                    initial_backoff=getattr(settings, "GEMINI_INITIAL_BACKOFF", 1.0)
                )
                if groq_key:
                    self._secondary_provider = GroqProvider(
                        api_key=groq_key,
                        model=getattr(settings, "GROQ_MODEL", None) or "llama-3.3-70b-versatile"
                    )
            elif groq_key:
                logger.info("[LLMService] Gemini API key is not configured; auto-failing over to active Groq API key.")
                self.provider_type = "groq"
                self.api_key = groq_key
                self.model = getattr(settings, "GROQ_MODEL", None) or "llama-3.3-70b-versatile"
                self._primary_provider = GroqProvider(
                    api_key=self.api_key,
                    model=self.model,
                    timeout=30.0,
                    max_retries=getattr(settings, "GROQ_MAX_RETRIES", 2),
                    initial_backoff=getattr(settings, "GROQ_INITIAL_BACKOFF", 1.0)
                )
            else:
                self.provider_type = "gemini"
                self.api_key = None
                self.model = model or getattr(settings, "GEMINI_MODEL", None) or "gemini-2.5-flash"
                self._primary_provider = None

    @staticmethod
    def _is_placeholder(k: Optional[str]) -> bool:
        if not k or not k.strip():
            return True
        val = k.strip().lower()
        return (
            "your_groq_api_key" in val
            or "your_gemini_api_key" in val
            or "your_api_key" in val
            or "placeholder" in val
            or val.startswith("your_")
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
        return not self._is_placeholder(self.api_key)

    @property
    def active_provider_name(self) -> str:
        if self.has_active_api_key and self._primary_provider:
            return getattr(self._primary_provider, "provider_name", self.provider_type)
        return "heuristic_fallback"

    def answer_question(self, question: str, context: str) -> GenerationResult:
        """
        Generates a factual, grounded answer to the question using ONLY the retrieved context.
        Attempts primary generation; fails over to secondary if available; falls back to heuristic provider.
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
                    f"[LLMService] {self.active_provider_name} generation failed ({e}).",
                    exc_info=False
                )
                if self._secondary_provider:
                    try:
                        sec_name = getattr(self._secondary_provider, "provider_name", "secondary")
                        logger.info(f"[LLMService] Attempting failover to secondary provider ({sec_name})...")
                        return self._secondary_provider.generate_answer(question, context)
                    except Exception as e2:
                        logger.warning(f"[LLMService] Secondary provider ({sec_name}) generation also failed: {e2}")

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

        last_error = None
        if self.has_active_api_key and self._primary_provider:
            try:
                logger.info(f"[LLMService] Generating conversational answer via {self.active_provider_name} ({self.model})...")
                return self._primary_provider.generate_conversational_answer(question, context, history)
            except Exception as e:
                last_error = str(e)
                logger.warning(
                    f"[LLMService] {self.active_provider_name} conversational generation failed ({e}).",
                    exc_info=False
                )
                if self._secondary_provider:
                    try:
                        sec_name = getattr(self._secondary_provider, "provider_name", "secondary")
                        logger.info(f"[LLMService] Attempting conversational failover to secondary provider ({sec_name})...")
                        return self._secondary_provider.generate_conversational_answer(question, context, history)
                    except Exception as e2:
                        last_error = f"{last_error}; secondary failed: {e2}"

        # In case of failure, DO NOT dump raw document text! Return the failure reason clearly.
        if last_error:
            if "RESOURCE_EXHAUSTED" in last_error or "429" in last_error:
                failure_text = (
                    f"⚠️ AI Generation Error ({self.active_provider_name}): Quota or rate limit exceeded (429 RESOURCE_EXHAUSTED).\n\n"
                    "The model provider has exceeded its current API quota. "
                    "To fix this, please set a valid GROQ_API_KEY in `backend/.env` (free tier at console.groq.com) or check your billing plan."
                )
            elif "401" in last_error or "API_KEY_INVALID" in last_error or "invalid api key" in last_error.lower():
                failure_text = (
                    f"⚠️ AI Generation Error ({self.active_provider_name}): Authentication failed (401 Invalid API Key).\n\n"
                    "Please check your API key in `backend/.env`."
                )
            elif "503" in last_error or "high demand" in last_error.lower():
                failure_text = (
                    f"⚠️ AI Generation Error ({self.active_provider_name}): Service temporarily unavailable (503 High Demand).\n\n"
                    "The upstream model is currently experiencing high demand. Please try again shortly or configure a GROQ_API_KEY in `backend/.env`."
                )
            else:
                failure_text = f"⚠️ AI Generation Error ({self.active_provider_name}): {last_error[:250]}"
        elif not self.has_active_api_key:
            failure_text = (
                f"⚠️ AI Generation Unavailable: No valid API key configured for provider '{self.provider_type}'.\n\n"
                "Please configure a valid GROQ_API_KEY (or GEMINI_API_KEY) in `backend/.env` to enable conversational AI answers."
            )
        else:
            failure_text = "⚠️ AI Generation Failed: The language model was unable to generate an answer."

        return GenerationResult(
            text=failure_text,
            provider="failure_notice",
            model="failure-handler",
            tokens_used=0,
            latency_ms=0.0
        )

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
