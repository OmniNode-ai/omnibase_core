"""
Advanced models for LangExtract-enhanced adaptive chunking results.

Supports Milestone 2: Adaptive Chunking enhanced with LangExtract patterns.
"""

from datetime import datetime
from typing import Dict, List, Optional, Set

from pydantic import BaseModel, Field

from .model_adaptive_chunk import (ModelModelAdaptiveChunk,
                                   ModelModelAdaptiveChunkMetadata)
from .model_chunking_quality_metrics import ModelModelChunkingQualityMetrics
from .model_semantic_boundary import ModelModelSemanticBoundary


class ModelModelEntityPreservation(BaseModel):
    """Information about entity preservation in adaptive chunks."""

    entity_name: str = Field(..., description="Name of the preserved entity")
    entity_type: str = Field(
        ..., description="Type of the entity (person, organization, concept, etc.)"
    )
    preservation_windows: List[Dict[str, int]] = Field(
        default_factory=list,
        description="Character ranges where this entity should be preserved",
    )
    confidence_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence in entity extraction and preservation",
    )


class ModelModelContentDensityAnalysis(BaseModel):
    """Analysis of content density for adaptive chunking."""

    position: int = Field(
        ..., description="Character position of this density measurement"
    )
    density_score: float = Field(
        ..., ge=0.0, le=1.0, description="Content density score at this position"
    )
    word_variety_score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Word variety contribution to density"
    )
    pattern_density_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="LangExtract pattern density contribution",
    )
    entity_density_score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Entity density contribution"
    )
    window_size: int = Field(
        default=100, description="Size of the analysis window in characters"
    )


class ModelModelAdaptiveChunkingResult(BaseModel):
    """Complete result of LangExtract-enhanced adaptive chunking."""

    # Core Results
    chunks: List[ModelModelAdaptiveChunk] = Field(
        ..., description="Generated adaptive chunks with metadata"
    )
    quality_metrics: ModelModelChunkingQualityMetrics = Field(
        ..., description="Quality metrics for the chunking operation"
    )

    # Analysis Data
    semantic_boundaries: List[ModelModelSemanticBoundary] = Field(
        default_factory=list, description="Detected semantic boundaries"
    )
    entity_preservation_map: List[ModelModelEntityPreservation] = Field(
        default_factory=list, description="Entity preservation information"
    )
    content_density_analysis: List[ModelModelContentDensityAnalysis] = Field(
        default_factory=list, description="Content density analysis results"
    )

    # Configuration and Context
    original_content_length: int = Field(
        ..., description="Length of original content in characters"
    )
    chunking_strategy: str = Field(
        default="langextract_adaptive", description="Chunking strategy used"
    )
    intelligence_available: bool = Field(
        ..., description="Whether LangExtract intelligence was available"
    )
    entities_available: bool = Field(
        ..., description="Whether entity extraction was available"
    )

    # Enhancement Metrics
    total_patterns_detected: int = Field(
        default=0, description="Total LangExtract patterns detected"
    )
    total_entities_preserved: int = Field(
        default=0, description="Total entities preserved across chunks"
    )
    unique_semantic_boundaries: int = Field(
        default=0, description="Number of unique semantic boundaries found"
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="When this result was created"
    )
    processing_completed_at: Optional[datetime] = Field(
        None, description="When processing was completed"
    )

    def get_chunks_by_boundary_type(
        self, boundary_type: str
    ) -> List[ModelModelAdaptiveChunk]:
        """Get chunks created using a specific boundary type."""
        matching_chunks = []
        for chunk in self.chunks:
            if chunk.adaptive_metadata.boundary_type == boundary_type:
                matching_chunks.append(chunk)
        return matching_chunks

    def get_high_confidence_chunks(
        self, confidence_threshold: float = 0.7
    ) -> List[ModelModelAdaptiveChunk]:
        """Get chunks with high boundary confidence."""
        high_confidence_chunks = []
        for chunk in self.chunks:
            if chunk.adaptive_metadata.boundary_confidence >= confidence_threshold:
                high_confidence_chunks.append(chunk)
        return high_confidence_chunks

    def get_entity_rich_chunks(
        self, min_entities: int = 2
    ) -> List[ModelModelAdaptiveChunk]:
        """Get chunks with significant entity preservation."""
        entity_rich_chunks = []
        for chunk in self.chunks:
            if len(chunk.adaptive_metadata.preserved_entities) >= min_entities:
                entity_rich_chunks.append(chunk)
        return entity_rich_chunks

    def calculate_improvement_over_baseline(
        self, baseline_chunk_count: int
    ) -> Dict[str, float]:
        """Calculate improvement metrics compared to baseline chunking."""
        return {
            "chunk_count_efficiency": (
                len(self.chunks) / baseline_chunk_count
                if baseline_chunk_count > 0
                else 1.0
            ),
            "semantic_enhancement": self.quality_metrics.semantic_coherence_score,
            "entity_preservation": self.quality_metrics.entity_preservation_score,
            "pattern_coverage": self.quality_metrics.pattern_coverage_score,
            "intelligence_utilization": self.quality_metrics.intelligence_utilization_score,
            "overall_improvement": (
                self.quality_metrics.semantic_coherence_score * 0.3
                + self.quality_metrics.entity_preservation_score * 0.25
                + self.quality_metrics.pattern_coverage_score * 0.25
                + self.quality_metrics.boundary_accuracy_score * 0.2
            ),
        }
