import pytest
from unittest.mock import patch

from backend.core.config import settings
from backend.schemas.ai_contract import AIProcessingMode
from backend.integration.engine_service import resolve_ai_policy, _create_ai_provider, _create_agent2_provider
from ai_engine.providers.ai_provider import XAIProvider

@pytest.fixture(autouse=True)
def setup_xai_config():
    # Save original
    orig_agent1 = settings.AI_ENGINE_AGENT1_MODE
    orig_agent2 = settings.AI_ENGINE_AGENT2_MODE
    orig_xai_key1 = settings.XAI_API_KEY_AGENT1
    orig_xai_key2 = settings.XAI_API_KEY_AGENT2
    orig_xai_model1 = settings.XAI_MODEL_AGENT1
    orig_xai_model2 = settings.XAI_MODEL_AGENT2

    # Set mock test config
    settings.AI_ENGINE_AGENT1_MODE = "xai"
    settings.AI_ENGINE_AGENT2_MODE = "xai"
    settings.XAI_API_KEY_AGENT1 = "xai-agent1-test"
    settings.XAI_API_KEY_AGENT2 = "xai-agent2-test"
    settings.XAI_MODEL_AGENT1 = "grok-4.5"
    settings.XAI_MODEL_AGENT2 = "grok-4.5"

    yield

    # Restore
    settings.AI_ENGINE_AGENT1_MODE = orig_agent1
    settings.AI_ENGINE_AGENT2_MODE = orig_agent2
    settings.XAI_API_KEY_AGENT1 = orig_xai_key1
    settings.XAI_API_KEY_AGENT2 = orig_xai_key2
    settings.XAI_MODEL_AGENT1 = orig_xai_model1
    settings.XAI_MODEL_AGENT2 = orig_xai_model2


def test_resolve_ai_policy_xai_auto():
    policy = resolve_ai_policy(AIProcessingMode.AUTO)
    assert policy.agent1_provider == "xai"
    assert policy.agent2_provider == "xai"
    assert policy.agent1_model == "grok-4.5"
    assert policy.agent2_model == "grok-4.5"
    assert policy.external_allowed is True

def test_resolve_ai_policy_local_overrides_xai():
    policy = resolve_ai_policy(AIProcessingMode.LOCAL)
    # LOCAL mode must strictly force Ollama regardless of agent settings
    assert policy.agent1_provider == "ollama"
    assert policy.agent2_provider == "ollama"
    assert policy.external_allowed is False

def test_create_ai_provider_xai_agent1():
    policy = resolve_ai_policy(AIProcessingMode.AUTO)
    provider = _create_ai_provider(policy)
    
    assert isinstance(provider, XAIProvider)
    assert provider.api_key == "xai-agent1-test"
    assert provider.model_name == "grok-4.5"

def test_create_ai_provider_xai_agent2():
    policy = resolve_ai_policy(AIProcessingMode.AUTO)
    provider = _create_agent2_provider(policy)
    
    assert isinstance(provider, XAIProvider)
    assert provider.api_key == "xai-agent2-test"
    assert provider.model_name == "grok-4.5"

def test_create_ai_provider_xai_missing_key():
    settings.XAI_API_KEY_AGENT1 = ""
    policy = resolve_ai_policy(AIProcessingMode.AUTO)
    
    with pytest.raises(RuntimeError, match="Agent 1 key missing"):
        _create_ai_provider(policy)
