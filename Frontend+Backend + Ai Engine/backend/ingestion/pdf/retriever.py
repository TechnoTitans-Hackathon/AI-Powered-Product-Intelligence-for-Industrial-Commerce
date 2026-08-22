import re
import math
from typing import List, Optional, Dict, Any, Set, Tuple
from backend.ingestion.pdf.schemas import PDFDocumentChunk, ChunkContentType

STOPWORDS: Set[str] = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "in", "on", "at", "to", "for", "from", "up", "of", "with", "by", "about",
    "against", "between", "into", "through", "during", "before", "after",
    "above", "below", "to", "from", "up", "down", "in", "out", "on", "off",
    "over", "under", "again", "further", "then", "once", "here", "there",
    "when", "where", "why", "how", "all", "any", "both", "each", "few",
    "more", "most", "other", "some", "such", "no", "nor", "not", "only",
    "own", "same", "so", "than", "too", "very", "s", "t", "can", "will",
    "just", "don", "should", "now", "d", "ll", "m", "o", "re", "ve", "y",
    "ain", "aren", "couldn", "didn", "doesn", "hadn", "hasn", "haven",
    "isn", "ma", "mightn", "mustn", "needn", "shan", "shouldn", "wasn",
    "weren", "won", "wouldn", "what", "which", "who", "whom", "this",
    "that", "these", "those", "am", "it", "its", "provided", "information",
    "details", "show", "find", "give", "tell", "describe", "summarize",
    "list", "explain", "document", "file", "pdf", "page", "section"
}


class PDFDocumentRetriever:
    """
    Hybrid Retrieval Engine for PDF Chunks.
    """

    def __init__(self, min_relevance_threshold: float = 0.20):
        self._index: Dict[str, List[PDFDocumentChunk]] = {}
        self.min_relevance_threshold = min_relevance_threshold

    def index_document_chunks(self, document_id: str, chunks: List[PDFDocumentChunk]) -> None:
        """Indexes document chunks into retrieval store."""
        self._index[document_id] = list(chunks)

    def retrieve_relevant_chunks(
        self,
        document_id: str,
        query: str,
        page_number: Optional[int] = None,
        section: Optional[str] = None,
        content_types: Optional[List[ChunkContentType]] = None,
        top_k: int = 10,
    ) -> List[PDFDocumentChunk]:
        """
        Retrieves, reranks, and returns top_k relevant chunks matching query.
        """
        all_chunks = self._index.get(document_id, [])
        if not all_chunks:
            return [self._build_fallback_chunk(document_id)]

        candidate_chunks = []
        for chk in all_chunks:
            if page_number is not None and chk.page_number != page_number:
                continue
            if section and chk.section and section.lower() not in chk.section.lower():
                continue
            if content_types and chk.content_type not in content_types:
                continue
            candidate_chunks.append(chk)

        if not candidate_chunks:
            return [self._build_fallback_chunk(document_id)]

        if not query or not query.strip():
            res = list(candidate_chunks[:top_k])
            for c in res:
                c.relevance_score = 1.0
            return res

        query_analysis = self._analyze_query(query)

        scored_candidates: List[Tuple[float, PDFDocumentChunk]] = []
        for chk in candidate_chunks:
            score = self._score_chunk(query_analysis, chk, candidate_chunks)
            if score >= self.min_relevance_threshold:
                chk_copy = chk.model_copy()
                chk_copy.relevance_score = round(score, 3)
                scored_candidates.append((score, chk_copy))

        if not scored_candidates:
            return [self._build_fallback_chunk(document_id)]

        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        top_scored = [chk for _, chk in scored_candidates[:top_k]]
        expanded_chunks = self._expand_neighbor_context(top_scored, all_chunks)
        expanded_chunks.sort(key=lambda c: (c.relevance_score or 0.0), reverse=True)

        return expanded_chunks[:top_k]

    def _analyze_query(self, query: str) -> Dict[str, Any]:
        q_raw = query.strip()
        q_lower = q_raw.lower()

        words = re.findall(r"\b[A-Za-z0-9_\-\./']+\b", q_raw)
        proper_nouns = [w for w in words if (w[0].isupper() or any(c.isdigit() for c in w)) and w.lower() not in STOPWORDS]
        cap_phrases = re.findall(r"\b(?:[A-Z][a-zA-Z0-9_\-\./']*(?:\s+[A-Z][a-zA-Z0-9_\-\./']*)+)\b", q_raw)
        key_terms = [w.lower() for w in words if w.lower() not in STOPWORDS and len(w) > 1]

        ngrams = []
        if len(key_terms) >= 2:
            for i in range(len(key_terms) - 1):
                ngrams.append(f"{key_terms[i]} {key_terms[i+1]}")
        if len(key_terms) >= 3:
            for i in range(len(key_terms) - 2):
                ngrams.append(f"{key_terms[i]} {key_terms[i+1]} {key_terms[i+2]}")

        table_intent = any(k in q_lower for k in ["table", "data", "row", "column", "matrix", "values", "specification", "spec", "rate"])
        visual_intent = any(k in q_lower for k in ["diagram", "image", "photo", "figure", "drawing", "schematic", "picture", "logo", "chart", "graph"])
        ocr_intent = any(k in q_lower for k in ["scanned", "ocr", "handwritten", "text"])

        return {
            "query_raw": q_raw,
            "query_lower": q_lower,
            "proper_nouns": list(set(proper_nouns)),
            "cap_phrases": list(set(cap_phrases)),
            "key_terms": list(set(key_terms)),
            "ngrams": list(set(ngrams)),
            "intents": {
                "table": table_intent,
                "visual": visual_intent,
                "ocr": ocr_intent,
            },
        }

    def _score_chunk(
        self, query_analysis: Dict[str, Any], chunk: PDFDocumentChunk, all_candidates: List[PDFDocumentChunk]
    ) -> float:
        text = chunk.text or ""
        text_lower = text.lower()
        section = (chunk.section or "").lower()

        score = 0.0

        q_lower = query_analysis["query_lower"]
        if q_lower in text_lower:
            score += 25.0

        for phrase in query_analysis["cap_phrases"]:
            if phrase.lower() in text_lower:
                score += 18.0
            if phrase.lower() in section:
                score += 10.0

        for ngram in query_analysis["ngrams"]:
            if ngram in text_lower:
                score += 12.0
            if ngram in section:
                score += 8.0

        for entity in query_analysis["proper_nouns"]:
            ent_lower = entity.lower()
            if ent_lower in text_lower:
                score += 8.0
            if ent_lower in section:
                score += 5.0

        key_terms = query_analysis["key_terms"]
        if key_terms:
            matches = 0
            for term in key_terms:
                count = text_lower.count(term)
                if count > 0:
                    matches += 1
                    score += (1.0 + math.log(count)) * 2.5

            overlap_ratio = matches / float(len(key_terms))
            score += overlap_ratio * 10.0

        intents = query_analysis["intents"]
        if intents["table"] and chunk.content_type == ChunkContentType.TABLE:
            score += 6.0
        elif intents["visual"] and chunk.content_type in [ChunkContentType.IMAGE, ChunkContentType.DIAGRAM]:
            score += 6.0
        elif intents["ocr"] and chunk.content_type == ChunkContentType.OCR:
            score += 6.0

        norm_score = min(1.0, score / 45.0)
        return norm_score

    def _expand_neighbor_context(
        self, primary_chunks: List[PDFDocumentChunk], all_chunks: List[PDFDocumentChunk]
    ) -> List[PDFDocumentChunk]:
        result_set = {c.chunk_id: c for c in primary_chunks}
        chunk_map = {c.chunk_id: (idx, c) for idx, c in enumerate(all_chunks)}

        for primary in list(primary_chunks):
            if (primary.relevance_score or 0.0) >= 0.50:
                if primary.chunk_id in chunk_map:
                    idx, _ = chunk_map[primary.chunk_id]
                    if idx > 0:
                        prev_c = all_chunks[idx - 1]
                        if prev_c.page_number == primary.page_number and prev_c.chunk_id not in result_set:
                            prev_copy = prev_c.model_copy()
                            prev_copy.relevance_score = round((primary.relevance_score or 0.0) * 0.85, 3)
                            prev_copy.metadata["context_type"] = "supporting_neighbor"
                            result_set[prev_copy.chunk_id] = prev_copy

                    if idx < len(all_chunks) - 1:
                        next_c = all_chunks[idx + 1]
                        if next_c.page_number == primary.page_number and next_c.chunk_id not in result_set:
                            next_copy = next_c.model_copy()
                            next_copy.relevance_score = round((primary.relevance_score or 0.0) * 0.85, 3)
                            next_copy.metadata["context_type"] = "supporting_neighbor"
                            result_set[next_copy.chunk_id] = next_copy

        return list(result_set.values())

    def _build_fallback_chunk(self, document_id: str) -> PDFDocumentChunk:
        return PDFDocumentChunk(
            chunk_id=f"chk_fallback_{document_id}",
            document_id=document_id,
            page_number=1,
            section="Retrieval Notice",
            content_type=ChunkContentType.TEXT,
            text="No sufficiently relevant evidence found in this document.",
            source="retriever",
            relevance_score=0.0,
            metadata={"status": "no_relevant_evidence_found"},
        )
