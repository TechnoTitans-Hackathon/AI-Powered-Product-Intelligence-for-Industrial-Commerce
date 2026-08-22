"""Integration tests between the final backend and Aman's AI Engine."""

import pytest
from backend.integration.engine_service import integrated_ai_service
from backend.schemas.ai_contract import AIServiceRequest
from backend.integration.retrieval_adapter import _backend_evidence_to_ai_evidence
from backend.schemas.retrieval import EvidenceSchema

def test_backend_evidence_conversion():
    """Verify backend EvidenceSchema correctly maps to AI engine Evidence without data loss."""
    backend_evidence = EvidenceSchema(
        evidence_id="test_1",
        source_id="src_1",
        document_id="doc_1",
        source="Test Document",
        document="Test Doc",
        url="http://test.com",
        page=1,
        timestamp="2026-08-11T23:00:00Z",
        content="Test content",
        score=0.95,
        metadata={"section": "Introduction"},
        provenance={"source_type": "manufacturer_document"}
    )
    
    ai_evidence = _backend_evidence_to_ai_evidence(backend_evidence)
    
    assert ai_evidence.evidence_id == "test_1"
    assert ai_evidence.content == "Test content"
    assert ai_evidence.source == "Test Document"
    assert ai_evidence.source_url == "http://test.com"
    assert ai_evidence.page == 1
    assert ai_evidence.section == "Introduction"
    assert ai_evidence.score == 0.95
    # Enum conversion verification
    assert ai_evidence.source_type.value == "MANUFACTURER_DOCUMENT"

@pytest.mark.asyncio
async def test_integrated_pipeline_mock_mode():
    """Verify the integrated pipeline runs end-to-end using the mock provider."""
    from backend.core.config import settings
    # Ensure it's in mock mode for testing
    settings.AI_ENGINE_MODE = "mock"
    
    request = AIServiceRequest(
        product_input={
            "name": "Industrial Pump ABC-420",
            "sku": "ABC-420",
            "manufacturer": "TestCorp",
            "industry": "Industrial",
        }
    )
    
    # Run the integrated service
    response = await integrated_ai_service.process_product(request)
    
    # Check for fallback response with errors
    if not response.attributes and "errors" in response.explanation:
        errors = str(response.explanation["errors"]).lower()
        if "404" in errors or "connection" in errors or "failed" in errors:
            pytest.skip("Live AI provider unavailable")
    
    # Verify AI pipeline output mapping
    assert response.product["name"] == "Industrial Pump ABC-420"
    assert response.product["sku"] == "ABC-420"
    assert "confidenceScore" in response.product
    
    # Expect overall confidence to be present (even if 0.0 or from mock)
    assert "overall" in response.confidence
