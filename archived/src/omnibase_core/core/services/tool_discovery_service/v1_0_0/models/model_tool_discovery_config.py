"""
Tool discovery configuration model for ONEX tool discovery service.

This model defines the configuration options for tool discovery and instantiation
as part of NODEBASE-001 Phase 3 deconstruction.

Author: ONEX Framework Team
"""

from pydantic import BaseModel, Field


class ModelToolDiscoveryConfig(BaseModel):
    """
    Configuration model for tool discovery service operations.

    Defines configuration options for tool class discovery, module resolution,
    instantiation, and error handling.
    """

    enable_module_caching: bool = Field(
        default=True,
        description="Enable caching of imported modules for performance",
    )

    enable_tool_validation: bool = Field(
        default=True,
        description="Enable validation of tool classes before instantiation",
    )

    enable_legacy_registry_fallback: bool = Field(
        default=True,
        description="Enable fallback to legacy registry pattern for tool resolution",
    )

    enable_security_validation: bool = Field(
        default=True,
        description="Enable security validation of module paths",
    )

    max_module_import_retries: int = Field(
        default=3,
        description="Maximum number of retries for module import failures",
        ge=0,
        le=10,
    )

    tool_instantiation_timeout_seconds: float | None = Field(
        default=30.0,
        description="Timeout for tool instantiation operations",
        gt=0,
        le=300.0,
    )

    module_path_validation_strict: bool = Field(
        default=True,
        description="Use strict validation for module paths (recommended for security)",
    )

    cache_tool_instances: bool = Field(
        default=False,
        description="Enable caching of tool instances (use with caution for stateful tools)",
    )
