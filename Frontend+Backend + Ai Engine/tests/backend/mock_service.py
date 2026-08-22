import uuid
from backend.ai_interface.interface import AIService
from backend.schemas.ai_contract import AIServiceRequest, AIServiceResponse, AIAttributeItem
from backend.schemas.retrieval import EvidenceSchema
from backend.core.logging import logger

# ---------------------------------------------------------------------------
# Per-category mock fixture definitions (DEMO/TEST DATA ONLY)
# These are explicitly labelled mock fixtures. They are NEVER used as
# universal fallbacks. If the input category is not recognised, the mock
# service returns the product's own input data with a "mock": true marker
# and does NOT fabricate attributes.
# ---------------------------------------------------------------------------

MOCK_FIXTURES = {
    "bearings": {
        "subcategory": "Deep Groove Ball Bearings",
        "industry": "Industrial Equipment",
        "attributes": [
            AIAttributeItem(key="Bore Diameter (d)", value="25 mm", normalized_value="25", unit="mm",
                            attribute_type="dimension", confidence=98.0,
                            source_snippet="Page 2: Dimensional Data: Bore 25 mm",
                            source_location="Page 2",
                            explanation="[MOCK] Extracted from demo bearing datasheet fixture."),
            AIAttributeItem(key="Outside Diameter (D)", value="52 mm", normalized_value="52", unit="mm",
                            attribute_type="dimension", confidence=98.0,
                            source_snippet="Outer Diameter 52 mm", source_location="Page 2",
                            explanation="[MOCK] Demo fixture data."),
            AIAttributeItem(key="Width (B)", value="15 mm", normalized_value="15", unit="mm",
                            attribute_type="dimension", confidence=98.0,
                            source_snippet="Width 15 mm", source_location="Page 2",
                            explanation="[MOCK] Demo fixture data."),
            AIAttributeItem(key="Sealing Type", value="2RS1", normalized_value="2RS1", unit=None,
                            attribute_type="technical_spec", confidence=95.0,
                            source_snippet="Sealing: Contact seal on both sides",
                            source_location="Page 1",
                            explanation="[MOCK] Demo fixture data."),
        ],
        "evidence_content": "Demo bearing spec sheet. Bore: 25mm, OD: 52mm, Width: 15mm.",
    },
    "motors": {
        "subcategory": "AC Induction Motors",
        "industry": "Industrial Equipment",
        "attributes": [
            AIAttributeItem(key="Rated Power", value="5.5 kW", normalized_value="5.5", unit="kW",
                            attribute_type="technical_spec", confidence=95.0,
                            source_snippet="Rated Power: 5.5 kW", source_location="Nameplate",
                            explanation="[MOCK] Demo motor fixture data."),
            AIAttributeItem(key="Rated Voltage", value="400 V", normalized_value="400", unit="V",
                            attribute_type="technical_spec", confidence=96.0,
                            source_snippet="Voltage: 400V 3-phase", source_location="Nameplate",
                            explanation="[MOCK] Demo motor fixture data."),
            AIAttributeItem(key="Speed", value="1450 rpm", normalized_value="1450", unit="rpm",
                            attribute_type="technical_spec", confidence=94.0,
                            source_snippet="Speed 1450 rpm", source_location="Datasheet",
                            explanation="[MOCK] Demo motor fixture data."),
            AIAttributeItem(key="Enclosure", value="TEFC", normalized_value="TEFC", unit=None,
                            attribute_type="technical_spec", confidence=97.0,
                            source_snippet="Enclosure: Totally Enclosed Fan Cooled",
                            source_location="Datasheet",
                            explanation="[MOCK] Demo motor fixture data."),
        ],
        "evidence_content": "Demo motor spec. 5.5 kW, 400V, 1450 rpm, TEFC.",
    },
    "pumps": {
        "subcategory": "Centrifugal Pumps",
        "industry": "Industrial Equipment",
        "attributes": [
            AIAttributeItem(key="Flow Rate", value="50 m³/h", normalized_value="50", unit="m³/h",
                            attribute_type="technical_spec", confidence=93.0,
                            source_snippet="Max Flow Rate: 50 m³/h", source_location="Datasheet",
                            explanation="[MOCK] Demo pump fixture data."),
            AIAttributeItem(key="Head", value="30 m", normalized_value="30", unit="m",
                            attribute_type="dimension", confidence=94.0,
                            source_snippet="Total Head: 30 m", source_location="Datasheet",
                            explanation="[MOCK] Demo pump fixture data."),
            AIAttributeItem(key="Impeller Diameter", value="200 mm", normalized_value="200", unit="mm",
                            attribute_type="dimension", confidence=95.0,
                            source_snippet="Impeller Diameter: 200 mm", source_location="Drawing",
                            explanation="[MOCK] Demo pump fixture data."),
        ],
        "evidence_content": "Demo pump spec. 50 m³/h, 30 m head, 200 mm impeller.",
    },
    "valves": {
        "subcategory": "Control Valves",
        "industry": "Process Industries",
        "attributes": [
            AIAttributeItem(key="Nominal Size", value="DN50", normalized_value="50", unit="mm",
                            attribute_type="dimension", confidence=96.0,
                            source_snippet="Nominal Size: DN50", source_location="Datasheet",
                            explanation="[MOCK] Demo valve fixture data."),
            AIAttributeItem(key="Pressure Rating", value="PN16", normalized_value="16", unit="bar",
                            attribute_type="technical_spec", confidence=95.0,
                            source_snippet="Pressure Rating: PN16", source_location="Datasheet",
                            explanation="[MOCK] Demo valve fixture data."),
            AIAttributeItem(key="Body Material", value="Carbon Steel", normalized_value="Carbon Steel",
                            unit=None, attribute_type="technical_spec", confidence=94.0,
                            source_snippet="Body Material: ASTM A216 WCB", source_location="Drawing",
                            explanation="[MOCK] Demo valve fixture data."),
        ],
        "evidence_content": "Demo valve spec. DN50, PN16, Carbon Steel.",
    },
    "sensors": {
        "subcategory": "Temperature Sensors",
        "industry": "Industrial Automation",
        "attributes": [
            AIAttributeItem(key="Measurement Range", value="-40 to 150 °C", normalized_value="-40..150",
                            unit="°C", attribute_type="technical_spec", confidence=96.0,
                            source_snippet="Range: -40 to 150 °C", source_location="Datasheet",
                            explanation="[MOCK] Demo sensor fixture data."),
            AIAttributeItem(key="Accuracy", value="±0.5 °C", normalized_value="0.5", unit="°C",
                            attribute_type="technical_spec", confidence=95.0,
                            source_snippet="Accuracy: ±0.5 °C", source_location="Datasheet",
                            explanation="[MOCK] Demo sensor fixture data."),
            AIAttributeItem(key="Output", value="4-20 mA", normalized_value="4-20", unit="mA",
                            attribute_type="technical_spec", confidence=97.0,
                            source_snippet="Output: 4-20 mA", source_location="Datasheet",
                            explanation="[MOCK] Demo sensor fixture data."),
        ],
        "evidence_content": "Demo sensor spec. -40 to 150 °C, ±0.5 °C, 4-20 mA output.",
    },
}


class MockAIService(AIService):
    """
    Mock AI Service implementation.
    Simulates Aman's AI Engine during backend development and automated testing.

    RULES:
    1. If input provides a category that matches a fixture, use that fixture's DEMO data.
    2. If input provides no recognisable category, return the product's own input data
       with a "mock": true marker. Never fabricate attributes for unknown products.
    3. All mock data is explicitly marked with [MOCK] in explanations.
    4. This service NEVER invents product names, brands, SKUs, or specifications
       that are not present in either the input or the designated fixture.
    """

    def process_product(self, request: AIServiceRequest) -> AIServiceResponse:
        inp = request.product_input
        prod_name = inp.get("name", "Unknown Product")
        brand = inp.get("brand") or inp.get("manufacturer") or ""
        sku = inp.get("sku") or ""
        category = inp.get("category") or ""
        subcategory = inp.get("subcategory") or ""
        industry = inp.get("industry") or ""
        description = inp.get("description") or ""
        manufacturer = inp.get("manufacturer") or brand

        logger.info(f"MockAIService processing product input: {prod_name} (category={category})")

        # Try to match a fixture by normalised category name
        fixture_key = category.strip().lower().rstrip("s")  # "Bearings" -> "bearing"
        # Also try plural
        fixture = MOCK_FIXTURES.get(fixture_key) or MOCK_FIXTURES.get(category.strip().lower())

        if fixture:
            attributes = fixture["attributes"]
            fixture_subcategory = fixture["subcategory"]
            fixture_industry = fixture["industry"]
            evidence_content = fixture["evidence_content"]
        else:
            # Unknown / unrecognised category — return input data as-is, NO fabrication
            attributes = []
            fixture_subcategory = subcategory
            fixture_industry = industry
            evidence_content = f"[MOCK] No fixture data available for category '{category}'. Product accepted without fabricated attributes."

        # Use request evidence if present, otherwise build a mock evidence item
        evidence_list = request.retrieved_evidence
        if not evidence_list:
            evidence_list = [
                EvidenceSchema(
                    evidence_id=f"ev_mock_{uuid.uuid4().hex[:8]}",
                    source_id="src_mock_001",
                    source=f"{brand} Technical Catalog" if brand else "Mock Catalog",
                    document=f"mock_datasheet.pdf",
                    url="",
                    page=1,
                    content=evidence_content,
                    score=0.90 if fixture else 0.50,
                    metadata={"category": category, "brand": brand, "mock": True},
                    provenance={"extracted_by": "MockAIService", "mock": True}
                )
            ]

        return AIServiceResponse(
            product={
                "name": prod_name,
                "sku": sku,
                "brand": brand,
                "manufacturer": manufacturer,
                "category": category or "Uncategorized",
                "subcategory": subcategory or fixture_subcategory,
                "industry": industry or fixture_industry,
                "description": description or f"Product: {prod_name}",
                "completenessScore": 85.0 if fixture else 30.0,
                "confidenceScore": 90.0 if fixture else 20.0,
                "status": "mock_processed",
                "review_status": "PENDING"
            },
            attributes=attributes,
            descriptions={
                "short": f"{brand} {sku} {prod_name}".strip() if brand else prod_name,
                "full": description or f"Product: {prod_name}"
            },
            confidence={
                "overall": 90.0 if fixture else 20.0,
                "source_quality": 85.0 if fixture else 10.0,
                "evidence_coverage": 90.0 if fixture else 0.0,
                "cross_source_agreement": 90.0 if fixture else 0.0,
                "validation_score": 95.0 if fixture else 50.0
            },
            sources=[{
                "id": "src_mock_001",
                "name": f"{brand} Technical Catalog" if brand else "Mock Source",
                "type": "mock",
                "url": ""
            }],
            evidence=evidence_list,
            explanation={
                "summary": f"[MOCK] Product processed via MockAIService fixture for category '{category}'."
                           if fixture else
                           f"[MOCK] No fixture matched for category '{category}'. No attributes fabricated."
            },
            validation_hints=["[MOCK] Data from mock service — not real AI extraction."],
            review_required=True
        )

mock_ai_service = MockAIService()
