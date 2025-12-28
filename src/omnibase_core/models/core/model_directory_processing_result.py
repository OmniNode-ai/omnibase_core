from pydantic import Field

# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-06-28T00:00:00.000000'
# description: Directory Processing Result Model
# entrypoint: python://model_directory_processing_result
# hash: generated
# last_modified_at: '2025-06-28T00:00:00.000000+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: model_directory_processing_result.py
# namespace: python://omnibase.model.core.model_directory_processing_result
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: {}
# uuid: generated
# version: 1.0.0
# === /OmniNode:Metadata ===

"""
Model for directory processing results.
"""

from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from .model_skipped_file_reason import ModelSkippedFileReason

if TYPE_CHECKING:
    from .model_file_filter import ModelFileFilter


class ModelDirectoryProcessingResult(BaseModel):
    """
    Results model for directory processing operations.

    This model captures the outcome of a directory processing operation,
    including counts of processed, failed, and skipped files.
    """

    # File statistics
    processed_count: int = Field(default=0, description="Number of files processed")
    failed_count: int = Field(
        default=0, description="Number of files that failed processing"
    )
    skipped_count: int = Field(default=0, description="Number of files skipped")

    # File sets
    processed_files: set[Path] = Field(
        default_factory=set,
        description="Set of processed files",
    )
    failed_files: set[Path] = Field(
        default_factory=set,
        description="Set of files that failed processing",
    )
    skipped_files: set[Path] = Field(
        default_factory=set,
        description="Set of files skipped",
    )

    # Processing metadata
    total_size_bytes: int = Field(
        default=0,
        description="Total size of processed files in bytes",
    )
    directory: Path | None = Field(
        default=None, description="Directory that was processed"
    )
    filter_config: "ModelFileFilter | None" = Field(
        default=None,
        description="Filter configuration used",
    )

    skipped_file_reasons: list[ModelSkippedFileReason] = Field(
        default_factory=list,
        description="List of skipped files and reasons",
    )

    model_config = ConfigDict(arbitrary_types_allowed=True)
