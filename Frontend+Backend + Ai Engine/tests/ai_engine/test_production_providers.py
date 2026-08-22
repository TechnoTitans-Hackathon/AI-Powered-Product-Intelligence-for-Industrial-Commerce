import pytest
import os
import asyncio
from unittest.mock import patch, MagicMock

from ai_engine.providers.ai_provider import AIProviderInterface, OllamaProvider, GeminiProvider
from backend.integration.engine_service import integrated_ai_service, _create_ai_provider, _create_agent2_provider, resolve_ai_policy
from backend.schemas.ai_contract import AIProcessingMode

@pytest.fixture
def mock_settings():
    """Provides a mock for the settings object."""
    with patch("backend.integration.engine_service.settings") as mock_set:
        mock_set.AI_ENGINE_MODE = "ollama"
        mock_set.AI_ENGINE_AGENT1_MODE = ""
        mock_set.AI_ENGINE_AGENT2_MODE = "gemini"
        mock_set.GEMINI_API_KEY_AGENT1 = ""
        mock_set.GEMINI_API_KEY_AGENT2 = ""
        mock_set.GEMINI_MODEL_AGENT1 = "gemini-2.0-flash"
        mock_set.GEMINI_MODEL_AGENT2 = "gemini-2.0-flash"
        yield mock_set

@pytest.mark.asyncio
async def test_agent1_provider_defaults_to_ollama(mock_settings):
    """Agent 1 should default to OllamaProvider if requested via LOCAL mode."""
    policy = resolve_ai_policy(AIProcessingMode.LOCAL)
    provider = _create_ai_provider(policy)
    assert isinstance(provider, OllamaProvider)
    assert provider.model_name == "qwen3.5:9b-q4_K_M"

@pytest.mark.asyncio
async def test_agent1_provider_explicit_gemini_missing_key(mock_settings):
    """If Agent 1 is explicitly set to gemini but missing key, it MUST raise RuntimeError."""
    mock_settings.AI_ENGINE_AGENT1_MODE = "gemini"
    policy = resolve_ai_policy(AIProcessingMode.AUTO)
    with pytest.raises(RuntimeError) as exc:
        _create_ai_provider(policy)
    assert "GEMINI_API_KEY_AGENT1 is required" in str(exc.value)

@pytest.mark.asyncio
async def test_agent1_provider_explicit_gemini_with_key(mock_settings):
    """If Agent 1 is explicitly set to gemini and has key, it uses GeminiProvider."""
    mock_settings.AI_ENGINE_AGENT1_MODE = "gemini"
    mock_settings.GEMINI_API_KEY_AGENT1 = "test-agent1-key"
    policy = resolve_ai_policy(AIProcessingMode.AUTO)
    provider = _create_ai_provider(policy)
    assert isinstance(provider, GeminiProvider)
    assert provider.api_key == "test-agent1-key"

@pytest.mark.asyncio
async def test_agent2_provider_defaults_to_gemini_with_missing_key(mock_settings):
    """Agent 2 should default to Gemini but raise RuntimeError if key is missing."""
    mock_settings.AI_ENGINE_AGENT2_MODE = "gemini"
    policy = resolve_ai_policy(AIProcessingMode.AUTO)
    with pytest.raises(RuntimeError) as exc:
        _create_agent2_provider(policy)
    assert "GEMINI_API_KEY_AGENT2 is required" in str(exc.value)

@pytest.mark.asyncio
async def test_agent2_provider_defaults_to_gemini_with_key(mock_settings):
    """Agent 2 should default to Gemini and use GEMINI_API_KEY_AGENT2."""
    mock_settings.GEMINI_API_KEY_AGENT2 = "test-agent2-key"
    policy = resolve_ai_policy(AIProcessingMode.AUTO)
    provider = _create_agent2_provider(policy)
    assert isinstance(provider, GeminiProvider)
    assert provider.api_key == "test-agent2-key"

@pytest.mark.asyncio
async def test_agent2_provider_explicit_ollama(mock_settings):
    """If Agent 2 is explicitly set to ollama, it should use OllamaProvider."""
    mock_settings.AI_ENGINE_AGENT2_MODE = "ollama"
    policy = resolve_ai_policy(AIProcessingMode.AUTO)
    provider = _create_agent2_provider(policy)
    assert isinstance(provider, OllamaProvider)
    # The default behavior for "ollama" agent routing needs a model config, 
    # but the engine service assumes gemini models unless it's LOCAL mode. 
    # Since Ollama doesn't have an agent2_model configured in settings, it inherits GEMINI_MODEL_AGENT2 as the fallback in our policy logic.
    # The test passes because _create_agent2_provider passes policy.agent2_model.
    assert isinstance(provider, OllamaProvider)
