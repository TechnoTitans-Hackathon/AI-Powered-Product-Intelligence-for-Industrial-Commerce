import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

from ai_engine.providers.ai_provider import (
    XAIProvider,
    XAIAuthenticationError,
    XAIRateLimitError,
    XAITimeoutError,
    XAIServerError,
    XAISchemaValidationError
)

@pytest.fixture
def xai_provider():
    return XAIProvider(api_key="test-key", model="grok-4.5", max_rps=100, max_tpm=10000)

@pytest.mark.asyncio
async def test_xai_provider_initialization():
    provider = XAIProvider(api_key="test-key", model="grok-4.5")
    assert provider.api_key == "test-key"
    assert provider.model_name == "grok-4.5"
    assert provider.get_provider_name() == "xAI (grok-4.5)"

@pytest.mark.asyncio
@patch("ai_engine.providers.ai_provider.AsyncClient.post")
async def test_xai_generate_structured_success(mock_post, xai_provider):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": '{"test_key": "test_value"}'
                }
            }
        ]
    }
    mock_post.return_value = mock_response

    schema = {"title": "TestSchema", "type": "object", "properties": {"test_key": {"type": "string"}}}
    result = await xai_provider.generate_structured(
        prompt="Test prompt",
        system_instruction="Test sys",
        response_schema=schema
    )
    
    assert result == {"test_key": "test_value"}
    
    # Verify request payload format
    call_kwargs = mock_post.call_args[1]
    assert call_kwargs["headers"]["Authorization"] == "Bearer test-key"
    assert "json" in call_kwargs
    payload = call_kwargs["json"]
    assert payload["model"] == "grok-4.5"
    assert payload["response_format"]["type"] == "json_schema"
    assert payload["response_format"]["json_schema"]["name"] == "TestSchema"
    assert payload["response_format"]["json_schema"]["strict"] is True

@pytest.mark.asyncio
@patch("ai_engine.providers.ai_provider.AsyncClient.post")
async def test_xai_auth_error(mock_post, xai_provider):
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = "Unauthorized"
    mock_post.return_value = mock_response

    with pytest.raises(XAIAuthenticationError):
        await xai_provider.generate_structured("Test prompt")

@pytest.mark.asyncio
@patch("ai_engine.providers.ai_provider.AsyncClient.post")
async def test_xai_rate_limit_backoff_and_fail(mock_post, xai_provider):
    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_response.headers = {"Retry-After": "0.1"} # small delay for test
    mock_post.return_value = mock_response

    with pytest.raises(XAIRateLimitError):
        await xai_provider.generate_structured("Test prompt")
    
    # Should have retried 3 times, so 4 calls total
    assert mock_post.call_count == 4

@pytest.mark.asyncio
@patch("ai_engine.providers.ai_provider.AsyncClient.post")
async def test_xai_schema_validation_error(mock_post, xai_provider):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": '{"invalid json'
                }
            }
        ]
    }
    mock_post.return_value = mock_response

    with pytest.raises(XAISchemaValidationError):
        await xai_provider.generate_structured("Test prompt")
