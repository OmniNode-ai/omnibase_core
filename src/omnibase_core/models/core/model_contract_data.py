from pydantic import Field
from omnibase_core.models.core.model_semver import ModelSemVer

"""
Contract Data Model.

Node contract information structure.
"""

from typing import Any

from pydantic import BaseModel, Field


class ModelContractData(BaseModel):
    """Node contract information."""

    contract_version: ModelSemVer | None = Field(
        default=None, description="Contract version"
    )
    contract_name: str | None = Field(default=None, description="Contract name")
    contract_description: str | None = Field(
        default=None,
        description="Contract description",
    )

    # Contract details
    input_schema: dict[str, Any] | None = Field(
        default=None,
        description="Input schema definition",
    )
    output_schema: dict[str, Any] | None = Field(
        default=None,
        description="Output schema definition",
    )
    error_codes: list[str] = Field(
        default_factory=list,
        description="Supported error codes",
    )

    # Contract metadata
    hash: str | None = Field(default=None, description="Contract hash")
    last_modified: str | None = Field(
        default=None, description="Last modification date"
    )

    # CLI interface
    cli_commands: list[str] = Field(
        default_factory=list,
        description="Available CLI commands",
    )
    exit_codes: dict[str, int] | None = Field(
        default=None, description="Exit code mappings"
    )
