"""
Model for multi-document generation result.

This model contains the results of generating models from a contract
and its associated documents.
"""

from pathlib import Path

from pydantic import BaseModel, Field

from omnibase_core.models.common.model_onex_warning import ModelOnexWarning
from omnibase_core.models.core.model_generated_file import ModelGeneratedFile
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class ModelMultiDocGenerationResult(BaseModel):
    """Result of multi-document model generation."""

    contract_path: Path = Field(
        default=...,
        description="Path to the source contract.yaml file",
    )
    output_dir: Path = Field(
        default=..., description="Directory where files were generated"
    )
    generated_files: list[ModelGeneratedFile] = Field(
        default_factory=list,
        description="List of generated files",
    )
    contract_hash: str = Field(
        default="",
        description="SHA256 hash of the contract content",
    )
    errors: list[ModelOnexError] = Field(
        default_factory=list,
        description="List of structured error messages encountered",
    )
    warnings: list[ModelOnexWarning] = Field(
        default_factory=list,
        description="List of structured warning messages encountered",
    )
