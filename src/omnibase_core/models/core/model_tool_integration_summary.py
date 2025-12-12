"""
Tool Integration Summary Model.

Summary of tool integration configuration.
"""

from pydantic import BaseModel, Field

from .model_tool_resource_requirements import ModelToolResourceRequirements
from .model_tool_timeout_settings import ModelToolTimeoutSettings


class ModelToolIntegrationSummary(BaseModel):
    """Summary of tool integration configuration."""

    auto_load_strategy: str = Field(description="Strategy for loading tool versions")
    has_fallback_versions: bool = Field(description="Whether has fallback versions")
    fallback_versions_count: int = Field(description="Number of fallback versions")
    directory_pattern_type: str = Field(description="Directory pattern type")
    implementation_file: str = Field(description="Main implementation file name")
    contract_file: str = Field(description="Contract file name")
    main_class_name: str = Field(description="Main implementation class name")
    resources: ModelToolResourceRequirements = Field(
        description="Resource requirements"
    )
    timeout_settings: ModelToolTimeoutSettings = Field(description="Timeout settings")
