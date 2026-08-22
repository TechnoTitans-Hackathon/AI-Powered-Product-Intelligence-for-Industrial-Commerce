"""Engine Service — the production AIService implementation.

This is the integration heart. It implements the backend's AIService interface
and drives Aman's AI Intelligence Pipeline with real backend infrastructure.

Architecture:
    Backend API → EngineService → ProductIntelligencePipeline
                                    ↓
                              DiscoveryAgent (AI)
                                    ↓
                              BackendRetrieverAdapter → Backend Vector Store
                                    ↓
                              KnowledgeDecisionEngine (AI)
                                    ↓
                              BackendResearchAdapter → Backend External Acquisition
                                    ↓
                              IntelligenceAgent (AI)
                                    ↓
                              ValidationEngine (AI)
                                    ↓
                              ConfidenceEngine (AI)
                                    ↓
                              CommerceOutputAdapter (AI)
                                    ↓
                              OutputAdapter → Backend DB
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional
from dotenv import load_dotenv
load_dotenv()


from ai_engine.orchestration.pipeline import PipelineResult, ProductIntelligencePipeline
from ai_engine.providers.ai_provider import AIProviderInterface, OllamaProvider
from ai_engine.schemas import ProductInput

from backend.ai_interface.interface import AIService
from backend.schemas.ai_contract import AIServiceRequest, AIServiceResponse, AIProcessingMode
from backend.core.config import settings
from backend.integration.retrieval_adapter import BackendRetrieverAdapter
from backend.integration.research_adapter import BackendResearchAdapter
from backend.integration.output_adapter import intelligence_to_ai_response, pipeline_result_to_full_response
from ai_engine.tools.registry import ToolRegistry
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class AIPolicy:
    mode: AIProcessingMode
    agent1_provider: str
    agent1_model: str
    agent2_provider: str
    agent2_model: str
    external_allowed: bool

def resolve_ai_policy(mode: AIProcessingMode) -> AIPolicy:
    """Centralized policy resolver converting requested mode into explicit backend provider config."""
    default_agent1_provider = settings.AI_ENGINE_AGENT1_MODE.lower() if settings.AI_ENGINE_AGENT1_MODE else "freellmapi"
    default_agent2_provider = settings.AI_ENGINE_AGENT2_MODE.lower() if settings.AI_ENGINE_AGENT2_MODE else "freellmapi"

    def _get_model(provider: str, mode: AIProcessingMode) -> str:
        if provider == "freellmapi":
            return "gpt-oss-120b"
        elif provider == "xai":
            return "grok-4.5"
        else:
            return "gemini-1.5-pro-latest" if mode == AIProcessingMode.DEEP else "gemini-1.5-flash-latest"

    if mode == AIProcessingMode.LOCAL:
        return AIPolicy(
            mode=mode,
            agent1_provider="ollama",
            agent1_model="qwen3.5:9b-q4_K_M",
            agent2_provider="ollama",
            agent2_model="qwen3.5:9b-q4_K_M",
            external_allowed=False,
        )
    elif mode == AIProcessingMode.FAST:
        return AIPolicy(
            mode=mode,
            agent1_provider=default_agent1_provider,
            agent1_model=_get_model(default_agent1_provider, mode),
            agent2_provider=default_agent2_provider,
            agent2_model=_get_model(default_agent2_provider, mode),
            external_allowed=True,
        )
    elif mode == AIProcessingMode.DEEP:
        return AIPolicy(
            mode=mode,
            agent1_provider=default_agent1_provider,
            agent1_model=_get_model(default_agent1_provider, mode),
            agent2_provider=default_agent2_provider,
            agent2_model=_get_model(default_agent2_provider, mode),
            external_allowed=True,
        )
    else: # AUTO
        return AIPolicy(
            mode=mode,
            agent1_provider=default_agent1_provider,
            agent1_model=_get_model(default_agent1_provider, mode),
            agent2_provider=default_agent2_provider,
            agent2_model=_get_model(default_agent2_provider, mode),
            external_allowed=True,
        )


def _create_ai_provider(policy: AIPolicy) -> AIProviderInterface:
    """Create the AI provider for Agent 1 based on configuration."""
    if policy.agent1_provider == "ollama":
        logger.info(f"AI Engine Agent 1: using OllamaProvider (model={policy.agent1_model})")
        return OllamaProvider(model=policy.agent1_model)
        
    if policy.agent1_provider == "freellmapi":
        from ai_engine.providers.ai_provider import FreeLLMAPIProvider
        if not policy.external_allowed:
            raise RuntimeError(f"LOCAL mode strict violation: Agent 1 attempting to initialize external provider {policy.agent1_provider}")
        logger.info(f"AI Engine Agent 1: using FreeLLMAPIProvider (model={policy.agent1_model})")
        return FreeLLMAPIProvider(
            base_url=settings.FREELLMAPI_BASE_URL,
            api_key=settings.FREELLMAPI_API_KEY,
            model=policy.agent1_model
        )

    if policy.agent1_provider == "gemini":
        from ai_engine.providers.ai_provider import GeminiProvider
        if not policy.external_allowed:
            raise RuntimeError(f"LOCAL mode strict violation: Agent 1 attempting to initialize external provider {policy.agent1_provider}")
        if not settings.GEMINI_API_KEY_AGENT1:
            raise RuntimeError("GEMINI_API_KEY_AGENT1 is required")
        logger.info(f"AI Engine Agent 1: using GeminiProvider (model={policy.agent1_model})")
        return GeminiProvider(api_key=settings.GEMINI_API_KEY_AGENT1, model=policy.agent1_model)

    if policy.agent1_provider == "xai":
        from ai_engine.providers.ai_provider import XAIProvider
        if not policy.external_allowed:
            raise RuntimeError(f"LOCAL mode strict violation: Agent 1 attempting to initialize external provider {policy.agent1_provider}")
        if not settings.XAI_API_KEY_AGENT1:
            raise RuntimeError("Agent 1 key missing")
        logger.info(f"AI Engine Agent 1: using XAIProvider (model={policy.agent1_model})")
        return XAIProvider(
            api_key=settings.XAI_API_KEY_AGENT1,
            model=policy.agent1_model,
            max_rps=settings.XAI_MAX_RPS,
            max_tpm=settings.XAI_MAX_TPM
        )

    raise RuntimeError(f"Unknown Agent 1 mode: {policy.agent1_provider}")


def _create_agent2_provider(policy: AIPolicy) -> AIProviderInterface:
    """Create the AI provider for Agent 2 based on configuration."""
    if policy.agent2_provider == "ollama":
        logger.info(f"AI Engine Agent 2: using OllamaProvider (model={policy.agent2_model})")
        return OllamaProvider(model=policy.agent2_model)
        
    if policy.agent2_provider == "freellmapi":
        from ai_engine.providers.ai_provider import FreeLLMAPIProvider
        if not policy.external_allowed:
            raise RuntimeError(f"LOCAL mode strict violation: Agent 2 attempting to initialize external provider {policy.agent2_provider}")
        logger.info(f"AI Engine Agent 2: using FreeLLMAPIProvider (model={policy.agent2_model})")
        return FreeLLMAPIProvider(
            base_url=settings.FREELLMAPI_BASE_URL,
            api_key=settings.FREELLMAPI_API_KEY,
            model=policy.agent2_model
        )

    if policy.agent2_provider == "gemini":
        from ai_engine.providers.ai_provider import GeminiProvider
        if not policy.external_allowed:
            raise RuntimeError(f"LOCAL mode strict violation: Agent 2 attempting to initialize external provider {policy.agent2_provider}")
        if not settings.GEMINI_API_KEY_AGENT2:
            raise RuntimeError("GEMINI_API_KEY_AGENT2 is required")
        logger.info(f"AI Engine Agent 2: using GeminiProvider (model={policy.agent2_model})")
        return GeminiProvider(api_key=settings.GEMINI_API_KEY_AGENT2, model=policy.agent2_model)

    if policy.agent2_provider == "xai":
        from ai_engine.providers.ai_provider import XAIProvider
        if not policy.external_allowed:
            raise RuntimeError(f"LOCAL mode strict violation: Agent 2 attempting to initialize external provider {policy.agent2_provider}")
        if not settings.XAI_API_KEY_AGENT2:
            raise RuntimeError("Agent 2 key missing")
        logger.info(f"AI Engine Agent 2: using XAIProvider (model={policy.agent2_model})")
        return XAIProvider(
            api_key=settings.XAI_API_KEY_AGENT2,
            model=policy.agent2_model,
            max_rps=settings.XAI_MAX_RPS,
            max_tpm=settings.XAI_MAX_TPM
        )

    raise RuntimeError(f"Unknown AI_ENGINE_AGENT2_MODE: {policy.agent2_provider}")


from ai_engine.retrieval.retriever import RetrieverInterface
from ai_engine.schemas import Evidence as AIEvidence, EvidenceSet, RetrievalRequest, RetrievalResponse, SourceType

class PreFetchedEvidenceRetriever(RetrieverInterface):
    """Wraps already-retrieved evidence for the Hackathon pipeline."""
    def __init__(self, pre_retrieved_evidence: list):
        self._evidence = pre_retrieved_evidence

    async def retrieve(self, request: RetrievalRequest) -> RetrievalResponse:
        evidence_set = EvidenceSet()
        for i, ev in enumerate(self._evidence):
            def _get(attr_name, default=None):
                if hasattr(ev, attr_name):
                    val = getattr(ev, attr_name)
                    return val if val is not None else default
                if isinstance(ev, dict):
                    return ev.get(attr_name, default)
                return default

            source_id = _get('source_id', f'techno_ev_{i}')
            content = _get('content', '')
            doc = _get('document', _get('document_name', source_id))
            url = _get('url')
            page = _get('page')
            score = float(_get('score', 0.5) or 0.5)
            provenance = _get('provenance', _get('provenance_json', {})) or {}

            ev_item = AIEvidence(
                evidence_id=source_id,
                content=content,
                source=doc or 'unknown_source',
                source_url=url,
                page=page,
                section=None,
                score=score,
                source_type=SourceType.AUTHORIZED_CATALOG,
                metadata=provenance if isinstance(provenance, dict) else {},
            )
            evidence_set.evidence.append(ev_item)
        evidence_set.compute_metrics()
        return RetrievalResponse(
            evidence_set=evidence_set,
            query_used=request.query,
            retrieval_time_ms=0.0,
            source_count=len(self._evidence),
        )

def _build_pipeline(retriever=None, ai_mode: AIProcessingMode = AIProcessingMode.AUTO) -> ProductIntelligencePipeline:
    """Build the full AI intelligence pipeline with backend adapters."""
    policy = resolve_ai_policy(ai_mode)
    logger.info(f"Resolved AI Policy for mode {ai_mode}: {policy}")

    provider = _create_ai_provider(policy)
    agent2_provider = _create_agent2_provider(policy)
    
    # Qwen #2 Router MUST be Ollama (local) as per architecture
    from ai_engine.providers.ai_provider import OllamaProvider
    router_provider = OllamaProvider(model="qwen3.5:9b-q4_K_M")
    retriever = retriever or BackendRetrieverAdapter()
    researcher = BackendResearchAdapter()

    tool_registry = ToolRegistry()
    tool_registry.register_tool(
        name="vector_search", 
        handler=retriever.retrieve, 
        description="Search internal knowledge base for evidence using vector similarity."
    )
    if policy.external_allowed:
        tool_registry.register_tool(
            name="web_acquire", 
            handler=researcher.research, 
            description="Perform targeted external research to find missing attributes."
        )
    else:
        logger.info(f"LOCAL mode: web_acquire tool disabled for strict isolation.")

    pipeline = ProductIntelligencePipeline(
        ai_provider=provider,
        retriever=retriever,
        researcher=researcher,
        intelligence_provider=agent2_provider,
        tool_registry=tool_registry,
        router_provider=router_provider,
    )
    logger.info(
        f"AI Pipeline initialized: provider={provider.get_provider_name()}, "
        f"agent2_provider={agent2_provider.get_provider_name()}, "
        f"router={router_provider.get_provider_name()}, "
        f"retriever=BackendRetrieverAdapter, researcher={'BackendResearchAdapter' if policy.external_allowed else 'Disabled'}, "
        f"tools=registered"
    )
    return pipeline


# Singleton pipeline instance — created lazily
_pipeline_instance: Optional[ProductIntelligencePipeline] = None


def get_pipeline(ai_mode: AIProcessingMode = AIProcessingMode.AUTO) -> ProductIntelligencePipeline:
    """Get or create the singleton pipeline instance. Note: caching may ignore dynamic mode changes."""
    # In production with dynamic modes, we should ideally not use a strict singleton, 
    # but build a new pipeline if the mode changes, or avoid get_pipeline.
    # For now, we will bypass get_pipeline and build fresh in the service.
    global _pipeline_instance
    if _pipeline_instance is None:
        _pipeline_instance = _build_pipeline(ai_mode=ai_mode)
    return _pipeline_instance



def _backend_request_to_product_input(request: AIServiceRequest) -> ProductInput:
    """Convert backend's AIServiceRequest to AI engine's ProductInput.

    Maps the backend's product dict to the AI engine's typed model.
    """
    pi = request.product_input
    return ProductInput(
        mfg_part_number=pi.get("sku") or pi.get("mpn") or pi.get("name", ""),
        part_description=pi.get("description") or pi.get("name", ""),
        manufacturer=pi.get("manufacturer", ""),
        brand=pi.get("brand", ""),
        unilog_brand=pi.get("unilog_brand", ""),
        dib_brand=pi.get("dib_brand", ""),
        category=pi.get("category", ""),
        industry=pi.get("industry", ""),
        additional_text=pi.get("additional_text", ""),
    )


class IntegratedAIService(AIService):
    """Production AIService implementation that routes through
    Aman's full AI Intelligence Pipeline.

    This is the production implementation.
    The pipeline handles the COMPLETE intelligence flow:
    Discovery → Retrieval → Knowledge Decision → Research →
    Intelligence → Normalization → Validation → Confidence → Commerce
    """

    async def process_product(self, request: AIServiceRequest, pre_retrieved_evidence: Optional[list] = None) -> AIServiceResponse:
        """Process a product through the full AI intelligence pipeline.

        Returns AIServiceResponse for backward compatibility with
        ProductService.apply_ai_response().
        """
        logger.info("IntegratedAIService: processing product through AI pipeline")

        product_input = _backend_request_to_product_input(request)
        # Always build fresh pipeline to respect dynamic ai_mode
        if pre_retrieved_evidence is not None:
            pipeline = _build_pipeline(retriever=PreFetchedEvidenceRetriever(pre_retrieved_evidence), ai_mode=request.ai_mode)
        else:
            pipeline = _build_pipeline(ai_mode=request.ai_mode)

        # Run the async pipeline
        pipeline_result: PipelineResult = await pipeline.process(product_input)

        if not pipeline_result.success:
            logger.warning(
                f"IntegratedAIService: pipeline did not fully succeed. "
                f"Errors: {[e.message for e in pipeline_result.errors]}"
            )

        # Convert to backend format
        if pipeline_result.intelligence:
            response = intelligence_to_ai_response(pipeline_result.intelligence, pipeline_result)
        else:
            # Fallback: return minimal response
            response = AIServiceResponse(
                product=request.product_input,
                attributes=[],
                review_required=True,
                explanation={"errors": [e.message for e in pipeline_result.errors]}
            )

        return response

    async def process_intelligence(
        self,
        product_input: ProductInput,
        pre_retrieved_evidence: Optional[list] = None,
        ai_mode: Optional[AIProcessingMode] = None,
    ) -> PipelineResult:
        """Process a product and return the FULL pipeline result.

        Used by the new /products/intelligence endpoint.
        Returns the complete PipelineResult with all intelligence metadata.
        """
        mode = ai_mode or AIProcessingMode.AUTO
        if pre_retrieved_evidence is not None:
            pipeline = _build_pipeline(retriever=PreFetchedEvidenceRetriever(pre_retrieved_evidence), ai_mode=ai_mode)
        else:
            pipeline = _build_pipeline(ai_mode=ai_mode)
        return await pipeline.process(product_input)


# Singleton service instance
integrated_ai_service = IntegratedAIService()
