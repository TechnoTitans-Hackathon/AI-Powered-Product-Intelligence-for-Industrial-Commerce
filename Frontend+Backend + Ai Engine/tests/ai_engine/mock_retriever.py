from ai_engine.retrieval.retriever import RetrieverInterface
from ai_engine.schemas import Evidence, EvidenceSet, RetrievalRequest, RetrievalResponse, SourceType
import time
import uuid
import logging

logger = logging.getLogger(__name__)

class MockRetriever(RetrieverInterface):
    """Mock retriever returning realistic product evidence fixtures."""

    def __init__(self):
        self._fixtures = self._build_fixtures()

    async def retrieve(self, request: RetrievalRequest) -> RetrievalResponse:
        start = time.time()
        logger.info(f"MockRetriever: query='{request.query[:60]}...'")

        query_lower = request.query.lower()
        matched_evidence: list[Evidence] = []

        # Match against fixtures based on keywords
        for keyword, evidence_list in self._fixtures.items():
            if keyword in query_lower:
                for ev in evidence_list:
                    if ev.score >= request.min_score:
                        matched_evidence.append(ev)

        # If no keyword match, return generic evidence
        if not matched_evidence:
            matched_evidence = self._generic_evidence(request.query)

        # Limit results
        matched_evidence = matched_evidence[: request.max_results]

        evidence_set = EvidenceSet(evidence=matched_evidence)
        evidence_set.compute_metrics()

        elapsed = (time.time() - start) * 1000
        return RetrievalResponse(
            evidence_set=evidence_set,
            query_used=request.query,
            retrieval_time_ms=elapsed,
            source_count=len(matched_evidence),
        )

    @staticmethod
    def _build_fixtures() -> dict[str, list[Evidence]]:
        """Build a library of realistic product evidence fixtures."""
        return {
            "sanding": [
                Evidence(
                    evidence_id=f"ev_{uuid.uuid4().hex[:8]}",
                    content="Diablo 1/2\" x 18\" Sanding Belt, 6-pack. Aluminum Oxide grain. 80 Grit. For use with portable belt sanders. Designed for wood, metal, and plastic surfaces.",
                    source="Freud/Diablo Product Catalog 2026",
                    source_type=SourceType.MANUFACTURER_DOCUMENT,
                    page=42,
                    section="Sanding Belts",
                    score=0.92,
                ),
                Evidence(
                    evidence_id=f"ev_{uuid.uuid4().hex[:8]}",
                    content="Product specifications: Belt size 1/2 x 18 inch. Pack quantity: 6. Backing: X-weight cloth. Application: General purpose sanding.",
                    source="Freud Technical Datasheet",
                    source_type=SourceType.MANUFACTURER_DOCUMENT,
                    page=3,
                    section="Specifications",
                    score=0.90,
                ),
            ],
            "cubitron": [
                Evidence(
                    evidence_id=f"ev_{uuid.uuid4().hex[:8]}",
                    content="3M Cubitron II 775L Stikit Film Disc. Precision-shaped grain technology. Available in P80, P120, P150, P180 grits. 5-inch diameter. Film backing for consistent finish. 50 discs per box.",
                    source="3M Industrial Abrasives Catalog",
                    source_type=SourceType.MANUFACTURER_DOCUMENT,
                    page=156,
                    section="Cubitron II Product Line",
                    score=0.95,
                ),
                Evidence(
                    evidence_id=f"ev_{uuid.uuid4().hex[:8]}",
                    content="Cubitron II technology uses precision-shaped triangular ceramic grain that self-sharpens. Cuts faster and lasts longer than conventional abrasives. NSF/ANSI certified for food processing environments.",
                    source="3M Technical Bulletin TB-2024-156",
                    source_type=SourceType.MANUFACTURER_DOCUMENT,
                    page=1,
                    section="Technology Overview",
                    score=0.88,
                ),
            ],
            "planer": [
                Evidence(
                    evidence_id=f"ev_{uuid.uuid4().hex[:8]}",
                    content="Oliver 15\" Benchtop Planer Model 10055.201. Motor: 2.5 HP, Single Phase, 230V. Maximum width: 15 inches. Maximum depth of cut: 1/8 inch. Cutterhead speed: 9000 RPM. Feed rate: 16/30 FPM.",
                    source="Oliver Machinery Product Specification Sheet",
                    source_type=SourceType.MANUFACTURER_DOCUMENT,
                    page=1,
                    section="Specifications",
                    score=0.96,
                ),
                Evidence(
                    evidence_id=f"ev_{uuid.uuid4().hex[:8]}",
                    content="Dimensions: 28\" L x 23\" W x 18\" H. Weight: 110 lbs. Table size: 15\" x 18\". Uses 3 HSS knives. Dust port: 4 inch. UL Listed.",
                    source="Oliver Machinery Product Specification Sheet",
                    source_type=SourceType.MANUFACTURER_DOCUMENT,
                    page=2,
                    section="Physical Specifications",
                    score=0.94,
                ),
            ],
            "dishwasher": [
                Evidence(
                    evidence_id=f"ev_{uuid.uuid4().hex[:8]}",
                    content="FRIGIDAIRE Professional Series PDSH4816AF Dishwasher. CleanBoost technology. 5 wash cycles. 120V, 15A. Leg mounting. 47 dBA sound level. Stainless Steel. ENERGY STAR Certified.",
                    source="Frigidaire Product Specification Sheet",
                    source_type=SourceType.MANUFACTURER_DOCUMENT,
                    page=1,
                    section="Product Overview",
                    score=0.97,
                ),
            ],
            "pump": [
                Evidence(
                    evidence_id=f"ev_{uuid.uuid4().hex[:8]}",
                    content="Industrial Pump ABC-420. Flow rate: 120 L/min. Maximum pressure: 10 bar. Operating temperature: 180°C. Material: Stainless Steel 316L. Seal type: Mechanical seal.",
                    source="Manufacturer Technical Manual",
                    source_type=SourceType.MANUFACTURER_DOCUMENT,
                    page=12,
                    section="Performance Specifications",
                    score=0.96,
                ),
                Evidence(
                    evidence_id=f"ev_{uuid.uuid4().hex[:8]}",
                    content="Motor: 2.2 kW, 3-phase, 50/60 Hz. Weight: 45 kg. Dimensions: 450mm x 320mm x 380mm. Connection: DN50 flanged. Certification: CE, ATEX Zone 2.",
                    source="Manufacturer Technical Manual",
                    source_type=SourceType.MANUFACTURER_DOCUMENT,
                    page=14,
                    section="Physical Specifications",
                    score=0.93,
                ),
                Evidence(
                    evidence_id=f"ev_{uuid.uuid4().hex[:8]}",
                    content="Motor power: 1.8 kW. Operating temperature: 160°C max. For chemical processing applications.",
                    source="Legacy Distributor Catalog Q2-2024",
                    source_type=SourceType.DISTRIBUTOR_DOCUMENT,
                    page=87,
                    section="Pumps",
                    score=0.72,
                    metadata={"note": "Older catalog — potential conflict with manufacturer data"},
                ),
            ],
            "valve": [
                Evidence(
                    evidence_id=f"ev_{uuid.uuid4().hex[:8]}",
                    content="Control Valve CV-240. Type: Globe valve. Size: 2 inch. Pressure class: ANSI 300. Body material: Carbon steel. Trim: Stainless steel 316.",
                    source="Northline Systems Product Datasheet",
                    source_type=SourceType.MANUFACTURER_DOCUMENT,
                    page=5,
                    section="Specifications",
                    score=0.91,
                ),
            ],
        }

    @staticmethod
    def _generic_evidence(query: str) -> list[Evidence]:
        """Generate generic evidence when no fixture matches."""
        return [
            Evidence(
                evidence_id=f"ev_{uuid.uuid4().hex[:8]}",
                content=f"Product information related to: {query}. Limited data available from general industrial catalog.",
                source="General Industrial Products Catalog",
                source_type=SourceType.SECONDARY_SOURCE,
                score=0.55,
                section="General Products",
            ),
        ]