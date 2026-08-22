"""Product Intelligence Agent (Agent 2) — enrichment, reasoning, structured output."""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Optional

from ai_engine.providers.ai_provider import AIProviderInterface
from ai_engine.schemas import (
    Conflict,
    ConflictType,
    DiscoveryResult,
    Evidence,
    EvidenceSet,
    EvidenceSnippet,
    FieldStatus,
    FieldValue,
    ProductIdentity,
    ProductInput,
    ProductIntelligenceResult,
    ProcessingStatus,
    Provenance,
    ReviewState,
    SourceType,
)

logger = logging.getLogger(__name__)


class IntelligenceAgent:
    """Agent 2: Produces rich, structured, evidence-grounded product intelligence.

    CRITICAL: Never fills a field merely because the schema contains it.
    If evidence does not support it → MISSING.
    If evidence conflicts → CONFLICTING.
    If inferred → INFERRED.
    If directly supported → DIRECTLY_SUPPORTED.
    """

    def __init__(self, ai_provider: AIProviderInterface):
        self._ai = ai_provider

    async def enrich(
        self,
        product_input: ProductInput,
        discovery: DiscoveryResult,
        evidence: EvidenceSet,
        request_id: str,
        agent2_task: Optional[dict[str, Any]] = None,
    ) -> ProductIntelligenceResult:
        """Run full enrichment pipeline."""
        logger.info(f"IntelligenceAgent: enriching {request_id}")

        result = ProductIntelligenceResult(
            request_id=request_id,
            product_input=product_input,
            processing_status=ProcessingStatus.ENRICHING,
            identity=discovery.product_identity,
        )

        try:
            # Step 1: Ask AI to extract and enrich using evidence
            from ai_engine.schemas.base import EvidenceClass
            
            # Filter evidence if task specifies it
            relevant_evidence = evidence.evidence
            if agent2_task and agent2_task.get("evidence_ids"):
                allowed_ids = set(agent2_task["evidence_ids"])
                relevant_evidence = [e for e in evidence.evidence if e.evidence_id in allowed_ids]
                # Fallback if filter is too strict
                if not relevant_evidence:
                    relevant_evidence = evidence.evidence
                    
            evidence_blocks = [
                f"[{getattr(e, 'evidence_class', EvidenceClass.PROVISIONAL).value} SOURCE] {e.content}"
                for e in relevant_evidence
            ]
            evidence_texts = [e.content for e in relevant_evidence]
            product_info = {
                "mfg_part_number": product_input.mfg_part_number,
                "part_description": product_input.part_description,
                "manufacturer": product_input.manufacturer,
                "brand": product_input.brand,
                "category": discovery.category,
                "industry": discovery.industry,
            }

            ai_enrichment = await self._ai.analyze_product(
                product_info=product_info,
                task="enrich_product_intelligence",
                context=self._build_enrichment_prompt(evidence_blocks, discovery, agent2_task),
            )

            # Step 2: Extract attributes from evidence
            ai_attributes = await self._ai.extract_attributes(
                product_info=product_info,
                evidence_texts=evidence_texts,
                required_attributes=discovery.required_attributes,
            )

            # Step 3: Build structured result
            self._populate_descriptions(result, ai_enrichment, evidence)
            self._populate_features(result, ai_enrichment, evidence)
            self._populate_attributes(result, ai_attributes, evidence)
            self._populate_applications_standards(result, ai_enrichment, evidence)
            self._populate_media_documents(result, ai_enrichment)

            # Step 4: Detect conflicts
            self._detect_conflicts(result, evidence)

            # Step 5: Update metrics
            self._compute_metrics(result)

            result.processing_status = ProcessingStatus.COMPLETED
            logger.info(
                f"IntelligenceAgent: completed. "
                f"Fields={result.fields_total}, Populated={result.fields_populated}, "
                f"Missing={result.fields_missing}, Conflicts={result.fields_conflicting}"
            )
            return result

        except Exception as e:
            logger.error(f"IntelligenceAgent: failed — {e}")
            result.processing_status = ProcessingStatus.FAILED
            result.errors.append({"stage": "intelligence_agent", "error": str(e)})
            return result

    @staticmethod
    def _build_enrichment_prompt(evidence_texts: list[str], discovery: DiscoveryResult, agent2_task: Optional[dict[str, Any]] = None) -> str:
        evidence_block = "\n---\n".join(evidence_texts[:5])
        
        task_objective = ""
        if agent2_task and agent2_task.get("objective"):
            task_objective = f"\nSpecific Synthesis Objective:\n{agent2_task['objective']}\n"
            
        return f"""Enrich this product using ONLY the provided evidence.
{task_objective}
Evidence Sources:
{evidence_block}

Known Information:
{json.dumps(discovery.known_information, default=str)}

Missing Information:
{json.dumps(discovery.missing_information, default=str)}

Generate:
1. short_description: concise product title (under 80 chars)
2. long_description: detailed technical description with specs
3. marketing_description: compelling marketing copy
4. retail_description: customer-facing short description
5. features: list of up to 10 key product features
6. applications: suitable applications
7. standards_approvals: certifications/standards
8. attributes: list of {{label, value, unit}} from evidence
9. warranty: warranty information if available

CRITICAL RULES:
- Use ONLY information from the evidence
- If a field has no evidence, set it to null
- Never invent specifications
- Never fabricate certifications
- Include attribute units where applicable
- Pay attention to whether a source is [VERIFIED SOURCE] or [PROVISIONAL SOURCE]

Return as JSON."""

    def _populate_descriptions(
        self,
        result: ProductIntelligenceResult,
        ai_data: dict[str, Any],
        evidence: EvidenceSet,
    ) -> None:
        """Populate description fields from AI enrichment."""
        desc_fields = {
            "short_description": "short_description",
            "long_description": "long_description",
            "marketing_description": "marketing_description",
            "retail_description": "retail_description",
            "mobile_description": "mobile_description",
            "invoice_description": "invoice_description",
        }

        for field_name, ai_key in desc_fields.items():
            value = ai_data.get(ai_key)
            fv = self._make_field_value(
                field_name=field_name,
                value=value,
                evidence=evidence,
                agent="intelligence_agent",
            )
            setattr(result, field_name, fv)

    def _populate_features(
        self,
        result: ProductIntelligenceResult,
        ai_data: dict[str, Any],
        evidence: EvidenceSet,
    ) -> None:
        """Populate feature fields (up to 20)."""
        features_raw = ai_data.get("features", [])
        if isinstance(features_raw, list):
            for i, feat in enumerate(features_raw[:20]):
                feat_text = feat if isinstance(feat, str) else str(feat)
                fv = self._make_field_value(
                    field_name=f"ITEM_FEATURES_{i + 1}",
                    value=feat_text,
                    evidence=evidence,
                    agent="intelligence_agent",
                )
                result.features.append(fv)

    def _populate_attributes(
        self,
        result: ProductIntelligenceResult,
        ai_attributes: list[dict[str, Any]],
        evidence: EvidenceSet,
    ) -> None:
        """Populate attribute triplets from AI extraction."""
        for attr_data in ai_attributes:
            attr_name = attr_data.get("attribute", attr_data.get("label", "Unknown"))
            attr_value = attr_data.get("value")
            attr_unit = attr_data.get("unit", "")
            attr_status = attr_data.get("status", "MISSING")
            attr_confidence = float(attr_data.get("confidence", 0.0))
            snippet = attr_data.get("evidence_snippet", "")

            # Map status string to enum
            status = self._parse_status(attr_status)

            evidence_snippets = []
            if snippet:
                evidence_snippets.append(EvidenceSnippet(
                    source=attr_data.get("source", "evidence"),
                    snippet=snippet,
                    score=attr_confidence,
                ))

            display = f"{attr_value} {attr_unit}".strip() if attr_value else None

            fv = FieldValue(
                field_name=attr_name,
                value=str(attr_value) if attr_value is not None else None,
                normalized_value=attr_value,
                unit=attr_unit if attr_unit else None,
                display_value=display,
                status=status,
                confidence=attr_confidence,
                evidence=evidence_snippets,
                reason=f"Extracted from evidence" if status == FieldStatus.DIRECTLY_SUPPORTED else
                       f"Inferred from context" if status == FieldStatus.INFERRED else
                       "Not found in evidence",
                provenance=Provenance(
                    source_agent="intelligence_agent",
                    evidence_ids=[s.source for s in evidence_snippets],
                ),
            )
            result.attributes.append(fv)

    def _populate_applications_standards(
        self,
        result: ProductIntelligenceResult,
        ai_data: dict[str, Any],
        evidence: EvidenceSet,
    ) -> None:
        """Populate applications, standards, and related fields."""
        result.applications = self._make_field_value(
            "applications", ai_data.get("applications"), evidence, "intelligence_agent"
        )
        result.standards_approvals = self._make_field_value(
            "standards_approvals", ai_data.get("standards_approvals"), evidence, "intelligence_agent"
        )
        result.warranty = self._make_field_value(
            "warranty", ai_data.get("warranty"), evidence, "intelligence_agent"
        )
        result.with_info = self._make_field_value(
            "with", ai_data.get("with"), evidence, "intelligence_agent"
        )

    def _populate_media_documents(
        self,
        result: ProductIntelligenceResult,
        ai_data: dict[str, Any],
    ) -> None:
        """Populate media and document references."""
        for key in ["images", "product_images"]:
            images = ai_data.get(key, [])
            if isinstance(images, list):
                for img in images:
                    result.images.append(FieldValue(
                        field_name="image",
                        value=str(img),
                        status=FieldStatus.DIRECTLY_SUPPORTED if img else FieldStatus.MISSING,
                        confidence=0.9 if img else 0.0,
                    ))

    def _detect_conflicts(
        self,
        result: ProductIntelligenceResult,
        evidence: EvidenceSet,
    ) -> None:
        """Detect and record conflicts between attribute values from different sources."""
        # Group evidence by topic for conflict detection
        attr_values: dict[str, list[tuple[str, str, SourceType]]] = {}
        for ev in evidence.evidence:
            # Simple keyword-based grouping
            content_lower = ev.content.lower()
            for attr in result.attributes:
                if attr.field_name.lower().replace("_", " ") in content_lower and attr.value:
                    key = attr.field_name
                    if key not in attr_values:
                        attr_values[key] = []
                    attr_values[key].append((attr.value, ev.source, ev.source_type))

        # Check for value mismatches across sources
        for attr_name, values in attr_values.items():
            unique_values = set(v[0] for v in values)
            if len(unique_values) > 1:
                vals = list(values)
                conflict = Conflict(
                    field_name=attr_name,
                    value_a=vals[0][0],
                    source_a=vals[0][1],
                    source_a_type=vals[0][2],
                    value_b=vals[1][0] if len(vals) > 1 else "",
                    source_b=vals[1][1] if len(vals) > 1 else "",
                    source_b_type=vals[1][2] if len(vals) > 1 else SourceType.UNKNOWN_SOURCE,
                    conflict_type=ConflictType.VALUE_MISMATCH,
                    review_required=True,
                    reasoning="Multiple sources provide different values",
                )
                result.conflicts.append(conflict)

                # Mark the attribute as conflicting
                for fv in result.attributes:
                    if fv.field_name == attr_name:
                        fv.status = FieldStatus.CONFLICTING
                        fv.review_state = ReviewState.PENDING_REVIEW
                        fv.conflicts.append(conflict)

    def _compute_metrics(self, result: ProductIntelligenceResult) -> None:
        """Compute overall product metrics."""
        all_fields: list[Optional[FieldValue]] = [
            result.short_description, result.long_description,
            result.marketing_description, result.retail_description,
            result.applications, result.standards_approvals,
            result.warranty,
        ]
        all_fields.extend(result.features)
        all_fields.extend(result.attributes)

        total = 0
        populated = 0
        missing = 0
        conflicting = 0
        needing_review = 0

        for fv in all_fields:
            if fv is None:
                continue
            total += 1
            if fv.value is not None and fv.status != FieldStatus.MISSING:
                populated += 1
            else:
                missing += 1
            if fv.status == FieldStatus.CONFLICTING:
                conflicting += 1
            if fv.review_state == ReviewState.PENDING_REVIEW:
                needing_review += 1

        result.fields_total = total
        result.fields_populated = populated
        result.fields_missing = missing
        result.fields_conflicting = conflicting
        result.fields_needing_review = needing_review
        result.completeness_ratio = populated / total if total > 0 else 0.0

    @staticmethod
    def _make_field_value(
        field_name: str,
        value: Any,
        evidence: EvidenceSet,
        agent: str,
    ) -> FieldValue:
        """Create a FieldValue with appropriate status based on evidence presence."""
        if value is None or (isinstance(value, str) and not value.strip()):
            return FieldValue(
                field_name=field_name,
                status=FieldStatus.MISSING,
                confidence=0.0,
                reason="Not found in evidence",
                provenance=Provenance(source_agent=agent),
            )

        # Find supporting evidence
        snippets = []
        for ev in evidence.evidence:
            if isinstance(value, str) and any(
                word in ev.content.lower()
                for word in value.lower().split()[:3]
                if len(word) > 3
            ):
                snippets.append(EvidenceSnippet(
                    source=ev.source,
                    page=ev.page,
                    snippet=ev.content[:200],
                    source_type=ev.source_type,
                    score=ev.score,
                ))

        status = FieldStatus.DIRECTLY_SUPPORTED if snippets else FieldStatus.INFERRED
        confidence = 0.85 if snippets else 0.55

        return FieldValue(
            field_name=field_name,
            value=str(value),
            display_value=str(value),
            status=status,
            confidence=confidence,
            evidence=snippets[:3],
            reason=(
                f"Supported by {len(snippets)} evidence source(s)"
                if snippets else "Generated by AI without direct evidence match"
            ),
            provenance=Provenance(
                source_agent=agent,
                evidence_ids=[s.source for s in snippets],
            ),
        )

    @staticmethod
    def _parse_status(status_str: str) -> FieldStatus:
        """Parse a status string from AI into FieldStatus enum."""
        mapping = {
            "DIRECTLY_SUPPORTED": FieldStatus.DIRECTLY_SUPPORTED,
            "INFERRED": FieldStatus.INFERRED,
            "MISSING": FieldStatus.MISSING,
            "CONFLICTING": FieldStatus.CONFLICTING,
            "UNKNOWN": FieldStatus.UNKNOWN,
        }
        return mapping.get(status_str.upper(), FieldStatus.UNKNOWN)
