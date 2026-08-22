from typing import Dict, Any
from backend.schemas.ai_contract import DiscoveryContextContract, AIServiceResponse
from backend.core.logging import logger

class ContractValidator:
    """
    Ensures that inputs and outputs sent between Aryan's backend and Aman's AI engine
    strictly adhere to contract schemas without corrupting the database.
    """

    @staticmethod
    def validate_discovery_contract(data: Dict[str, Any]) -> bool:
        try:
            DiscoveryContextContract(**data)
            return True
        except Exception as e:
            logger.error(f"Discovery Context contract validation error: {e}")
            return False

    @staticmethod
    def validate_ai_response_contract(data: Dict[str, Any]) -> bool:
        try:
            AIServiceResponse(**data)
            return True
        except Exception as e:
            logger.error(f"AI Service Response contract validation error: {e}")
            return False

contract_validator = ContractValidator()
