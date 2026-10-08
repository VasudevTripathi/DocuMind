import pytest
import json
from unittest.mock import MagicMock, patch
from app.services.llm_provider import GroqProvider, HeuristicFallbackProvider, GenerationResult
from app.services.llm_service import LLMService

def test_groq_provider_initialization():
    provider = GroqProvider(api_key="gsk_test_key_123", model="llama-3.3-70b-versatile")
    assert provider.api_key == "gsk_test_key_123"
    assert provider.model == "llama-3.3-70b-versatile"
    assert provider.provider_name == "groq"

def test_groq_provider_success_and_telemetry():
    fake_client = MagicMock()
    fake_choice = MagicMock()
    fake_choice.message.content = "The replication factor is set to 3 across 3 zones."
    fake_choice.finish_reason = "stop"
    fake_usage = MagicMock()
    fake_usage.total_tokens = 55

    fake_response = MagicMock()
    fake_response.choices = [fake_choice]
    fake_response.usage = fake_usage

    fake_client.chat.completions.create.return_value = fake_response

    provider = GroqProvider(api_key="gsk_valid_key", model="llama-3.3-70b-versatile")
    provider._client = fake_client

    context = "Database replication factor is 3 across 3 availability zones."
    result = provider.generate_answer("What is the replication factor?", context)

    assert isinstance(result, GenerationResult)
    assert result.provider == "groq"
    assert result.model == "llama-3.3-70b-versatile"
    assert result.tokens_used == 55
    assert result.finish_reason == "stop"
    assert "replication factor is set to 3" in result.text
    assert result.latency_ms >= 0.0

    # Verify anti-injection isolation
    call_args = fake_client.chat.completions.create.call_args[1]
    messages = call_args["messages"]
    system_msg = next(m["content"] for m in messages if m["role"] == "system")
    user_msg = next(m["content"] for m in messages if m["role"] == "user")

    assert "Anti-Injection" in system_msg
    assert "<untrusted_document_context>" in user_msg
    assert "</untrusted_document_context>" in user_msg
    assert context in user_msg

def test_groq_provider_empty_context_abstention():
    provider = GroqProvider(api_key="gsk_valid_key")
    result = provider.generate_answer("What is X?", "")
    assert result.text == "The answer could not be found in the provided documents."
    assert result.tokens_used == 0

def test_groq_temporary_failure_bounded_retry():
    fake_client = MagicMock()
    fake_choice = MagicMock()
    fake_choice.message.content = "Recovered after transient error."
    fake_choice.finish_reason = "stop"
    fake_usage = MagicMock()
    fake_usage.total_tokens = 25
    fake_response = MagicMock(choices=[fake_choice], usage=fake_usage)

    # First call: 503 transient error, second call: success
    transient_exc = Exception("503 Service Unavailable: server overloaded")
    fake_client.chat.completions.create.side_effect = [transient_exc, fake_response]

    provider = GroqProvider(
        api_key="gsk_valid_key",
        max_retries=2,
        initial_backoff=0.01
    )
    provider._client = fake_client

    result = provider.generate_answer("Test question", "Some context")
    assert result.text == "Recovered after transient error."
    assert fake_client.chat.completions.create.call_count == 2

def test_groq_invalid_api_key_no_pointless_retries():
    fake_client = MagicMock()
    auth_exc = Exception("401 Invalid API Key: authenticationerror")
    fake_client.chat.completions.create.side_effect = auth_exc

    provider = GroqProvider(
        api_key="invalid_key",
        max_retries=3,
        initial_backoff=0.01
    )
    provider._client = fake_client

    with pytest.raises(Exception) as exc_info:
        provider.generate_answer("Test", "Context")

    assert "401" in str(exc_info.value)
    # Must fail immediately on attempt 1 without retrying
    assert fake_client.chat.completions.create.call_count == 1

def test_groq_invalid_model_no_pointless_retries():
    fake_client = MagicMock()
    model_exc = Exception("404 The model `non-existent-model` does not exist: notfounderror")
    fake_client.chat.completions.create.side_effect = model_exc

    provider = GroqProvider(
        api_key="gsk_key",
        model="non-existent-model",
        max_retries=3,
        initial_backoff=0.01
    )
    provider._client = fake_client

    with pytest.raises(Exception) as exc_info:
        provider.generate_answer("Test", "Context")

    assert "404" in str(exc_info.value)
    assert fake_client.chat.completions.create.call_count == 1

def test_llm_service_routes_to_groq_by_default():
    fake_primary = MagicMock()
    fake_primary.provider_name = "groq"
    fake_primary.generate_answer.return_value = GenerationResult(
        text="Answer via Groq",
        provider="groq",
        model="llama-3.3-70b-versatile",
        tokens_used=30
    )

    service = LLMService(
        api_key="gsk_test_123",
        primary_provider=fake_primary
    )
    assert service.has_active_api_key
    assert service.active_provider_name == "groq"

    ans = service.answer_question("What is the speed?", "Speed is 100 km/h.")
    assert ans.provider == "groq"
    assert "Answer via Groq" in ans.text

def test_llm_service_quota_exhaustion_fallback():
    fake_primary = MagicMock()
    fake_primary.provider_name = "groq"
    fake_primary.analyze_document.side_effect = Exception("429 rate_limit_exceeded: TPM limit reached")

    service = LLMService(
        api_key="gsk_test_123",
        primary_provider=fake_primary
    )

    text = "Overview of the project. Team consists of Alice and Bob. Project deadline is next week."
    result = service.analyze_document(text)

    # Seamlessly falls back to heuristic extraction with clear quota attribution
    assert result["quota_exceeded"] is True
    assert result["provider"] == "quota_exhausted"
    assert "summary" in result
    assert "Notice: Groq API quota/rate limit reached" in result["summary"]

def test_groq_conversational_answer_generation():
    fake_client = MagicMock()
    fake_choice = MagicMock()
    fake_choice.message.content = "The storage limit is 50 GB as previously mentioned."
    fake_choice.finish_reason = "stop"
    fake_response = MagicMock(choices=[fake_choice], usage=MagicMock(total_tokens=40))
    fake_client.chat.completions.create.return_value = fake_response

    provider = GroqProvider(api_key="gsk_valid_key")
    provider._client = fake_client

    history = [
        {"role": "user", "content": "What is the max storage?"},
        {"role": "assistant", "content": "The max storage is 50 GB."}
    ]
    result = provider.generate_conversational_answer(
        question="Can it be expanded beyond that?",
        context="Storage capacity is 50 GB maximum.",
        history=history
    )

    assert result.provider == "groq"
    assert "50 GB" in result.text
    call_args = fake_client.chat.completions.create.call_args[1]
    messages = call_args["messages"]
    assert len(messages) >= 3  # system, user (from history), assistant (from history), user (current)

def test_groq_explain_comparison():
    fake_client = MagicMock()
    fake_choice = MagicMock()
    fake_choice.message.content = "Document B increases storage from 200 GB to 500 GB."
    fake_choice.finish_reason = "stop"
    fake_response = MagicMock(choices=[fake_choice], usage=MagicMock(total_tokens=45))
    fake_client.chat.completions.create.return_value = fake_response

    provider = GroqProvider(api_key="gsk_valid_key")
    provider._client = fake_client

    diffs = {
        "modifications": [{
            "topic": "Storage",
            "document_a": "200 GB",
            "document_b": "500 GB",
            "explanation": "Updated capacity."
        }],
        "additions": [],
        "removals": [],
        "conflicts": [],
        "common": []
    }
    result = provider.explain_comparison("Spec A", "Spec B", diffs)
    assert result.provider == "groq"
    assert "Document B increases storage" in result.text
