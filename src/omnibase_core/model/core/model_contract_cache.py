"""
Model for contract cache representation in ONEX NodeBase implementation.

This model supports the PATTERN-005 ContractLoader functionality for
performance optimization through caching.

Author: ONEX Framework Team
"""

from pathlib import Path

from pydantic import BaseModel, Field

from omnibase_core.model.core.model_contract_content import ModelContractContent


class ModelContractCache(BaseModel):
    """Model for contract caching to improve performance."""

    file_path: Path = Field(..., description="Absolute path to cached file")
    content: ModelContractContent = Field(..., description="Cached contract content")
    last_modified: float = Field(..., description="Last modification timestamp")
