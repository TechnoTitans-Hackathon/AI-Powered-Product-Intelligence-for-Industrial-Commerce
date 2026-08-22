from backend.retrieval.vector_store import InMemoryVectorStore
from backend.retrieval.retrieval_service import RetrievalService
from backend.schemas.source import ProcessedSource

def test_vector_store_and_retrieval():
    vstore = InMemoryVectorStore()
    service = RetrievalService(store=vstore)

    processed = ProcessedSource(
        source_id="src_doc_001",
        original_file="SKF_6205_Datasheet.pdf",
        source_type="pdf",
        extracted_text="SKF 6205-2RS1 Deep Groove Ball Bearing. Bore 25 mm, OD 52 mm, Width 15 mm.",
        metadata={"brand": "SKF", "url": "https://skf.com/6205"}
    )

    indexed = service.index_processed_source(processed)
    assert indexed >= 1

    evidence_results = service.search("Bore 25 mm SKF 6205", top_k=2)
    assert len(evidence_results) >= 1
    ev = evidence_results[0]
    assert ev.source_id == "src_doc_001"
    assert "25 mm" in ev.content
    assert ev.score > 0.0
