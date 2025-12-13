"""
ModelTierConfig

Configuration for processing tiers and model availability.

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
===============================================
This module is part of a carefully managed import chain to avoid circular dependencies.

Safe Runtime Imports (OK to import at module level):
- Standard library modules only
"""

from pydantic import BaseModel, Field


class ModelTierConfig(BaseModel):
    """Configuration for processing tiers and model availability."""

    local_small: str = Field(default="llama3.2:1b", description="Small local model")
    local_medium: str = Field(default="llama3.2:3b", description="Medium local model")
    local_large: str = Field(default="llama3.2:8b", description="Large local model")
    local_huge: str = Field(default="llama3.2:70b", description="Huge local model")
    cloud_gpt: str = Field(default="gpt-4o", description="Cloud GPT model")
    cloud_claude: str = Field(
        default="claude-3-5-sonnet-20241022",
        description="Cloud Claude model",
    )

    timeout_seconds: int = Field(default=300, description="Processing timeout")
    retry_attempts: int = Field(default=3, description="Retry attempts")
