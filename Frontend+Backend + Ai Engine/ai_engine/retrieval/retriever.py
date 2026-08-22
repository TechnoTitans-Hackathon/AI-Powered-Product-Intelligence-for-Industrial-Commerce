"""Retriever interface."""

from __future__ import annotations

import logging
import time
import uuid
from abc import ABC, abstractmethod
from typing import Any

from ai_engine.schemas import (
    Evidence,
    EvidenceSet,
    RetrievalRequest,
    RetrievalResponse,
    SourceType,
)

logger = logging.getLogger(__name__)


class RetrieverInterface(ABC):
    """Abstract retrieval interface.

    The real RAG system will implement this.
    """

    @abstractmethod
    async def retrieve(
        self,
        request: RetrievalRequest,
    ) -> RetrievalResponse:
        """Retrieve evidence matching the request."""
        ...
