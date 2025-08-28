"""
Model for multi-document generation result.

This model contains the results of generating models from a contract
and its associated documents.
"""

from pathlib import Path
from typing import List

from pydantic import BaseModel, Field

from omnibase.model.core.model_generated_file import ModelGeneratedFile
from omnibase.model.core.model_onex_error import ModelOnexError
from omnibase.model.core.model_onex_warning import ModelOnexWarning


class ModelMultiDocGenerationResult(BaseModel):
    """Result of multi-document model generation."""

    contract_path: Path = Field(
        ..., description="Path to the source contract.yaml file"
    )
    output_dir: Path = Field(..., description="Directory where files were generated")
    generated_files: List[ModelGeneratedFile] = Field(
        default_factory=list, description="List of generated files"
    )
    contract_hash: str = Field(
        default="", description="SHA256 hash of the contract content"
    )
    errors: List[ModelOnexError] = Field(
        default_factory=list,
        description="List of structured error messages encountered",
    )
    warnings: List[ModelOnexWarning] = Field(
        default_factory=list,
        description="List of structured warning messages encountered",
    )
