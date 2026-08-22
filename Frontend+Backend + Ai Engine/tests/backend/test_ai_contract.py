from backend.schemas.ai_contract import AIServiceRequest, AIServiceResponse, DiscoveryContextContract
from tests.backend.mock_service import mock_ai_service
from backend.ai_interface.contracts import contract_validator

def test_ai_engine_contract_serialization():
    req = AIServiceRequest(
        product_input={"name": "6205-2RS1 SKF", "brand": "SKF", "category": "Bearings"},
        discovery=DiscoveryContextContract(product_category="Bearings"),
        retrieved_evidence=[]
    )

    res = mock_ai_service.process_product(req)

    assert res.product["name"] is not None
    assert res.product["brand"] == "SKF"
    assert len(res.attributes) >= 1
    assert "overall" in res.confidence

    res_dict = res.model_dump()
    assert contract_validator.validate_ai_response_contract(res_dict) is True
