"""Service Dependency Graph Model.

Implements ProtocolDependencyGraph for service registry dependency analysis.

This model provides dependency graph information for services registered
in the service registry, including:
- Direct dependencies and dependents
- Circular reference detection
- Resolution ordering for dependency injection

Note: This is distinct from ModelDependencyGraph in workflow/execution which
is used for workflow step ordering. This model is specific to DI containers.
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.types.type_serializable_value import SerializableValue


class ModelServiceDependencyGraph(BaseModel):
    """
    Dependency graph for a service in the registry.

    Implements ProtocolDependencyGraph.
    Tracks service dependencies for proper initialization ordering
    and circular dependency detection.

    Attributes:
        service_id: ID of the service this graph describes
        dependencies: List of service IDs this service depends on
        dependents: List of service IDs that depend on this service
        depth_level: Depth in the dependency tree (0 = root, no dependencies)
        circular_references: List of service IDs forming circular dependencies
        resolution_order: Ordered list of service IDs for proper initialization
        metadata: Additional graph metadata

    Example:
        ```python
        graph = ModelServiceDependencyGraph(
            service_id=UUID("12345678-1234-5678-1234-567812345678"),
            dependencies=[UUID("aaaa-...")],
            dependents=[UUID("bbbb-...")],
            depth_level=1,
            circular_references=[],
            resolution_order=[UUID("aaaa-..."), UUID("12345678-...")],
        )
        ```
    """

    model_config = ConfigDict(
        extra="ignore",
        frozen=False,
        validate_assignment=True,
    )

    service_id: UUID = Field(description="ID of the service this graph describes")
    dependencies: list[UUID] = Field(
        default_factory=list,
        description="Service IDs this service depends on",
    )
    dependents: list[UUID] = Field(
        default_factory=list,
        description="Service IDs that depend on this service",
    )
    depth_level: int = Field(
        default=0,
        ge=0,
        description="Depth in dependency tree (0 = root with no dependencies)",
    )
    circular_references: list[UUID] = Field(
        default_factory=list,
        description="Service IDs forming circular dependencies",
    )
    resolution_order: list[UUID] = Field(
        default_factory=list,
        description="Ordered service IDs for proper initialization",
    )
    metadata: dict[str, SerializableValue] = Field(
        default_factory=dict,
        description="Additional graph metadata",
    )

    @property
    def has_circular_dependencies(self) -> bool:
        """Check if this service has circular dependencies."""
        return len(self.circular_references) > 0

    @property
    def has_dependencies(self) -> bool:
        """Check if this service has any dependencies."""
        return len(self.dependencies) > 0

    @property
    def has_dependents(self) -> bool:
        """Check if any services depend on this one."""
        return len(self.dependents) > 0

    def add_dependency(self, dependency_id: UUID) -> None:
        """Add a dependency to this service."""
        if dependency_id == self.service_id:
            return  # Ignore self-reference
        if dependency_id not in self.dependencies:
            self.dependencies.append(dependency_id)

    def add_dependent(self, service_id: UUID) -> None:
        """Add a service that depends on this one."""
        if service_id not in self.dependents:
            self.dependents.append(service_id)

    def mark_circular_reference(self, service_id: UUID) -> None:
        """Mark a circular reference with another service."""
        if service_id not in self.circular_references:
            self.circular_references.append(service_id)


__all__ = ["ModelServiceDependencyGraph"]
