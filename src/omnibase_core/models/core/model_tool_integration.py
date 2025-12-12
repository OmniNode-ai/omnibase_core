"""
Tool Integration Model.

Service integration configuration for tool with deployment settings.
"""

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_tool_integration_summary import (
    ModelToolIntegrationSummary,
)
from omnibase_core.models.core.model_tool_resource_requirements import (
    ModelToolResourceRequirements,
)
from omnibase_core.models.core.model_tool_timeout_settings import (
    ModelToolTimeoutSettings,
)

__all__ = [
    "ModelToolIntegration",
    "ModelToolIntegrationSummary",
    "ModelToolResourceRequirements",
    "ModelToolTimeoutSettings",
]


class ModelToolIntegration(BaseModel):
    """Service integration configuration for tool."""

    auto_load_strategy: str = Field(
        default="current_stable", description="Strategy for loading tool versions"
    )
    fallback_versions: list[str] = Field(
        default_factory=list, description="Fallback versions if preferred unavailable"
    )
    version_directory_pattern: str = Field(
        default="v{major}_{minor}_{patch}", description="Directory pattern for versions"
    )
    implementation_file: str = Field(
        default="node.py", description="Main implementation file name"
    )
    contract_file: str = Field(
        default="contract.yaml", description="Contract file name"
    )
    main_class_name: str = Field(description="Main implementation class name")
    load_as_module: bool = Field(
        default=True, description="Whether loaded as module by service"
    )
    requires_separate_port: bool = Field(
        default=False, description="Whether tool requires separate HTTP port"
    )
    initialization_order: int = Field(
        default=5, description="Initialization order relative to other tools"
    )
    shutdown_timeout: int = Field(
        default=30, description="Graceful shutdown timeout in seconds"
    )
    health_check_via_service: bool = Field(
        default=True, description="Whether health checked by parent service"
    )

    def get_load_strategy(self) -> str:
        """Get load strategy in lowercase."""
        return self.auto_load_strategy.lower()

    def has_fallback_versions(self) -> bool:
        """Check if tool has fallback versions."""
        return len(self.fallback_versions) > 0

    def get_directory_pattern_type(self) -> str:
        """Get directory pattern type."""
        if "{major}" in self.version_directory_pattern:
            return "semantic_version"
        elif "{version}" in self.version_directory_pattern:
            return "simple_version"
        else:
            return "static"

    def get_required_resources(self) -> ModelToolResourceRequirements:
        """Get required resources summary."""
        return ModelToolResourceRequirements(
            requires_separate_port=self.requires_separate_port,
            health_check_via_service=self.health_check_via_service,
            loaded_as_module=self.load_as_module,
        )

    def get_timeout_settings(self) -> ModelToolTimeoutSettings:
        """Get timeout-related settings."""
        return ModelToolTimeoutSettings(
            shutdown_timeout=self.shutdown_timeout,
            initialization_order=self.initialization_order,
        )

    def get_summary(self) -> ModelToolIntegrationSummary:
        """Get integration summary."""
        return ModelToolIntegrationSummary(
            auto_load_strategy=self.get_load_strategy(),
            has_fallback_versions=self.has_fallback_versions(),
            fallback_versions_count=len(self.fallback_versions),
            directory_pattern_type=self.get_directory_pattern_type(),
            implementation_file=self.implementation_file,
            contract_file=self.contract_file,
            main_class_name=self.main_class_name,
            resources=self.get_required_resources(),
            timeout_settings=self.get_timeout_settings(),
        )
