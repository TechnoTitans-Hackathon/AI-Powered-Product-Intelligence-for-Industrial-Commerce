import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from ai_engine.orchestration.pipeline import ProductIntelligencePipeline
from ai_engine.providers.ai_provider import AIProviderInterface
from ai_engine.schemas import (
    ProductInput,
    DiscoveryResult,
    ProductIdentity,
    EvidenceSet,
    Evidence,
    ProcessingStatus
)

class MockAgent1Provider(AIProviderInterface):
    """Mock Provider that simulates Agent 1 (Ollama)."""
    def __init__(self):
        self.generate_calls = 0
        self.model_name = "qwen3.5:9b-q4_K_M"
    
    def get_provider_name(self):
        return "Ollama Mock"

    async def generate_structured(self, prompt, **kwargs):
        self.generate_calls += 1
        if "Evaluate if deep reasoning (Agent 2) is required" in prompt:
            return {
                "agent2_required": True,
                "reason": "Complex inference needed",
                "task": {"objective": "Analyze material properties"}
            }
        return {}

    async def analyze_product(self, product_info, task, context=""):
        return {}
    
    async def extract_attributes(self, product_info, evidence_texts, required_attributes):
        return []

    async def analyze_multimodal(self, multimodal_request):
        return {}


class MockAgent2Provider(AIProviderInterface):
    """Mock Provider that simulates Agent 2 (Gemini)."""
    def __init__(self):
        self.generate_calls = 0
        self.analyze_calls = 0
        self.extract_calls = 0
        self.model_name = "gemini-2.0-flash"
    
    def get_provider_name(self):
        return "Gemini Mock"

    async def generate_structured(self, prompt, **kwargs):
        self.generate_calls += 1
        return {}

    async def analyze_product(self, product_info, task, context=""):
        self.analyze_calls += 1
        return {}
    
    async def extract_attributes(self, product_info, evidence_texts, required_attributes):
        self.extract_calls += 1
        return [
            {
                "attribute": "material",
                "value": "Steel",
                "status": "DIRECTLY_SUPPORTED",
                "confidence": 0.95
            }
        ]

    async def analyze_multimodal(self, multimodal_request):
        return {}

@pytest.fixture
def mock_retriever():
    retriever = MagicMock()
    retriever.retrieve = AsyncMock(return_value=MagicMock(evidence_set=EvidenceSet()))
    return retriever

@pytest.fixture
def mock_researcher():
    researcher = MagicMock()
    researcher.research = AsyncMock(return_value=None)
    return researcher

@pytest.mark.asyncio
async def test_production_pipeline_provider_routing(mock_retriever, mock_researcher):
    """Verify that Agent 1 and Agent 2 calls go to their respective providers."""
    agent1_provider = MockAgent1Provider()
    agent2_provider = MockAgent2Provider()

    # The discovery agent internally needs to return a valid object to progress the pipeline
    with patch("ai_engine.agents.discovery_agent.DiscoveryAgent.discover") as mock_discover:
        mock_discover.return_value = DiscoveryResult(
            request_id="req_123",
            product_identity=ProductIdentity(part_number="PN123", manufacturer="TestMfg"),
            missing_information=["material"],
            known_information=[],
            required_attributes=["material"],
            actions=[],
            research_required=False
        )

        pipeline = ProductIntelligencePipeline(
            ai_provider=agent1_provider,
            intelligence_provider=agent2_provider,
            retriever=mock_retriever,
            researcher=mock_researcher
        )

        product_input = ProductInput(
            mfg_part_number="PN123",
            part_description="Steel Pipe"
        )

        result = await pipeline.process(product_input)

        assert result.success
        assert agent1_provider.generate_calls == 1  # Qwen Router call
        assert agent2_provider.extract_calls == 1   # Agent 2 extraction call
        assert agent2_provider.analyze_calls == 1   # Agent 2 synthesis call

        # Ensure Agent 1 wasn't used for extraction
        assert hasattr(agent1_provider, "extract_calls") is False

        assert result.diagnostics["provider"] == "Ollama Mock"
        assert result.diagnostics["agent2_required"] is True
        assert result.diagnostics["step_6_enrichment"]["via_agent2"] is True
