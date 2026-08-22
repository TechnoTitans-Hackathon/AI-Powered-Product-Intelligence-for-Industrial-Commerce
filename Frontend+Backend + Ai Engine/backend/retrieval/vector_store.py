from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from backend.schemas.retrieval import EvidenceSchema
from backend.core.logging import logger

class VectorStore(ABC):
    """
    Replaceable Vector Database Abstraction.
    Allows switching between ChromaDB, FAISS, or In-Memory vector indexing
    without altering business logic or API endpoints.
    """

    @abstractmethod
    def add(self, id: str, text: str, metadata: Dict[str, Any], vector: Optional[List[float]] = None) -> bool:
        pass

    @abstractmethod
    def search(self, query: str, top_k: int = 5, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def delete(self, id: str) -> bool:
        pass

    @abstractmethod
    def update(self, id: str, text: str, metadata: Dict[str, Any]) -> bool:
        pass

    @abstractmethod
    def health(self) -> dict:
        pass

class InMemoryVectorStore(VectorStore):
    def __init__(self):
        self._index: List[Dict[str, Any]] = []

    def add(self, id: str, text: str, metadata: Dict[str, Any], vector: Optional[List[float]] = None) -> bool:
        # Check if item exists, update if found
        for idx, item in enumerate(self._index):
            if item["id"] == id:
                self._index[idx] = {"id": id, "text": text, "metadata": metadata}
                return True

        self._index.append({"id": id, "text": text, "metadata": metadata})
        return True

    def search(self, query: str, top_k: int = 5, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        query_terms = [t.lower() for t in query.split() if len(t) > 2]
        results = []

        filters = filters or {}

        for item in self._index:
            meta = item["metadata"]
            # Apply metadata filters
            if "category" in filters and filters["category"] and meta.get("category") != filters["category"]:
                continue
            if "source_id" in filters and filters["source_id"] and meta.get("source_id") != filters["source_id"]:
                continue

            text_lower = item["text"].lower()
            # Simple term overlap scoring
            score = 0.5 # baseline relevance score
            if query.lower() in text_lower:
                score += 0.4
            for term in query_terms:
                if term in text_lower:
                    score += 0.1

            score = min(score, 0.99)
            results.append({
                "id": item["id"],
                "text": item["text"],
                "metadata": item["metadata"],
                "score": score
            })

        # Sort by relevance score descending
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def delete(self, id: str) -> bool:
        initial_len = len(self._index)
        self._index = [item for item in self._index if item["id"] != id]
        return len(self._index) < initial_len

    def update(self, id: str, text: str, metadata: Dict[str, Any]) -> bool:
        return self.add(id, text, metadata)

    def health(self) -> dict:
        return {
            "status": "healthy",
            "provider": "InMemoryVectorStore",
            "indexed_chunks_count": len(self._index)
        }

vector_store = InMemoryVectorStore()
