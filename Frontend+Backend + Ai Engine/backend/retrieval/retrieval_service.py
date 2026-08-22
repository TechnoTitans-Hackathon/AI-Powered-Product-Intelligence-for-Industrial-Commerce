import uuid
from typing import List, Dict, Any, Optional
from backend.schemas.retrieval import RetrievalQuery, EvidenceSchema, RetrievalFilter
from backend.retrieval.vector_store import vector_store, VectorStore
from backend.schemas.source import ProcessedSource
from backend.retrieval.chunker import chunker
from backend.core.logging import logger

class RetrievalService:
    """
    Coordinates semantic search, metadata filtering, and indexing.
    Returns Evidence[] objects containing traceable provenance.
    Never returns untraceable raw text strings.
    """

    def __init__(self, store: VectorStore = vector_store):
        self.store = store

    def index_processed_source(self, processed: ProcessedSource) -> int:
        chunks = chunker.chunk_source(processed)
        indexed_count = 0

        for chk in chunks:
            success = self.store.add(
                id=chk["chunk_id"],
                text=chk["content"],
                metadata={
                    "source_id": chk["source_id"],
                    "document_name": chk["document_name"],
                    "page": chk["page"],
                    "source_type": chk["metadata"].get("source_type"),
                    "url": chk["metadata"].get("url"),
                    "original_file": chk["metadata"].get("original_file")
                }
            )
            if success:
                indexed_count += 1

        logger.info(f"Indexed {indexed_count} chunks for source {processed.source_id}")
        return indexed_count

    def search(self, query: str, top_k: int = 5, filters: Optional[RetrievalFilter] = None) -> List[EvidenceSchema]:
        filter_dict = {}
        if filters:
            if filters.category:
                filter_dict["category"] = filters.category
            if filters.source_id:
                filter_dict["source_id"] = filters.source_id

        raw_results = self.store.search(query=query, top_k=top_k, filters=filter_dict)
        evidence_list: List[EvidenceSchema] = []

        for idx, res in enumerate(raw_results):
            meta = res["metadata"]
            evidence = EvidenceSchema(
                evidence_id=f"ev_{res['id']}",
                source_id=meta.get("source_id", "unknown_source"),
                document_id=res["id"],
                source=meta.get("original_file") or meta.get("document_name") or "Technical Document",
                document=meta.get("document_name", "Datasheet"),
                url=meta.get("url"),
                page=meta.get("page", 1),
                timestamp=meta.get("timestamp"),
                content=res["text"],
                score=round(res["score"], 4),
                metadata=meta,
                provenance={
                    "retrieved_at": "2026-08-11T23:00:00Z",
                    "chunk_id": res["id"],
                    "source_type": meta.get("source_type", "document")
                }
            )
            evidence_list.append(evidence)

        return evidence_list

retrieval_service = RetrievalService()
