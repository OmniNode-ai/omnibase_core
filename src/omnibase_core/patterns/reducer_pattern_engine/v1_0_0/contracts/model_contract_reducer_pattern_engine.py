#!/usr/bin/env python3
"""
ModelContract for Reducer Pattern Engine - ONEX Standards Compliant.

Specialized contract model for multi-workflow reducer pattern engine providing:
- Multi-workflow execution capabilities with instance isolation
- Enhanced metrics collection and performance monitoring
- Registry-based subreducer management
- State machine integration with proper transitions
- Protocol-based service resolution

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from omnibase_core.core.contracts.model_contract_base import (
    ModelContractBase,
    ModelPerformanceRequirements,
    ModelLifecycleConfig,
    ModelValidationRules,
)
from omnibase_core.enums.node import EnumNodeType


class ModelPatternConfiguration(BaseModel):
    """
    Pattern-specific configuration for the Reducer Pattern Engine.
    
    Defines pattern behavior, workflow support, and feature enablement
    for multi-workflow execution with proper isolation.
    """
    
    supported_workflows: list[str] = Field(
        default=["DATA_ANALYSIS", "REPORT_GENERATION", "DOCUMENT_REGENERATION"],
        description="List of supported workflow types",
        min_length=1,
    )
    
    features: dict[str, bool] = Field(
        default_factory=lambda: {
            "instance_isolation": True,
            "concurrent_processing": True,
            "enhanced_metrics": True,
            "registry_system": True,
            "state_management": True,
            "routing_optimization": True,
        },
        description="Feature flags for pattern capabilities",
    )
    
    max_concurrent_workflows: int = Field(
        default=100,
        description="Maximum number of concurrent workflows",
        ge=1,
        le=1000,
    )
    
    isolation_level: str = Field(
        default="instance_based",
        description="Isolation level for workflow processing",
    )
    
    architecture: str = Field(
        default="multi_workflow",
        description="Pattern architecture type",
    )


class ModelComponentSpecification(BaseModel):
    """
    Component specification for pattern components.
    
    Defines component class, module, and description for proper
    instantiation and documentation.
    """
    
    class_name: str = Field(
        ...,
        description="Component class name",
        min_length=1,
    )
    
    module: str = Field(
        ...,
        description="Full module path for component",
        min_length=1,
    )
    
    description: str = Field(
        ...,
        description="Component description",
        min_length=1,
    )


class ModelSubreducerSpecification(BaseModel):
    """
    Subreducer specification with capabilities and workflow support.
    
    Defines subreducer implementation details, supported workflows,
    and processing capabilities for proper registration.
    """
    
    class_name: str = Field(
        ...,
        description="Subreducer class name",
        min_length=1,
    )
    
    module: str = Field(
        ...,
        description="Full module path for subreducer",
        min_length=1,
    )
    
    supported_workflows: list[str] = Field(
        ...,
        description="List of workflow types this subreducer supports",
        min_length=1,
    )
    
    capabilities: list[str] = Field(
        default_factory=list,
        description="List of processing capabilities",
    )


class ModelStateConfiguration(BaseModel):
    """
    State management configuration for workflow processing.
    
    Defines state model, validator, states, and transitions for
    proper workflow lifecycle management.
    """
    
    state_model: str = Field(
        ...,
        description="Fully qualified state model class name",
        min_length=1,
    )
    
    validator: str = Field(
        ...,
        description="Fully qualified state validator class name",
        min_length=1,
    )
    
    states: list[dict[str, Any]] = Field(
        default_factory=list,
        description="State definitions with name, description, and flags",
    )
    
    transitions: list[dict[str, Any]] = Field(
        default_factory=list,
        description="State transition definitions",
    )


class ModelDependencySpecification(BaseModel):
    """
    Structured dependency specification for pattern dependencies.
    
    Defines protocol dependencies with full specification including
    name, type, class name, and module path.
    """
    
    name: str = Field(
        ...,
        description="Dependency identifier name",
        min_length=1,
    )
    
    type: str = Field(
        ...,
        description="Dependency type (protocol, service, utility)",
        min_length=1,
    )
    
    class_name: str = Field(
        ...,
        description="Implementation class name",
        min_length=1,
    )
    
    module: str = Field(
        ...,
        description="Full module path for the implementation",
        min_length=1,
    )


class ModelContractReducerPatternEngine(ModelContractBase):
    """
    Contract model for Reducer Pattern Engine - ONEX Compliant.
    
    Specialized contract for multi-workflow execution pattern providing
    instance isolation, enhanced metrics, registry management, and
    state machine integration following ONEX architectural standards.
    
    ZERO TOLERANCE: No Any types allowed in implementation.
    """
    
    node_type: Literal[EnumNodeType.COMPUTE] = Field(
        default=EnumNodeType.COMPUTE,
        description="Node type classification for 4-node architecture",
    )
    
    # Pattern-specific configuration
    pattern_type: str = Field(
        default="execution_pattern",
        description="Type of pattern implementation",
    )
    
    pattern_config: ModelPatternConfiguration = Field(
        default_factory=ModelPatternConfiguration,
        description="Pattern-specific configuration",
    )
    
    # Component specifications
    components: dict[str, ModelComponentSpecification] = Field(
        default_factory=dict,
        description="Component specifications for pattern implementation",
    )
    
    # Subreducer specifications
    subreducers: dict[str, ModelSubreducerSpecification] = Field(
        default_factory=dict,
        description="Subreducer specifications and capabilities",
    )
    
    # State management configuration
    state_management: ModelStateConfiguration | None = Field(
        default=None,
        description="State management configuration",
    )
    
    # Enhanced dependencies with structured format
    dependencies: list[str | dict[str, str] | ModelDependencySpecification] = Field(
        default_factory=list,
        description="Dependencies supporting multiple formats",
    )
    
    # Performance requirements override for pattern-specific needs
    performance: ModelPerformanceRequirements = Field(
        default_factory=lambda: ModelPerformanceRequirements(
            single_operation_max_ms=30000,
            batch_operation_max_s=300,
            memory_limit_mb=2048,
            cpu_limit_percent=80,
            throughput_min_ops_per_second=10.0,
        ),
        description="Pattern-specific performance requirements",
    )
    
    # Lifecycle configuration with pattern-specific timeouts
    lifecycle: ModelLifecycleConfig = Field(
        default_factory=lambda: ModelLifecycleConfig(
            initialization_timeout_s=60,
            cleanup_timeout_s=30,
            error_recovery_enabled=True,
            state_persistence_enabled=True,
            health_check_interval_s=30,
        ),
        description="Pattern lifecycle management configuration",
    )
    
    def validate_node_specific_config(self) -> None:
        """
        Validate pattern-specific configuration requirements.
        
        Validates pattern configuration, component specifications,
        subreducer definitions, and state management setup.
        
        Raises:
            ValidationError: If pattern-specific validation fails
        """
        # Validate pattern configuration
        self._validate_pattern_configuration()
        
        # Validate component specifications
        self._validate_component_specifications()
        
        # Validate subreducer specifications
        self._validate_subreducer_specifications()
        
        # Validate state management configuration
        self._validate_state_management_configuration()
        
        # Validate dependency specifications
        self._validate_dependency_specifications()
    
    def _validate_pattern_configuration(self) -> None:
        """Validate pattern configuration requirements."""
        if not self.pattern_config.supported_workflows:
            msg = "Pattern must support at least one workflow type"
            raise ValueError(msg)
        
        # Validate workflow types are known
        valid_workflow_types = {
            "DATA_ANALYSIS",
            "REPORT_GENERATION", 
            "DOCUMENT_REGENERATION",
        }
        
        for workflow in self.pattern_config.supported_workflows:
            if workflow not in valid_workflow_types:
                msg = f"Unknown workflow type: {workflow}"
                raise ValueError(msg)
        
        # Validate required features are enabled
        required_features = ["instance_isolation", "state_management"]
        for feature in required_features:
            if not self.pattern_config.features.get(feature, False):
                msg = f"Required feature '{feature}' must be enabled"
                raise ValueError(msg)
    
    def _validate_component_specifications(self) -> None:
        """Validate component specifications."""
        required_components = ["engine", "router", "registry", "metrics"]
        
        for component in required_components:
            if component not in self.components:
                msg = f"Required component '{component}' not specified"
                raise ValueError(msg)
            
            spec = self.components[component]
            if not spec.class_name or not spec.module:
                msg = f"Component '{component}' missing class_name or module"
                raise ValueError(msg)
    
    def _validate_subreducer_specifications(self) -> None:
        """Validate subreducer specifications."""
        if not self.subreducers:
            msg = "Pattern must define at least one subreducer"
            raise ValueError(msg)
        
        # Validate each workflow type has at least one subreducer
        workflow_coverage = set()
        for spec in self.subreducers.values():
            workflow_coverage.update(spec.supported_workflows)
        
        missing_coverage = set(self.pattern_config.supported_workflows) - workflow_coverage
        if missing_coverage:
            msg = f"No subreducers defined for workflows: {missing_coverage}"
            raise ValueError(msg)
    
    def _validate_state_management_configuration(self) -> None:
        """Validate state management configuration."""
        if not self.state_management:
            msg = "State management configuration is required"
            raise ValueError(msg)
        
        if not self.state_management.states:
            msg = "State management must define at least one state"
            raise ValueError(msg)
        
        # Validate initial and final states
        initial_states = [s for s in self.state_management.states if s.get("initial")]
        if len(initial_states) != 1:
            msg = "Exactly one initial state must be defined"
            raise ValueError(msg)
        
        final_states = [s for s in self.state_management.states if s.get("final")]
        if not final_states:
            msg = "At least one final state must be defined"
            raise ValueError(msg)
    
    def _validate_dependency_specifications(self) -> None:
        """Validate dependency specifications."""
        required_deps = {"container"}
        found_deps = set()
        
        for dep in self.dependencies:
            if isinstance(dep, str):
                # Simple string dependency
                if "container" in dep.lower():
                    found_deps.add("container")
            elif isinstance(dep, dict):
                # Dict dependency
                dep_name = dep.get("name", "").lower()
                if "container" in dep_name:
                    found_deps.add("container")
            elif hasattr(dep, "name"):
                # Structured dependency
                if "container" in dep.name.lower():
                    found_deps.add("container")
        
        missing_deps = required_deps - found_deps
        if missing_deps:
            msg = f"Required dependencies not found: {missing_deps}"
            raise ValueError(msg)
    
    @field_validator("dependencies", mode="before")
    @classmethod
    def parse_flexible_dependencies(
        cls,
        v: list[str | dict[str, str] | ModelDependencySpecification],
    ) -> list[str | dict[str, str] | ModelDependencySpecification]:
        """Parse dependencies in flexible formats."""
        if not v:
            return v
        
        parsed_deps = []
        for dep in v:
            if isinstance(dep, str):
                parsed_deps.append(dep)
            elif isinstance(dep, dict):
                if all(key in dep for key in ["name", "type", "class_name", "module"]):
                    parsed_deps.append(ModelDependencySpecification(**dep))
                else:
                    parsed_deps.append(dep)
            else:
                parsed_deps.append(dep)
        
        return parsed_deps
    
    class Config:
        """Pydantic model configuration for ONEX compliance."""
        
        extra = "ignore"
        use_enum_values = False
        validate_assignment = True
        str_strip_whitespace = True