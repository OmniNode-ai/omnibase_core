"""
Tool discovery result model for ONEX tool discovery operations.

This model encapsulates the results of tool discovery and instantiation
as part of NODEBASE-001 Phase 3 deconstruction.

Author: ONEX Framework Team
"""

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.decorators import allow_any_type


@allow_any_type("Model must store generic tool instances and metadata")
class ModelToolDiscoveryResult(BaseModel):
    """
    Result model for tool discovery and instantiation operations.

    Encapsulates the results of tool class discovery, module resolution,
    instantiation, and metadata collection with comprehensive details.
    """

    tool_instance: Any = Field(
        ...,
        description="Successfully instantiated tool instance",
    )

    tool_class: type = Field(..., description="Tool class type that was instantiated")

    module_path: str = Field(
        ...,
        description="Python module path used for tool discovery",
    )

    tool_class_name: str = Field(
        ...,
        description="Name of the tool class in the module",
    )

    contract_path: Path = Field(
        ...,
        description="Path to contract file used for discovery",
    )

    discovery_method: str = Field(
        ...,
        description="Method used for tool discovery (module|registry|cached)",
    )

    instantiation_method: str = Field(
        ...,
        description="Method used for tool instantiation (container|registry|direct)",
    )

    registry_key: str | None = Field(
        default=None,
        description="Registry key used for legacy registry resolution",
    )

    module_import_time_ms: float | None = Field(
        default=None,
        description="Time taken to import tool module in milliseconds",
        ge=0,
    )

    tool_instantiation_time_ms: float | None = Field(
        default=None,
        description="Time taken to instantiate tool in milliseconds",
        ge=0,
    )

    validation_results: dict[str, bool] = Field(
        default_factory=dict,
        description="Results of various validation checks performed",
    )

    tool_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata extracted from tool class and module",
    )

    discovery_warnings: list[str] = Field(
        default_factory=list,
        description="Non-critical warnings encountered during discovery",
    )

    fallback_used: bool = Field(
        default=False,
        description="Whether fallback resolution method was used",
    )

    cache_hit: bool = Field(
        default=False,
        description="Whether cached module or tool instance was used",
    )

    total_time_ms: float | None = Field(
        default=None,
        description="Total time for complete tool resolution in milliseconds",
        ge=0,
    )

    class Config:
        """Pydantic configuration."""

        arbitrary_types_allowed = True
