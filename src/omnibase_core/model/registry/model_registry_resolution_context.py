"""
Enterprise Registry Resolution Context Model.

This module provides comprehensive registry resolution context management with business intelligence,
dependency tracking, and operational insights for ONEX registry resolution systems.
"""

import os
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, Field, field_validator

from omnibase_core.enums.enum_dependency_mode import EnumDependencyMode
from omnibase_core.model.core.model_generic_metadata import \
    ModelGenericMetadata
from omnibase_core.model.core.model_tool_collection import ToolCollection
from omnibase_core.model.service.model_external_service_config import \
    ModelExternalServiceConfig

from .model_registry_operational_summary import ModelRegistryOperationalSummary
from .model_registry_resource_requirements import \
    ModelRegistryResourceRequirements


class ResolutionComplexity(str, Enum):
    """Registry resolution complexity levels."""

    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    ENTERPRISE = "enterprise"


class ResolutionStrategy(str, Enum):
    """Registry resolution strategy options."""

    FAST = "fast"
    COMPREHENSIVE = "comprehensive"
    FAILSAFE = "failsafe"
    DEVELOPMENT = "development"
    PRODUCTION = "production"


class ModelRegistryResolutionContext(BaseModel):
    """
    Enterprise-grade registry resolution context with comprehensive dependency management,
    business intelligence, and operational insights.

    Features:
    - Intelligent dependency mode resolution with business logic
    - External service configuration management and validation
    - Tool collection analysis and optimization
    - Performance tracking and resolution analytics
    - Security assessment and configuration validation
    - Business intelligence and operational insights
    - Factory methods for common scenarios
    """

    scenario_path: Optional[Path] = Field(
        None, description="Path to the scenario YAML file"
    )

    dependency_mode: EnumDependencyMode = Field(
        EnumDependencyMode.MOCK,
        description="Resolved dependency mode for tool injection",
    )

    external_services: Dict[str, ModelExternalServiceConfig] = Field(
        default_factory=dict,
        description="External service configurations when dependency_mode is REAL",
    )

    registry_tools: ToolCollection = Field(
        default_factory=dict, description="Tool collection for registry injection"
    )

    node_dir: Optional[Path] = Field(
        None, description="Node directory for context-aware tools"
    )

    force_dependency_mode: Optional[EnumDependencyMode] = Field(
        None, description="CLI override for dependency mode (for debugging/CI)"
    )

    resolution_strategy: Optional[ResolutionStrategy] = Field(
        default=ResolutionStrategy.COMPREHENSIVE,
        description="Strategy for registry resolution",
    )

    timeout_seconds: Optional[int] = Field(
        default=30, description="Timeout for resolution operations", ge=1, le=300
    )

    retry_count: Optional[int] = Field(
        default=3, description="Number of retries for failed resolutions", ge=0, le=10
    )

    cache_enabled: Optional[bool] = Field(
        default=True, description="Whether to use caching for resolution results"
    )

    validation_enabled: Optional[bool] = Field(
        default=True, description="Whether to validate resolved configurations"
    )

    metadata: Optional[ModelGenericMetadata] = Field(
        None, description="Additional metadata and configuration"
    )

    resolution_id: Optional[str] = Field(
        default=None,
        description="Unique identifier for this resolution context",
        max_length=100,
    )

    created_at: Optional[str] = Field(
        default=None, description="ISO timestamp when context was created"
    )

    @field_validator("scenario_path")
    @classmethod
    def validate_scenario_path(cls, v: Optional[Path]) -> Optional[Path]:
        """Validate scenario path exists and is readable."""
        if v is None:
            return v

        if not isinstance(v, Path):
            v = Path(v)

        # Check if file exists and is readable
        if not v.exists():
            raise ValueError(f"Scenario path does not exist: {v}")

        if not v.is_file():
            raise ValueError(f"Scenario path is not a file: {v}")

        if not os.access(v, os.R_OK):
            raise ValueError(f"Scenario path is not readable: {v}")

        return v

    @field_validator("node_dir")
    @classmethod
    def validate_node_dir(cls, v: Optional[Path]) -> Optional[Path]:
        """Validate node directory exists and is accessible."""
        if v is None:
            return v

        if not isinstance(v, Path):
            v = Path(v)

        if not v.exists():
            raise ValueError(f"Node directory does not exist: {v}")

        if not v.is_dir():
            raise ValueError(f"Node directory is not a directory: {v}")

        return v

    @field_validator("created_at")
    @classmethod
    def validate_created_at(cls, v: Optional[str]) -> Optional[str]:
        """Validate ISO timestamp format."""
        if v is None:
            return datetime.now().isoformat()

        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
            return v
        except ValueError:
            raise ValueError("created_at must be a valid ISO timestamp")

    # === Dependency Mode Analysis ===

    def get_effective_dependency_mode(self) -> EnumDependencyMode:
        """Get the effective dependency mode, considering force override."""
        return self.force_dependency_mode or self.dependency_mode

    def is_mock_mode(self) -> bool:
        """Check if running in mock mode."""
        return self.get_effective_dependency_mode() == EnumDependencyMode.MOCK

    def is_real_mode(self) -> bool:
        """Check if running in real mode with external services."""
        return self.get_effective_dependency_mode() == EnumDependencyMode.REAL

    def is_hybrid_mode(self) -> bool:
        """Check if running in hybrid mode (note: HYBRID not currently supported)."""
        # HYBRID mode not currently available in DependencyModeEnum
        return False

    def requires_external_services(self) -> bool:
        """Check if external services are required for this mode."""
        return self.get_effective_dependency_mode() == EnumDependencyMode.REAL

    def get_dependency_complexity(self) -> ResolutionComplexity:
        """Assess the complexity of dependency resolution."""
        complexity_score = 0

        # Base complexity from dependency mode
        if self.is_real_mode():
            complexity_score += 3
        elif self.is_hybrid_mode():
            complexity_score += 2
        else:  # mock mode
            complexity_score += 1

        # Additional complexity factors
        if len(self.external_services) > 5:
            complexity_score += 2
        elif len(self.external_services) > 2:
            complexity_score += 1

        tool_count = (
            len(list(self.registry_tools.keys()))
            if hasattr(self.registry_tools, "keys")
            else 0
        )
        if tool_count > 10:
            complexity_score += 2
        elif tool_count > 5:
            complexity_score += 1

        # Map score to complexity level
        if complexity_score >= 7:
            return ResolutionComplexity.ENTERPRISE
        elif complexity_score >= 5:
            return ResolutionComplexity.COMPLEX
        elif complexity_score >= 3:
            return ResolutionComplexity.MODERATE
        else:
            return ResolutionComplexity.SIMPLE

    # === External Service Management ===

    def has_external_service(self, service_name: str) -> bool:
        """Check if a specific external service is configured."""
        return service_name in self.external_services

    def get_external_service(
        self, service_name: str
    ) -> Optional[ModelExternalServiceConfig]:
        """Get configuration for a specific external service."""
        return self.external_services.get(service_name)

    def add_external_service(
        self, service_name: str, config: ModelExternalServiceConfig
    ) -> None:
        """Add or update an external service configuration."""
        self.external_services[service_name] = config

    def remove_external_service(self, service_name: str) -> bool:
        """Remove an external service configuration."""
        if service_name in self.external_services:
            del self.external_services[service_name]
            return True
        return False

    def get_external_services_by_type(
        self, service_type: str
    ) -> Dict[str, ModelExternalServiceConfig]:
        """Get all external services of a specific type."""
        return {
            name: config
            for name, config in self.external_services.items()
            if hasattr(config, "service_type") and config.service_type == service_type
        }

    def get_external_services_count(self) -> int:
        """Get total count of external services."""
        return len(self.external_services)

    def validate_external_services(self) -> List[str]:
        """Validate all external service configurations."""
        issues = []

        for service_name, config in self.external_services.items():
            # Check if config is valid
            try:
                # Basic validation - config should have required fields
                if not hasattr(config, "service_name") or not config.service_name:
                    issues.append(f"Service {service_name}: Missing service_name")

                # Additional validation can be added here

            except Exception as e:
                issues.append(f"Service {service_name}: Validation error - {e}")

        return issues

    # === Tool Collection Management ===

    def get_tool_count(self) -> int:
        """Get total count of tools in collection."""
        return (
            len(list(self.registry_tools.keys()))
            if hasattr(self.registry_tools, "keys")
            else 0
        )

    def has_tool(self, tool_name: str) -> bool:
        """Check if a specific tool is in the collection."""
        return tool_name in self.registry_tools

    def get_tool_names(self) -> Set[str]:
        """Get set of all tool names."""
        return set(self.registry_tools.keys())

    def get_tools_by_type(self, tool_type: str) -> Dict[str, Any]:
        """Get tools filtered by type (if type information is available)."""
        # This assumes tools have type information
        filtered_tools = {}
        for name, tool in self.registry_tools.items():
            if hasattr(tool, "tool_type") and tool.tool_type == tool_type:
                filtered_tools[name] = tool
        return filtered_tools

    # === Performance and Optimization ===

    def get_estimated_resolution_time(self) -> int:
        """Estimate resolution time in seconds based on complexity."""
        base_time = 1  # Base resolution time

        complexity = self.get_dependency_complexity()
        if complexity == ResolutionComplexity.ENTERPRISE:
            base_time *= 8
        elif complexity == ResolutionComplexity.COMPLEX:
            base_time *= 4
        elif complexity == ResolutionComplexity.MODERATE:
            base_time *= 2

        # Factor in external services
        if self.requires_external_services():
            base_time += len(self.external_services) * 2

        # Factor in strategy
        if self.resolution_strategy == ResolutionStrategy.COMPREHENSIVE:
            base_time *= 1.5
        elif self.resolution_strategy == ResolutionStrategy.FAILSAFE:
            base_time *= 2

        return min(int(base_time), self.timeout_seconds or 30)

    def should_use_cache(self) -> bool:
        """Determine if caching should be used for this resolution."""
        return (
            self.cache_enabled
            and self.resolution_strategy != ResolutionStrategy.DEVELOPMENT
            and not self.force_dependency_mode  # Don't cache forced modes
        )

    def get_cache_key(self) -> str:
        """Generate a cache key for this resolution context."""
        key_components = [
            str(self.scenario_path) if self.scenario_path else "no_scenario",
            self.get_effective_dependency_mode().value,
            str(sorted(self.external_services.keys())),
            str(sorted(self.registry_tools.keys())),
            str(self.node_dir) if self.node_dir else "no_node_dir",
            self.resolution_strategy.value if self.resolution_strategy else "default",
        ]

        cache_key = "|".join(key_components)
        return hashlib.sha256(cache_key.encode()).hexdigest()[:16]

    # === Validation and Health Checks ===

    def validate_context(self) -> List[str]:
        """Validate the entire resolution context."""
        issues = []

        # Validate paths
        if self.scenario_path and not self.scenario_path.exists():
            issues.append(f"Scenario path does not exist: {self.scenario_path}")

        if self.node_dir and not self.node_dir.exists():
            issues.append(f"Node directory does not exist: {self.node_dir}")

        # Validate external services if required
        if self.requires_external_services() and not self.external_services:
            issues.append("External services required but none configured")

        # Validate external service configurations
        issues.extend(self.validate_external_services())

        # Validate timeout settings
        estimated_time = self.get_estimated_resolution_time()
        if estimated_time > (self.timeout_seconds or 30):
            issues.append(
                f"Estimated resolution time ({estimated_time}s) exceeds timeout"
            )

        return issues

    def is_valid(self) -> bool:
        """Check if the context is valid for resolution."""
        return len(self.validate_context()) == 0

    def get_health_score(self) -> float:
        """Get a health score (0.0 to 1.0) for this context."""
        issues = self.validate_context()

        if not issues:
            return 1.0

        # Penalize based on issue count
        penalty = len(issues) * 0.2
        return max(0.0, 1.0 - penalty)

    # === Business Intelligence ===

    def get_operational_summary(self) -> ModelRegistryOperationalSummary:
        """Get operational summary for monitoring and reporting."""
        return ModelRegistryOperationalSummary(
            resolution_id=self.resolution_id,
            dependency_mode=self.get_effective_dependency_mode().value,
            complexity=self.get_dependency_complexity().value,
            strategy=(
                self.resolution_strategy.value
                if self.resolution_strategy
                else "default"
            ),
            external_services_count=self.get_external_services_count(),
            tools_count=self.get_tool_count(),
            estimated_time_seconds=self.get_estimated_resolution_time(),
            cache_enabled=self.should_use_cache(),
            validation_enabled=self.validation_enabled,
            health_score=self.get_health_score(),
            is_valid=self.is_valid(),
            created_at=self.created_at,
        )

    def get_resource_requirements(self) -> ModelRegistryResourceRequirements:
        """Estimate resource requirements for this resolution."""
        complexity = self.get_dependency_complexity()

        # Base resource estimates
        if complexity == ResolutionComplexity.ENTERPRISE:
            cpu_score, memory_score = 8, 8
        elif complexity == ResolutionComplexity.COMPLEX:
            cpu_score, memory_score = 6, 6
        elif complexity == ResolutionComplexity.MODERATE:
            cpu_score, memory_score = 4, 4
        else:
            cpu_score, memory_score = 2, 2

        return ModelRegistryResourceRequirements(
            cpu_score=cpu_score,  # 1-10 scale
            memory_score=memory_score,  # 1-10 scale
            network_required=self.requires_external_services(),
            disk_space_score=2 if self.should_use_cache() else 1,
            estimated_duration_seconds=self.get_estimated_resolution_time(),
        )

    # === Factory Methods ===

    @classmethod
    def create_mock_context(
        cls,
        scenario_path: Optional[Path] = None,
        tools: Optional[ToolCollection] = None,
    ) -> "ModelRegistryResolutionContext":
        """Create a mock resolution context for testing."""
        return cls(
            scenario_path=scenario_path,
            dependency_mode=EnumDependencyMode.MOCK,
            registry_tools=tools or {},
            resolution_strategy=ResolutionStrategy.FAST,
            cache_enabled=False,
            validation_enabled=True,
            resolution_id=f"mock_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        )

    @classmethod
    def create_development_context(
        cls, scenario_path: Path, node_dir: Path, tools: Optional[ToolCollection] = None
    ) -> "ModelRegistryResolutionContext":
        """Create a development resolution context."""
        return cls(
            scenario_path=scenario_path,
            dependency_mode=EnumDependencyMode.MOCK,
            registry_tools=tools or {},
            node_dir=node_dir,
            resolution_strategy=ResolutionStrategy.DEVELOPMENT,
            cache_enabled=True,
            validation_enabled=True,
            timeout_seconds=60,
            resolution_id=f"dev_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        )

    @classmethod
    def create_production_context(
        cls,
        scenario_path: Path,
        node_dir: Path,
        external_services: Dict[str, ModelExternalServiceConfig],
        tools: ToolCollection,
    ) -> "ModelRegistryResolutionContext":
        """Create a production resolution context."""
        return cls(
            scenario_path=scenario_path,
            dependency_mode=EnumDependencyMode.REAL,
            external_services=external_services,
            registry_tools=tools,
            node_dir=node_dir,
            resolution_strategy=ResolutionStrategy.PRODUCTION,
            cache_enabled=True,
            validation_enabled=True,
            timeout_seconds=120,
            retry_count=5,
            resolution_id=f"prod_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        )

    @classmethod
    def create_from_environment(
        cls, env_prefix: str = "ONEX_RESOLUTION_"
    ) -> "ModelRegistryResolutionContext":
        """Create resolution context from environment variables."""
        config_data = {
            "resolution_id": f"env_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        }

        # Load from environment variables
        if scenario_path := os.getenv(f"{env_prefix}SCENARIO_PATH"):
            config_data["scenario_path"] = Path(scenario_path)

        if node_dir := os.getenv(f"{env_prefix}NODE_DIR"):
            config_data["node_dir"] = Path(node_dir)

        if dependency_mode := os.getenv(f"{env_prefix}DEPENDENCY_MODE"):
            try:
                config_data["dependency_mode"] = EnumDependencyMode(
                    dependency_mode.lower()
                )
            except ValueError:
                pass

        if resolution_strategy := os.getenv(f"{env_prefix}STRATEGY"):
            try:
                config_data["resolution_strategy"] = ResolutionStrategy(
                    resolution_strategy.lower()
                )
            except ValueError:
                pass

        if timeout := os.getenv(f"{env_prefix}TIMEOUT_SECONDS"):
            try:
                config_data["timeout_seconds"] = int(timeout)
            except ValueError:
                pass

        return cls(**config_data)


# Add hashlib import for cache key generation
import hashlib
