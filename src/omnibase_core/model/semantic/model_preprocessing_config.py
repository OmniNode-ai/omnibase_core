"""
Preprocessing configuration model for semantic discovery engine.

This model defines configuration options for advanced text preprocessing
including chunk sizes, overlap strategies, and language-aware processing.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic_core import ValidationInfo

from omnibase_core.model.semantic.model_chunk_strategy import \
    ModelChunkStrategy
from omnibase_core.model.semantic.model_language_detection_mode import \
    ModelLanguageDetectionMode
from omnibase_core.model.semantic.model_overlap_strategy import \
    ModelOverlapStrategy


class ModelPreprocessingConfig(BaseModel):
    """
    Configuration for advanced text preprocessing in semantic discovery.

    This model provides comprehensive configuration options for optimizing
    text chunking, overlap handling, and language-aware processing.
    """

    # Chunk Size Configuration
    chunk_size: int = Field(
        default=512, ge=50, le=8192, description="Target chunk size in tokens"
    )

    chunk_strategy: ModelChunkStrategy = Field(
        default=ModelChunkStrategy.TOKEN_BASED,
        description="Strategy for determining chunk boundaries",
    )

    # Overlap Configuration
    overlap_size: int = Field(
        default=50,
        ge=0,
        le=512,
        description="Number of tokens to overlap between chunks",
    )

    overlap_strategy: ModelOverlapStrategy = Field(
        default=ModelOverlapStrategy.FIXED_OVERLAP,
        description="Strategy for handling chunk overlap",
    )

    stride: Optional[int] = Field(
        default=None,
        ge=1,
        le=1024,
        description="Stride size for stride-based overlap (if using stride strategy)",
    )

    # Language Processing
    language_detection: ModelLanguageDetectionMode = Field(
        default=ModelLanguageDetectionMode.AUTO_DETECT,
        description="Language detection and processing mode",
    )

    forced_language: Optional[str] = Field(
        default=None,
        regex=r"^[a-z]{2}(-[A-Z]{2})?$",
        description="Forced language code (e.g., 'en', 'en-US') when using forced mode",
    )

    # Sentence Boundary Detection
    sentence_splitting: bool = Field(
        default=True, description="Enable language-aware sentence boundary detection"
    )

    preserve_sentences: bool = Field(
        default=True,
        description="Avoid splitting sentences across chunk boundaries when possible",
    )

    # Content Structure Awareness
    preserve_structure: bool = Field(
        default=True,
        description="Attempt to preserve document structure (headers, paragraphs, etc.)",
    )

    structure_markers: List[str] = Field(
        default_factory=lambda: ["#", "##", "###", "####", "*", "-", "1.", "2.", "3."],
        description="Markers that indicate document structure",
    )

    # Code Block Handling
    preserve_code_blocks: bool = Field(
        default=True, description="Keep code blocks intact when possible"
    )

    code_block_markers: List[str] = Field(
        default_factory=lambda: ["```", "~~~", "    ", "\t"],
        description="Markers that indicate code blocks",
    )

    # Metadata Preservation
    preserve_metadata: bool = Field(
        default=True, description="Preserve document metadata in chunks"
    )

    metadata_fields: List[str] = Field(
        default_factory=lambda: ["source", "title", "author", "section", "page"],
        description="Metadata fields to preserve in chunks",
    )

    # Performance Options
    parallel_processing: bool = Field(
        default=True, description="Enable parallel processing for large documents"
    )

    max_workers: Optional[int] = Field(
        default=None,
        ge=1,
        le=32,
        description="Maximum number of worker threads for parallel processing",
    )

    # Quality Control
    min_chunk_size: int = Field(
        default=50,
        ge=10,
        le=1000,
        description="Minimum chunk size in tokens (discard smaller chunks)",
    )

    max_chunk_size: int = Field(
        default=2048,
        ge=100,
        le=16384,
        description="Maximum chunk size in tokens (split larger chunks)",
    )

    quality_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Quality threshold for chunk validation (0.0-1.0)",
    )

    @field_validator("overlap_size")
    @classmethod
    def validate_overlap_size(cls, v: int, info: ValidationInfo) -> int:
        """Ensure overlap size is smaller than chunk size."""
        chunk_size = info.data.get("chunk_size", 512) if info.data else 512
        if v >= chunk_size:
            raise ValueError(
                f"Overlap size ({v}) must be smaller than chunk size ({chunk_size})"
            )
        return v

    @field_validator("max_chunk_size")
    @classmethod
    def validate_max_chunk_size(cls, v: int, info: ValidationInfo) -> int:
        """Ensure max chunk size is larger than min and target chunk sizes."""
        data = info.data if info.data else {}
        min_chunk_size = data.get("min_chunk_size", 50)
        chunk_size = data.get("chunk_size", 512)

        if v <= min_chunk_size:
            raise ValueError(
                f"Max chunk size ({v}) must be larger than min chunk size ({min_chunk_size})"
            )

        if v < chunk_size:
            raise ValueError(
                f"Max chunk size ({v}) should be larger than target chunk size ({chunk_size})"
            )

        return v

    @field_validator("stride")
    @classmethod
    def validate_stride(cls, v: Optional[int], info: ValidationInfo) -> Optional[int]:
        """Validate stride configuration when using stride-based overlap."""
        data = info.data if info.data else {}
        overlap_strategy = data.get("overlap_strategy")

        if overlap_strategy == ModelOverlapStrategy.STRIDE_BASED and v is None:
            raise ValueError(
                "Stride must be specified when using stride-based overlap strategy"
            )

        if v is not None:
            chunk_size = data.get("chunk_size", 512)
            if v >= chunk_size:
                raise ValueError(
                    f"Stride ({v}) must be smaller than chunk size ({chunk_size})"
                )

        return v

    @field_validator("forced_language")
    @classmethod
    def validate_forced_language(
        cls, v: Optional[str], info: ValidationInfo
    ) -> Optional[str]:
        """Validate forced language when using forced language detection mode."""
        data = info.data if info.data else {}
        language_detection = data.get("language_detection")

        if language_detection == ModelLanguageDetectionMode.FORCED and v is None:
            raise ValueError(
                "Forced language must be specified when using forced language detection mode"
            )

        return v

    def get_chunk_config(self) -> Dict[str, Any]:
        """Get chunk configuration for Haystack preprocessor."""
        return {
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.overlap_size,
            "split_by": (
                "word"
                if self.chunk_strategy == ModelChunkStrategy.TOKEN_BASED
                else "sentence"
            ),
            "split_length": self.chunk_size,
            "split_overlap": self.overlap_size,
            "split_respect_sentence_boundary": self.preserve_sentences,
        }

    def get_processing_config(self) -> Dict[str, Any]:
        """Get processing configuration for advanced features."""
        return {
            "language_detection": self.language_detection.value,
            "forced_language": self.forced_language,
            "sentence_splitting": self.sentence_splitting,
            "preserve_structure": self.preserve_structure,
            "preserve_code_blocks": self.preserve_code_blocks,
            "preserve_metadata": self.preserve_metadata,
            "parallel_processing": self.parallel_processing,
            "max_workers": self.max_workers,
            "quality_threshold": self.quality_threshold,
        }

    model_config = ConfigDict(
        use_enum_values=True, validate_assignment=True, extra="forbid"
    )
