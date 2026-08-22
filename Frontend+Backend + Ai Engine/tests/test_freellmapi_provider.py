import pytest
import pytest_asyncio
import json
from unittest.mock import patch, AsyncMock, MagicMock
from ai_engine.providers.ai_provider import FreeLLMAPIProvider
import httpx

@pytest.mark.asyncio
async def test_freellmapi_generate_structured():
    provider = FreeLLMAPIProvider(base_url="http://localhost:3001/v1", api_key="test_key", model="gpt-oss-120b")
    
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": '{"answer": "test"}'
                }
            }
        ]
    }
    mock_response.headers = {"X-Routed-Via": "mock-route"}
    mock_response.raise_for_status = MagicMock()
    
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        
        result = await provider.generate_structured(
            prompt="test prompt",
            response_schema={"type": "object", "properties": {"answer": {"type": "string"}}}
        )
        
        assert result == {"answer": "test"}

@pytest.mark.asyncio
async def test_freellmapi_multimodal_fallback():
    provider = FreeLLMAPIProvider(base_url="http://localhost:3001/v1", api_key="test_key", model="gpt-oss-120b")
    result = await provider.analyze_multimodal(
        prompt="test",
        response_schema={"type": "object", "properties": {"video_desc": {"type": "string"}}}
    )
    
    assert result == {"video_desc": "Vision analysis unavailable for FreeLLMAPI"}

@pytest.mark.asyncio
async def test_freellmapi_extract_attributes():
    provider = FreeLLMAPIProvider(base_url="http://localhost:3001/v1", api_key="test_key", model="gpt-oss-120b")
    
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": '{"attributes": [{"attribute": "color", "value": "red", "unit": null, "status": "DIRECTLY_SUPPORTED", "evidence_snippet": "is red", "source": "test", "confidence": 0.9}]}'
                }
            }
        ]
    }
    mock_response.headers = {}
    mock_response.raise_for_status = MagicMock()
    
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        
        result = await provider.extract_attributes(
            product_info={"name": "test"},
            evidence_texts=["is red"],
            required_attributes=["color"]
        )
        
        assert len(result) == 1
        assert result[0]["attribute"] == "color"
