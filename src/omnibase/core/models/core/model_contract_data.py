"""
Contract Data Model.

Node contract information structure.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ModelContractData(BaseModel):
    """Node contract information."""

    contract_version: Optional[str] = Field(None, description="Contract version")
    contract_name: Optional[str] = Field(None, description="Contract name")
    contract_description: Optional[str] = Field(
        None, description="Contract description"
    )

    # Contract details
    input_schema: Optional[Dict[str, Any]] = Field(
        None, description="Input schema definition"
    )
    output_schema: Optional[Dict[str, Any]] = Field(
        None, description="Output schema definition"
    )
    error_codes: List[str] = Field(
        default_factory=list, description="Supported error codes"
    )

    # Contract metadata
    hash: Optional[str] = Field(None, description="Contract hash")
    last_modified: Optional[str] = Field(None, description="Last modification date")

    # CLI interface
    cli_commands: List[str] = Field(
        default_factory=list, description="Available CLI commands"
    )
    exit_codes: Optional[Dict[str, int]] = Field(None, description="Exit code mappings")
