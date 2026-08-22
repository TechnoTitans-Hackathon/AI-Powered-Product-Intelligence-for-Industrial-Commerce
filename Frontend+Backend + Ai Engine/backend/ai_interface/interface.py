from abc import ABC, abstractmethod
from backend.schemas.ai_contract import AIServiceRequest, AIServiceResponse

class AIService(ABC):
    """
    Abstract Interface for AI Service Integration.
    Defines the strict input/output contract for Aman's AI Engine.
    Backend API routes communicate exclusively with this interface.
    """

    @abstractmethod
    def process_product(self, request: AIServiceRequest) -> AIServiceResponse:
        pass
