"""
Model for runtime information in introspection metadata.
"""

from pydantic import BaseModel, Field


class ModelIntrospectionRuntimeInfo(BaseModel):
    """Runtime information for introspection metadata."""

    python_path: str = Field(description="Python path of the module")
    module_path: str = Field(description="Module import path")
    command_pattern: str = Field(description="Command pattern for execution")
    supports_hub: bool = Field(
        default=False,
        description="Whether supports hub execution",
    )
    available_modes: list[str] = Field(
        default_factory=list,
        description="Available execution modes",
    )
    memory_usage_mb: float | None = Field(
        default=None,
        description="Memory usage in MB",
    )
