"""Product Intelligence Pipeline — full end-to-end orchestration."""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Optional

from ai_engine.agents.discovery_agent import DiscoveryAgent
from ai_engine.agents.intelligence_agent import IntelligenceAgent
from ai_engine.agents.knowledge_decision import KnowledgeDecisionEngine
from ai_engine.confidence.engine import ConfidenceEngine
from ai_engine.normalization.normalizer import NormalizationEngine
from ai_engine.output.commerce_adapter import CommerceOutputAdapter
from ai_engine.providers.ai_provider import AIProviderInterface
from ai_engine.retrieval.retriever import RetrieverInterface
from ai_engine.research.researcher import ResearchInterface
from ai_engine.validation.validator import ValidationEngine
from ai_engine.tools.registry import ToolRegistry
from ai_engine.schemas import (
    DiscoveryRequest,
    EvidenceSufficiency,
    NormalizedInput,
    ProcessingError,
    ProcessingStatus,
    ProductInput,
    ProductIntelligenceResult,
    ResearchRequest,
    ResearchTarget,
    RetrievalRequest,
    SourceType,
)
from ai_engine.tracing.emitter import trace_emitter, TraceEvent


logger = logging.getLogger(__name__)


class PipelineResult:
    """Complete pipeline output with diagnostics."""

    def __init__(self):
        self.intelligence: Optional[ProductIntelligenceResult] = None
        self.commerce_data: dict[str, str] = {}
        self.commerce_json: str = ""
        self.discovery_result: Any = None
        self.evidence_sufficiency: Optional[EvidenceSufficiency] = None
        self.all_evidence: Any = None  # EvidenceCollection
        self.validation_result: Any = None
        self.research_performed: bool = False
        self.processing_time_ms: float = 0.0
        self.errors: list[ProcessingError] = []
        self.diagnostics: dict[str, Any] = {}

    @property
    def success(self) -> bool:
        return (
            self.intelligence is not None
            and self.intelligence.processing_status == ProcessingStatus.COMPLETED
            and len(self.errors) == 0
        )


class ProductIntelligencePipeline:
    """Orchestrates the full product intelligence workflow.

    Flow:
    1. Normalize input
    2. Discovery Agent → identify product, find gaps
    3. Retrieve evidence from knowledge base
    4. Knowledge Decision → is evidence sufficient?
    5. If insufficient → targeted research
    6. Intelligence Agent → enrich with evidence
    7. Normalize values
    8. Validate
    9. Calculate confidence
    10. Adapt to commerce output
    """

    def __init__(
        self,
        ai_provider: AIProviderInterface,
        retriever: RetrieverInterface,
        researcher: ResearchInterface,
        confidence_engine: Optional[ConfidenceEngine] = None,
        validation_engine: Optional[ValidationEngine] = None,
        normalization_engine: Optional[NormalizationEngine] = None,
        commerce_adapter: Optional[CommerceOutputAdapter] = None,
        knowledge_decision: Optional[KnowledgeDecisionEngine] = None,
        intelligence_provider: Optional[AIProviderInterface] = None,
        tool_registry: Optional[ToolRegistry] = None,
        router_provider: Optional[AIProviderInterface] = None,
    ):
        self.ai_provider = ai_provider
        
        # Enforce provider separation (Rule 3)
        if intelligence_provider is None:
            # Production: NEVER silently reuse Agent 1 credentials (Rule 5 & 7)
            raise ValueError("intelligence_provider must be explicitly provided in production.")
        
        self.intelligence_provider = intelligence_provider

        # The Qwen Router for Agent 2 requirement evaluation MUST use the local planner model.
        # Fall back to ai_provider only for testing when explicit provider isn't passed.
        self.router_provider = router_provider or self.ai_provider

        self.retriever = retriever
        self.researcher = researcher
        self.confidence_engine = confidence_engine or ConfidenceEngine()
        self.validation_engine = validation_engine or ValidationEngine()
        self.normalization_engine = normalization_engine or NormalizationEngine()
        self.commerce_adapter = commerce_adapter or CommerceOutputAdapter()
        self.knowledge_decision = knowledge_decision or KnowledgeDecisionEngine()
        self.tool_registry = tool_registry or ToolRegistry()
        
        # Auto-register tools if not already registered (for tests and standalone usage)
        if not self.tool_registry.has_tool("vector_search") and self.retriever:
            self.tool_registry.register(
                name="vector_search",
                description="Search internal vector database",
                handler=self.retriever.retrieve,
                schema={"type": "object", "properties": {"query": {"type": "string"}}}
            )
            
        if not self.tool_registry.has_tool("web_acquire") and self.researcher:
            self.tool_registry.register(
                name="web_acquire",
                description="Search external web sources",
                handler=self.researcher.research,
                schema={"type": "object", "properties": {"query": {"type": "string"}}}
            )
            
        self.discovery_agent = DiscoveryAgent(self.ai_provider, self.tool_registry)
        self.intelligence_agent = IntelligenceAgent(self.intelligence_provider)

    async def process(self, product_input: ProductInput, previous_result: Optional[ProductIntelligenceResult] = None) -> PipelineResult:
        """Process a single product through the full pipeline with an adaptive feedback loop."""
        start = time.time()
        request_id = f"req_{uuid.uuid4().hex[:12]}"
        pipeline_result = PipelineResult()
        pipeline_result.diagnostics["request_id"] = request_id
        pipeline_result.diagnostics["provider"] = self.ai_provider.get_provider_name()
        pipeline_result.diagnostics["is_reenrichment"] = previous_result is not None

        trace_ctx = product_input.metadata or {}
        trace_id = trace_ctx.get("trace_id", request_id)
        job_id = trace_ctx.get("job_id")
        product_id = trace_ctx.get("product_id")
        tenant_id = trace_ctx.get("tenant_id")

        await trace_emitter.emit(TraceEvent(
            trace_id=trace_id, request_id=request_id, job_id=job_id, product_id=product_id, tenant_id=tenant_id,
            stage="PIPELINE_START", event_type="STARTED", status="IN_PROGRESS",
            payload={"mfg_part_number": product_input.mfg_part_number, "trace_ctx": trace_ctx}
        ))

        logger.info(f"Pipeline: starting {request_id} for part={product_input.mfg_part_number}")

        try:
            # Step 1: Normalize input
            normalized = self._normalize_input(product_input)
            pipeline_result.diagnostics["step_1_normalize"] = "completed"

            # Step 2: Discovery Agent
            discovery_request = DiscoveryRequest(
                request_id=request_id,
                mfg_part_number=product_input.mfg_part_number,
                part_description=product_input.part_description,
                brand=product_input.brand,
                manufacturer=product_input.manufacturer,
                category=product_input.category,
                industry=product_input.industry,
                extracted_texts=[normalized.text] if normalized.text else [],
                tables=normalized.tables,
            )
            discovery = await self.discovery_agent.discover(discovery_request)
            pipeline_result.discovery_result = discovery
            
            await trace_emitter.emit(TraceEvent(
                trace_id=trace_id, request_id=request_id, job_id=job_id, product_id=product_id, tenant_id=tenant_id,
                stage="DISCOVERY", event_type="AGENT_OUTPUT", component="DiscoveryAgent", status="COMPLETED",
                payload={"known": len(discovery.known_information), "missing": len(discovery.missing_information), "research_required": discovery.research_required}
            ))
            
            pipeline_result.diagnostics["step_2_discovery"] = {
                "known": len(discovery.known_information),
                "missing": len(discovery.missing_information),
                "research_required": discovery.research_required,
            }

            # Step 3: Initial Retrieve evidence
            all_evidence = await self._retrieve_evidence(discovery)
            
            await trace_emitter.emit(TraceEvent(
                trace_id=trace_id, request_id=request_id, job_id=job_id, product_id=product_id, tenant_id=tenant_id,
                stage="RETRIEVAL", event_type="EVIDENCE_GATHERED", component="Retriever", status="COMPLETED",
                payload={"sources_count": all_evidence.total_sources, "avg_score": all_evidence.average_score}
            ))
            
            pipeline_result.diagnostics["step_3_retrieval"] = {
                "sources": all_evidence.total_sources,
                "avg_score": round(all_evidence.average_score, 3),
                "has_manufacturer": all_evidence.has_manufacturer_source,
            }
            
            # --- ADAPTIVE FEEDBACK LOOP ---
            MAX_ITERATIONS = 3
            iteration = 0
            final_decision_struct = None
            
            while iteration < MAX_ITERATIONS:
                iteration += 1
                logger.info(f"Pipeline: Knowledge Decision Loop iteration {iteration}/{MAX_ITERATIONS}")
                
                # Evaluate current evidence
                decision_struct = self.knowledge_decision.evaluate(discovery, all_evidence)
                final_decision_struct = decision_struct
                sufficiency = decision_struct.decision
                
                pipeline_result.evidence_sufficiency = sufficiency
                pipeline_result.diagnostics[f"loop_{iteration}_decision"] = sufficiency.value
                pipeline_result.diagnostics[f"loop_{iteration}_coverage"] = decision_struct.evidence_coverage
                
                if sufficiency == EvidenceSufficiency.SUFFICIENT:
                    logger.info("Pipeline: Evidence is SUFFICIENT. Breaking loop.")
                    break
                    
                # If we need more info, perform targeted research
                logger.info(f"Pipeline: Evidence is {sufficiency.value}. Attempting targeted research.")
                research_result = await self._perform_research(discovery, decision_struct)
                
                if research_result:
                    if getattr(research_result, "error", "") == "RESEARCH_PROVIDER_UNAVAILABLE":
                        pipeline_result.diagnostics["research_status"] = "RESEARCH_PROVIDER_UNAVAILABLE"
                        logger.info("Pipeline: Research provider unavailable. Breaking loop.")
                        break
                        
                    research_evidence = research_result.evidence_set
                    if research_evidence and research_evidence.evidence:
                        # Deduplicate and add
                        existing_ids = {e.evidence_id for e in all_evidence.evidence}
                        new_ev = [e for e in research_evidence.evidence if e.evidence_id not in existing_ids]
                        
                        if not new_ev:
                            logger.info("Pipeline: Research yielded no novel evidence. Breaking loop.")
                            break
                            
                        all_evidence.evidence.extend(new_ev)
                        all_evidence.compute_metrics()
                        pipeline_result.research_performed = True
                    else:
                        logger.info("Pipeline: Research yielded no results. Breaking loop.")
                        break
                else:
                    logger.info("Pipeline: Research failed. Breaking loop.")
                    break
                    
            if iteration == MAX_ITERATIONS and final_decision_struct and final_decision_struct.decision != EvidenceSufficiency.SUFFICIENT:
                logger.warning(f"Pipeline: Max iterations ({MAX_ITERATIONS}) reached. Proceeding with best-effort intelligence.")
            
            pipeline_result.diagnostics["adaptive_iterations"] = iteration
            pipeline_result.all_evidence = all_evidence
            # ------------------------------

            # ------------------------------
            # Qwen Router: Evaluate if Agent 2 is required
            # ------------------------------
            is_agent2_required, router_decision = await self._evaluate_agent2_requirement(
                discovery=discovery, 
                evidence=all_evidence,
                request_id=request_id
            )
            
            pipeline_result.diagnostics["agent2_required"] = is_agent2_required
            
            if is_agent2_required:
                logger.info(f"Pipeline: Routing to Agent 2. Reason: {router_decision.get('reason')}")
                
                await trace_emitter.emit(TraceEvent(
                    trace_id=trace_id, request_id=request_id, job_id=job_id, product_id=product_id, tenant_id=tenant_id,
                    stage="ROUTING", event_type="ROUTING_DECISION", component="QwenRouter", status="COMPLETED",
                    payload={"agent2_required": True, "reason": router_decision.get("reason"), "task": router_decision.get("task")}
                ))
                
                # Optional: log or pass the 'task' to intelligence_agent if supported in future
                
                # Step 6: Intelligence Agent (Agent 2)
                intelligence = await self.intelligence_agent.enrich(
                    product_input=product_input,
                    discovery=discovery,
                    evidence=all_evidence,
                    request_id=request_id,
                    agent2_task=router_decision.get("task"),
                )
                
                await trace_emitter.emit(TraceEvent(
                    trace_id=trace_id, request_id=request_id, job_id=job_id, product_id=product_id, tenant_id=tenant_id,
                    stage="ENRICHMENT", event_type="AGENT_OUTPUT", component="IntelligenceAgent", status="COMPLETED",
                    payload={"fields_populated": intelligence.fields_populated, "fields_missing": intelligence.fields_missing}
                ))
            else:
                logger.info(f"Pipeline: Agent 2 not required. Building baseline intelligence. Reason: {router_decision.get('reason')}")
                intelligence = self._build_baseline_intelligence(
                    product_input=product_input,
                    discovery=discovery,
                    evidence=all_evidence,
                    request_id=request_id,
                )
            
            # Handle re-enrichment versioning
            if previous_result:
                intelligence.enrichment_version = previous_result.enrichment_version + 1
                intelligence.previous_result_id = previous_result.request_id
                
            pipeline_result.diagnostics["step_6_enrichment"] = {
                "status": intelligence.processing_status.value,
                "fields_total": intelligence.fields_total,
                "fields_populated": intelligence.fields_populated,
                "via_agent2": is_agent2_required,
            }

            # Step 7: Normalize values
            intelligence.attributes = self.normalization_engine.normalize_product(intelligence.attributes)
            pipeline_result.diagnostics["step_7_normalization"] = "completed"

            # Step 8: Validate
            validation = self.validation_engine.validate(intelligence)
            pipeline_result.validation_result = validation
            pipeline_result.diagnostics["step_8_validation"] = {
                "passed": validation.passed,
                "checks": validation.total_checks,
                "failures": validation.failed_checks,
                "warnings": validation.warning_checks,
            }

            # Step 9: Confidence
            self.confidence_engine.calculate_product_confidence(intelligence, all_evidence)
            pipeline_result.diagnostics["step_9_confidence"] = {
                "overall": round(intelligence.overall_confidence, 4),
            }

            # Step 10: Commerce output
            commerce_data = self.commerce_adapter.adapt(intelligence)
            commerce_json = self.commerce_adapter.to_json(intelligence)

            pipeline_result.intelligence = intelligence
            pipeline_result.commerce_data = commerce_data
            pipeline_result.commerce_json = commerce_json
            pipeline_result.diagnostics["step_10_output"] = "completed"
            
            await trace_emitter.emit(TraceEvent(
                trace_id=trace_id, request_id=request_id, job_id=job_id, product_id=product_id, tenant_id=tenant_id,
                stage="PIPELINE_END", event_type="COMPLETED", status="COMPLETED",
                payload={"success": True}
            ))

        except Exception as e:
            error_msg = str(e)
            if type(e).__name__ == "RetryError" and hasattr(e, "last_attempt"):
                try:
                    inner = e.last_attempt.exception()
                    if inner:
                        error_msg = str(inner)
                except Exception:
                    pass

            logger.error(f"Pipeline: failed — {error_msg}", exc_info=True)
            
            await trace_emitter.emit(TraceEvent(
                trace_id=trace_id, request_id=request_id, job_id=job_id, product_id=product_id, tenant_id=tenant_id,
                stage="PIPELINE_END", event_type="FAILED", status="FAILED",
                payload={"error": error_msg, "error_type": type(e).__name__}
            ))
            pipeline_result.errors.append(ProcessingError(
                stage="pipeline",
                error_type=type(e).__name__,
                message=error_msg,
            ))

        pipeline_result.processing_time_ms = (time.time() - start) * 1000
        pipeline_result.diagnostics["processing_time_ms"] = round(pipeline_result.processing_time_ms, 1)
        logger.info(
            f"Pipeline: finished {request_id} in {pipeline_result.processing_time_ms:.0f}ms "
            f"success={pipeline_result.success}"
        )
        return pipeline_result

    async def process_batch(
        self,
        products: list[ProductInput],
        max_failures: int = -1,
    ) -> list[PipelineResult]:
        """Process multiple products. One failure does not destroy the batch."""
        results = []
        failures = 0
        for i, product in enumerate(products):
            logger.info(f"Pipeline batch: processing {i + 1}/{len(products)}")
            try:
                result = await self.process(product)
                results.append(result)
                if not result.success:
                    failures += 1
            except Exception as e:
                logger.error(f"Pipeline batch: product {i + 1} failed — {e}")
                fail_result = PipelineResult()
                fail_result.errors.append(ProcessingError(
                    stage="batch_pipeline",
                    error_type=type(e).__name__,
                    message=str(e),
                ))
                results.append(fail_result)
                failures += 1

            if max_failures >= 0 and failures > max_failures:
                logger.warning(f"Pipeline batch: max failures ({max_failures}) exceeded, stopping")
                break

        return results

    def _normalize_input(self, product_input: ProductInput) -> NormalizedInput:
        """Create a NormalizedInput from raw ProductInput."""
        texts = []
        if product_input.part_description:
            texts.append(product_input.part_description)
        if product_input.additional_text:
            texts.append(product_input.additional_text)
            
        normalized = NormalizedInput(
            product_input=product_input,
            text="\n".join(texts) if texts else None,
        )
        
        # Multimodal connection (Phase O)
        # Check if the backend passed ingestion results via metadata
        if "ingestion_results" in product_input.metadata:
            results = product_input.metadata["ingestion_results"]
            if isinstance(results, list):
                for res in results:
                    text_preview = res.get("extracted_text_preview")
                    if text_preview:
                        normalized.text = f"{normalized.text}\n{text_preview}" if normalized.text else text_preview
                    if res.get("images"):
                        normalized.images.extend(res["images"])
                    if res.get("tables"):
                        normalized.tables.extend(res["tables"])
                    
        return normalized

    async def _retrieve_evidence(self, discovery):
        """Retrieve evidence using all discovery queries."""
        from ai_engine.schemas import EvidenceSet
        all_evidence = EvidenceSet()

        for action in discovery.actions:
            tool_name = action.get("action") or action.get("tool")
            if tool_name != "vector_search":
                continue
            
            params = action.get("parameters", {})
            query = params.get("query")
            if not query:
                continue
                
            request = RetrievalRequest(
                query=query,
                product_context={
                    "part_number": discovery.product_identity.part_number,
                    "manufacturer": discovery.product_identity.manufacturer,
                },
                required_attributes=discovery.required_attributes,
            )
            
            response = await self.tool_registry.execute_tool(
                name="vector_search",
                parameters={"request": request}
            )
            if response.evidence_set.evidence:
                all_evidence.evidence.extend(response.evidence_set.evidence)

        # Deduplicate by evidence_id
        seen = set()
        unique = []
        for ev in all_evidence.evidence:
            if ev.evidence_id not in seen:
                seen.add(ev.evidence_id)
                unique.append(ev)
        all_evidence.evidence = unique
        all_evidence.compute_metrics()
        return all_evidence

    async def _perform_research(self, discovery, decision_struct):
        """Perform targeted external research."""
        research_plan = decision_struct.research_plan
        if not research_plan:
            return None

        targets = []
        for plan in research_plan[:3]:  # Bounded research
            targets.append(ResearchTarget(
                query=plan["query"],
                target_attributes=plan.get("target_attributes", []),
                priority=plan.get("priority", "MEDIUM"),
            ))

        research_request = ResearchRequest(
            request_id=f"research_{uuid.uuid4().hex[:8]}",
            product_name=discovery.product_identity.product_name,
            manufacturer=discovery.product_identity.manufacturer,
            part_number=discovery.product_identity.part_number,
            targets=targets,
        )

        try:
            result = await self.tool_registry.execute_tool(
                name="web_acquire",
                parameters={"request": research_request}
            )
            return result
        except Exception as e:
            logger.error(f"Pipeline: research failed — {e}")
            return None

    async def _evaluate_agent2_requirement(self, discovery, evidence, request_id: str) -> tuple[bool, dict[str, Any]]:
        """Qwen Router: evaluate whether Agent 2 is actually required.
        
        Outputs a structured decision:
        {
          "agent2_required": true/false,
          "reason": "...",
          "task": {
            "objective": "...",
            "evidence_ids": []
          }
        }
        """
        logger.info(f"Pipeline: Qwen Router evaluating Agent 2 requirement for {request_id}")
        
        # Build prompt from discovery and evidence
        evidence_summary = [
            f"ID: {e.evidence_id} | Source: {e.source} | Content: {e.content[:100]}..." 
            for e in evidence.evidence
        ]
        
        prompt = f"""Evaluate if deep reasoning (Agent 2) is required.

Known Info:
{discovery.known_information}

Missing Info required:
{discovery.missing_information}

Evidence Gathered:
{evidence_summary}

Decide if the evidence needs complex extraction, conflict resolution, or synthesis (Agent 2 required), or if the known information is already sufficient and evidence is straightforward (Agent 2 NOT required).

Respond with valid JSON matching:
{{
  "agent2_required": true or false,
  "reason": "explanation",
  "task": {{
    "objective": "what Agent 2 should focus on, if required",
    "evidence_ids": ["ids of relevant evidence"]
  }}
}}"""

        try:
            # We use the pipeline's router_provider (which is OllamaProvider in production)
            decision = await self.router_provider.generate_structured(
                prompt=prompt,
                system_instruction="You are a routing layer. Decide if deep reasoning is needed based on evidence.",
                temperature=0.1
            )
            
            # Validate decision
            is_req = bool(decision.get("agent2_required", True))
            return is_req, decision
        except Exception as e:
            logger.error(f"Pipeline: Router evaluation failed: {e}. Defaulting to Agent 2 = True.")
            return True, {"agent2_required": True, "reason": f"Fallback due to error: {str(e)}"}

    def _build_baseline_intelligence(
        self, 
        product_input: ProductInput, 
        discovery, 
        evidence, 
        request_id: str
    ) -> ProductIntelligenceResult:
        """Build baseline intelligence without Agent 2 LLM calls."""
        from ai_engine.schemas import FieldValue, FieldStatus, Provenance
        
        result = ProductIntelligenceResult(
            request_id=request_id,
            product_input=product_input,
            processing_status=ProcessingStatus.COMPLETED,
            identity=discovery.product_identity,
        )
        
        # Map known info from DiscoveryResult
        for info in discovery.known_information:
            field = info.get("field", "")
            value = info.get("value", "")
            if not field or not value:
                continue
                
            fv = FieldValue(
                field_name=field,
                value=str(value),
                display_value=str(value),
                status=FieldStatus.DIRECTLY_SUPPORTED,
                confidence=1.0,
                reason="From normalized input/discovery",
                provenance=Provenance(source_agent="pipeline_baseline")
            )
            
            # Map common fields
            if field == "description" and not result.short_description:
                result.short_description = fv
            elif field == "manufacturer" and not result.identity.manufacturer:
                result.identity.manufacturer = value
            elif field == "part_number" and not result.identity.part_number:
                result.identity.part_number = value
            else:
                result.attributes.append(fv)
                
        # Map required attributes as missing
        for attr in discovery.required_attributes:
            found = any(a.field_name.lower() == attr.lower() for a in result.attributes)
            if not found:
                result.attributes.append(FieldValue(
                    field_name=attr,
                    status=FieldStatus.MISSING,
                    confidence=0.0,
                    reason="Not found in baseline",
                    provenance=Provenance(source_agent="pipeline_baseline")
                ))
                
        # Compute metrics
        all_fields = [result.short_description] + result.attributes
        total, populated = 0, 0
        for fv in all_fields:
            if fv:
                total += 1
                if fv.status == FieldStatus.DIRECTLY_SUPPORTED:
                    populated += 1
                    
        result.fields_total = total
        result.fields_populated = populated
        result.fields_missing = total - populated
        result.completeness_ratio = populated / total if total > 0 else 0.0
        
        return result
