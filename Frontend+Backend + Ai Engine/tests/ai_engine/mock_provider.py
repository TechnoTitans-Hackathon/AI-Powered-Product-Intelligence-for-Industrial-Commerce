from typing import Any, Dict, List
from ai_engine.providers.ai_provider import AIProviderInterface
from ai_engine.schemas import FieldValue, FieldStatus

class MockProvider(AIProviderInterface):
    def __init__(self, **kwargs):
        pass

    def get_provider_name(self) -> str:
        return "MockProvider"
        
    async def analyze_product(self, product_info: Dict[str, Any], task: str, context: str = "") -> Dict[str, Any]:
        part_number = product_info.get("mfg_part_number", product_info.get("part_number", "TEST-001"))
        manufacturer = product_info.get("manufacturer", "TestCorp")
        part_description = product_info.get("part_description", "Test Product")
        
        queries = [part_description]
        if part_number == "DCB518ASTS06G":
            queries.append("sanding")

        return {
            "product_identity": {"part_number": part_number, "manufacturer": manufacturer},
            "known_information": [],
            "missing_information": ["Missing detail 1"],
            "required_attributes": ["Weight", "Material", "Tensile Strength", "Operating Altitude"],
            "retrieval_queries": queries,
            "actions": [{"action": "vector_search", "parameters": {"query": q}} for q in queries],
            "evidence_requirements": [{"attribute": "Weight", "importance": "HIGH", "reason": "Missing"}],
            "raw_ai_response": "AGENT_1_TEST_RESPONSE"
        }
        
    async def analyze_multimodal(self, prompt: str, image_paths: list[str] = None, audio_paths: list[str] = None, video_paths: list[str] = None, system_instruction: str = "", response_schema: Any = None, temperature: float = 0.2) -> Dict[str, Any]:
        return {"mock": True, "multimodal_response": "mock_response"}
        
    async def extract_attributes(self, product_info: Dict[str, Any], evidence_texts: List[str], required_attributes: List[str]) -> List[Dict[str, Any]]:
        status = "DIRECTLY_SUPPORTED" if evidence_texts else "MISSING"
        return [
            {
                "attribute": attr,
                "value": "mock_value" if status != "MISSING" else None,
                "unit": None,
                "status": status,
                "evidence_snippet": "mock snippet" if status != "MISSING" else None,
                "source": "Mock Source" if status != "MISSING" else None,
                "confidence": 0.9 if status != "MISSING" else 0.0
            }
            for attr in required_attributes
        ]
        
    async def evaluate_confidence(self, field: FieldValue, evidence_texts: List[str]) -> Dict[str, Any]:
        return {"confidence_score": 0.9, "reasoning": "Mock"}
        
    async def validate_output(self, intelligence: Any, rules: str = "") -> Dict[str, Any]:
        return {"is_valid": True, "failures": []}

    async def generate_structured(self, prompt: str, system_instruction: str = "", **kwargs) -> Dict[str, Any]:
        return {"agent2_required": True, "reason": "mock reason", "task": {}}
