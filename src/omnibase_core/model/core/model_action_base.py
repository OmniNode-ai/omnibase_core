"""
Base Action Model

Base class for all action models with tool-as-a-service support.
Provides UUID correlation tracking, trust scores, and service metadata.
"""

from datetime import datetime
from typing import Dict, List, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ModelActionBase(BaseModel):
    """
    Base class for all action models with tool-as-a-service support.

    Provides UUID correlation tracking, trust scores, and service metadata
    required for MCP/GraphQL integration and tool composition.

    Inherits from BaseModel for domain model functionality.
    """

    # Action tracking with strong typing
    action_correlation_id: UUID = Field(
        default_factory=uuid4,
        description="Unique correlation ID for tracking action definition",
    )
    action_created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Action model creation timestamp"
    )
    trust_level: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Trust score for action validation (0.0-1.0)",
    )

    # Service metadata for tool-as-a-service with strong typing
    service_metadata: Dict[str, Union[str, int, float, bool, List[str]]] = Field(
        default_factory=dict, description="Service discovery and composition metadata"
    )
    tool_discovery_tags: List[str] = Field(
        default_factory=list, description="Tags for tool discovery and categorization"
    )

    # MCP/GraphQL compatibility with strong typing
    mcp_schema_version: str = Field(
        default="1.0.0", description="MCP schema version for compatibility"
    )
    graphql_compatible: bool = Field(
        default=True, description="Whether action supports GraphQL serialization"
    )
