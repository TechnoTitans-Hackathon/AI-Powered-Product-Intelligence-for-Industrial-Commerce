"""Research interface."""

from __future__ import annotations

import logging
import time
import uuid
from abc import ABC, abstractmethod

from ai_engine.schemas import (
    Evidence,
    EvidenceSet,
    ResearchRequest,
    ResearchResult,
    ResearchSourceCandidate,
    SourceType,
)

logger = logging.getLogger(__name__)


class ResearchInterface(ABC):
    """Abstract interface for external knowledge acquisition.

    The real web research system will implement this.
    """

    @abstractmethod
    async def research(self, request: ResearchRequest) -> ResearchResult:
        """Perform targeted external research."""
        ...
