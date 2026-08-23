"""Discovery Agent (Agent 1) — identifies product, analyzes gaps, generates research plans."""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Optional

from ai_engine.providers.ai_provider import AIProviderInterface
from ai_engine.schemas import (
    DiscoveryRequest,
    DiscoveryResult,
    EvidenceSufficiency,
    KnowledgeRequirement,
    ProductIdentity,
)
from ai_engine.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

# Commerce-critical attributes that should always be sought
CORE_COMMERCE_ATTRIBUTES = [
    "Product Name", "Series", "Model", "Voltage Rating", "Amperage Rating",
    "Mounting Type", "Size", "Material", "Color", "Weight",
    "Standards/Approvals", "Warranty",
]


class DiscoveryAgent:
    """Agent 1: Understands the product, identifies what is known/missing,
    generates targeted retrieval and research queries.

    NEVER fabricates specifications.
    """

    def __init__(self, ai_provider: AIProviderInterface, tool_registry: Optional[ToolRegistry] = None):
        self._ai = ai_provider
        self._tool_registry = tool_registry or ToolRegistry()

    async def discover(self, request: DiscoveryRequest) -> DiscoveryResult:
        """Run the full discovery process."""
        logger.info(f"DiscoveryAgent: starting discovery for {request.request_id}")

        # Build product context for AI
        product_info = self._build_product_info(request)

        # Ask AI to analyze the product
        ai_result = await self._ai.analyze_product(
            product_info=product_info,
            task="discover_and_identify",
            context=self._build_discovery_prompt(),
        )

        # Parse AI response into structured result
        result = self._parse_discovery_result(request.request_id, ai_result, request)
        logger.info(
            f"DiscoveryAgent: completed. Known={len(result.known_information)}, "
            f"Missing={len(result.missing_information)}, "
            f"Research={'YES' if result.research_required else 'NO'}"
        )
        return result

    def _build_product_info(self, request: DiscoveryRequest) -> dict[str, Any]:
        """Assemble the product information dict for AI analysis."""
        info: dict[str, Any] = {}
        if request.mfg_part_number:
            info["mfg_part_number"] = request.mfg_part_number
        if request.part_description:
            info["part_description"] = request.part_description
        if request.brand:
            info["brand"] = request.brand
        if request.manufacturer:
            info["manufacturer"] = request.manufacturer
        if request.category:
            info["category"] = request.category
        if request.industry:
            info["industry"] = request.industry
        if request.extracted_texts:
            info["extracted_texts"] = request.extracted_texts[:3]  # Context control
        if request.tables:
            info["tables"] = request.tables[:2]
        return info

    @staticmethod
    def _build_discovery_prompt() -> str:
        return """Analyze this product and provide:

1. Product Identity: manufacturer, brand, part_number, product_name, category, industry, confidence (0-1)
2. Known Information: list of {field, value} pairs that are explicitly present
3. Missing Information: list of important missing attributes
4. Required Attributes: commerce-critical attributes to seek
5. Evidence Requirements: list of {attribute, importance, reason}
6. Retrieval Queries: specific queries to search internal knowledge base
7. External Search Queries: specific queries for external research
8. Research Required: true/false
9. Actions: A list of objects representing tools to execute: {"tool": "vector_search", "parameters": {"query": "..."}} or {"tool": "web_acquire", "parameters": {"query": "..."}}

CRITICAL RULES:
- Do NOT fabricate specifications
- Only report what is explicitly present in the input
- Be specific about what is missing
- Generate TARGETED search queries, not generic ones
- Identify the most likely product category and industry

Return as JSON with these exact keys: product_identity, known_information,
missing_information, required_attributes, evidence_requirements,
retrieval_queries, external_search_queries, research_required, industry, category, actions"""

    def _parse_discovery_result(
        self,
        request_id: str,
        ai_result: dict[str, Any],
        request: DiscoveryRequest,
    ) -> DiscoveryResult:
        """Convert AI response to typed DiscoveryResult."""
        # Parse product identity
        identity_data = ai_result.get("product_identity", {})
        identity = ProductIdentity(
            manufacturer=identity_data.get("manufacturer", request.manufacturer),
            brand=identity_data.get("brand", request.brand),
            part_number=identity_data.get("part_number", request.mfg_part_number),
            product_name=identity_data.get("product_name"),
            category=identity_data.get("category"),
            industry=identity_data.get("industry"),
            confidence=float(identity_data.get("confidence", 0.5)),
        )

        # Parse evidence requirements
        evidence_reqs = []
        for req in ai_result.get("evidence_requirements", []):
            if isinstance(req, dict):
                evidence_reqs.append(KnowledgeRequirement(
                    attribute=req.get("attribute", "unknown"),
                    importance=req.get("importance", "MEDIUM"),
                    reason=req.get("reason", ""),
                ))

        # Determine sufficiency
        missing = ai_result.get("missing_information", [])
        research_required = ai_result.get("research_required", True)
        if not missing:
            sufficiency = EvidenceSufficiency.SUFFICIENT
        elif research_required:
            sufficiency = EvidenceSufficiency.RESEARCH_REQUIRED
        else:
            sufficiency = EvidenceSufficiency.INSUFFICIENT

        # Normalize required_attributes to list of strings
        raw_req_attrs = ai_result.get("required_attributes", CORE_COMMERCE_ATTRIBUTES)
        normalized_req_attrs = []
        if isinstance(raw_req_attrs, list):
            for attr in raw_req_attrs:
                if isinstance(attr, dict):
                    # Handle hallucinated dicts e.g. {"attribute": "power_rating", "reason": "..."}
                    if "attribute" in attr:
                        normalized_req_attrs.append(str(attr["attribute"]))
                    elif "name" in attr:
                        normalized_req_attrs.append(str(attr["name"]))
                elif isinstance(attr, str):
                    normalized_req_attrs.append(attr)

        if not normalized_req_attrs:
            normalized_req_attrs = CORE_COMMERCE_ATTRIBUTES

        return DiscoveryResult(
            request_id=request_id,
            product_identity=identity,
            industry=ai_result.get("industry", identity.industry),
            category=ai_result.get("category", identity.category),
            known_information=ai_result.get("known_information", []),
            missing_information=missing,
            required_attributes=normalized_req_attrs,
            evidence_requirements=evidence_reqs,
            retrieval_queries=ai_result.get("retrieval_queries", []),
            external_search_queries=ai_result.get("external_search_queries", []),
            actions=ai_result.get("actions", []),
            research_required=research_required,
            initial_sufficiency=sufficiency,
            raw_ai_response=json.dumps(ai_result, default=str)[:2000],
        )


