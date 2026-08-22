"""Confidence calculation schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ConfidenceSignals(BaseModel):
    """Individual signals that feed into confidence calculation."""
    source_authority: float = 0.0        # 0-1: quality of the best source
    direct_evidence: float = 0.0         # 0-1: is the value directly stated?
    evidence_quality: float = 0.0        # 0-1: retrieval score / evidence clarity
    evidence_coverage: float = 0.0       # 0-1: proportion of required attrs covered
    cross_source_agreement: float = 0.0  # 0-1: do multiple sources agree?
    validation_success: float = 0.0      # 0-1: did deterministic validation pass?
    inference_penalty: float = 0.0       # 0-1: penalty for inferred values
    conflict_penalty: float = 0.0        # 0-1: penalty for conflicting sources
    missing_context_penalty: float = 0.0 # 0-1: penalty for missing surrounding info
    provisional_penalty: float = 0.0     # 0-1: penalty for relying on PROVISIONAL tier knowledge


class ConfidenceWeights(BaseModel):
    """Configurable weights for each confidence signal."""
    source_authority: float = 0.25
    direct_evidence: float = 0.20
    evidence_quality: float = 0.10
    evidence_coverage: float = 0.10
    cross_source_agreement: float = 0.15
    validation_success: float = 0.10
    inference_penalty: float = 0.04
    conflict_penalty: float = 0.03
    missing_context_penalty: float = 0.01
    provisional_penalty: float = 0.02


class ConfidenceResult(BaseModel):
    """Calculated confidence with full explanation."""
    score: float = 0.0  # 0.0 to 1.0
    signals: ConfidenceSignals = Field(default_factory=ConfidenceSignals)
    weights_used: ConfidenceWeights = Field(default_factory=ConfidenceWeights)
    explanation: str = ""
    breakdown: dict[str, float] = Field(default_factory=dict)
