#!/usr/bin/env python3
"""
Indexing Configuration Model - ONEX Standards Compliant.

Strongly-typed model for adaptive chunking and indexing configuration.
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ModelIndexingConfiguration(BaseModel):
    """
    Model for indexing and chunking configuration.

    Used by adaptive chunkers to configure content processing,
    chunk sizing, overlap settings, and quality thresholds.
    """

    chunk_size: int = Field(
        description="Target chunk size in characters",
        default=1000,
        ge=100,
        le=10000,
    )

    chunk_overlap: int = Field(
        description="Overlap between chunks in characters",
        default=100,
        ge=0,
        le=500,
    )

    min_chunk_size: int = Field(
        description="Minimum allowed chunk size",
        default=200,
        ge=50,
    )

    max_chunk_size: int = Field(
        description="Maximum allowed chunk size",
        default=2000,
        ge=500,
    )

    use_semantic_splitting: bool = Field(
        description="Enable semantic boundary detection for splitting",
        default=True,
    )

    preserve_code_blocks: bool = Field(
        description="Preserve code blocks intact when possible",
        default=True,
    )

    preserve_tables: bool = Field(
        description="Preserve table structures intact",
        default=True,
    )

    quality_threshold: float = Field(
        description="Minimum quality threshold for chunks",
        default=0.7,
        ge=0.0,
        le=1.0,
    )

    enable_entity_extraction: bool = Field(
        description="Enable entity extraction during chunking",
        default=True,
    )

    enable_relationship_detection: bool = Field(
        description="Enable relationship detection between chunks",
        default=False,
    )

    supported_formats: List[str] = Field(
        description="Supported content formats",
        default_factory=lambda: ["text", "markdown", "html", "json"],
    )

    metadata_extraction_enabled: bool = Field(
        description="Enable metadata extraction from content",
        default=True,
    )

    language_detection_enabled: bool = Field(
        description="Enable automatic language detection",
        default=True,
    )

    custom_separators: Optional[List[str]] = Field(
        description="Custom separators for content splitting",
        default=None,
    )

    additional_config: Dict[str, str] = Field(
        description="Additional configuration parameters",
        default_factory=dict,
    )

    class Config:
        """Pydantic model configuration for ONEX compliance."""

        validate_assignment = True
