import os
from backend.ingestion.text_processor import TextProcessor
from backend.ingestion.document_processor import DocumentProcessor
from backend.retrieval.chunker import chunker

def test_text_processor(tmp_path):
    sample_file = tmp_path / "sample_datasheet.txt"
    sample_file.write_text("SKF 6205-2RS1 Deep Groove Ball Bearing. Bore 25 mm, OD 52 mm, Width 15 mm.")

    processor = TextProcessor()
    processed = processor.process(str(sample_file), source_id="src_test_01")

    assert processed.source_id == "src_test_01"
    assert "Bore 25 mm" in processed.extracted_text
    assert processed.metadata["file_size"] > 0

    chunks = chunker.chunk_source(processed)
    assert len(chunks) >= 1
    assert chunks[0]["source_id"] == "src_test_01"

def test_document_processor_csv(tmp_path):
    sample_csv = tmp_path / "products.csv"
    sample_csv.write_text("SKU,Name,Brand\n6205-2RS1,Deep Groove Bearing,SKF\n6206-ZZ,Ball Bearing,NSK\n")

    processor = DocumentProcessor()
    processed = processor.process(str(sample_csv), source_id="src_csv_01")

    assert processed.source_type == "csv"
    assert len(processed.tables) >= 1
    assert "6205-2RS1" in processed.extracted_text
