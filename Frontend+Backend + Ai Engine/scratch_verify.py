import os
import sys
from dotenv import load_dotenv

load_dotenv()

from backend.core.config import settings
from backend.integration.engine_service import resolve_ai_policy, _create_ai_provider, _create_agent2_provider
from backend.schemas.ai_contract import AIProcessingMode
from ai_engine.providers.ai_provider import XAIProvider, OllamaProvider

def test_xai_configuration():
    print("--- XAI CONFIGURATION AUDIT ---")
    
    # Verify .env variables are loaded
    print(f"\n1. ENV LOAD VERIFICATION:")
    print(f"XAI_MODEL_AGENT1: {settings.XAI_MODEL_AGENT1}")
    print(f"XAI_MODEL_AGENT2: {settings.XAI_MODEL_AGENT2}")
    
    # We must explicitly set the modes to xai for the test
    settings.AI_ENGINE_AGENT1_MODE = "xai"
    settings.AI_ENGINE_AGENT2_MODE = "xai"
    
    policy = resolve_ai_policy(AIProcessingMode.AUTO)
    
    print(f"\n2. POLICY RESOLUTION:")
    print(f"Agent 1 Provider Selected: {policy.agent1_provider}")
    print(f"Agent 2 Provider Selected: {policy.agent2_provider}")
    
    assert policy.agent1_provider == "xai", "Policy failed to select xai for agent 1"
    assert policy.agent2_provider == "xai", "Policy failed to select xai for agent 2"
    
    print(f"\n3. CREDENTIAL VERIFICATION (AGENT 1):")
    try:
        # XAI_API_KEY_AGENT1 is empty in .env as requested
        provider1 = _create_ai_provider(policy)
        print("ERROR: Agent 1 initialized xAI without a key!")
        sys.exit(1)
    except RuntimeError as e:
        print(f"SUCCESS: Agent 1 caught missing key -> {e}")
        assert "XAI_API_KEY_AGENT1" in str(e)
        
    print(f"\n4. CREDENTIAL VERIFICATION (AGENT 2):")
    try:
        # XAI_API_KEY_AGENT2 is empty in .env as requested
        provider2 = _create_agent2_provider(policy)
        print("ERROR: Agent 2 initialized xAI without a key!")
        sys.exit(1)
    except RuntimeError as e:
        print(f"SUCCESS: Agent 2 caught missing key -> {e}")
        assert "XAI_API_KEY_AGENT2" in str(e)
        
    print(f"\n5. QWEN/OLLAMA ISOLATION:")
    local_policy = resolve_ai_policy(AIProcessingMode.LOCAL)
    provider_local = _create_ai_provider(local_policy)
    print(f"Local Agent 1 Provider: {type(provider_local).__name__}")
    assert isinstance(provider_local, OllamaProvider)
    
    print("\nALL CONFIGURATION VERIFICATION TESTS PASSED.")

if __name__ == "__main__":
    test_xai_configuration()
