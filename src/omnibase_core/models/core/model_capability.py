import uuid
from typing import Any

from pydantic import Field

from omnibase_core.primitives.model_semver import ModelSemVer

"""
Capability Model

Extensible capability definition that replaces hardcoded capability enums
with flexible, third-party extensible capabilities.
"""

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ModelCapability(BaseModel):
    """
    Extensible capability definition.

    This model allows nodes to define and register custom capabilities
    beyond hardcoded enums, enabling third-party extensibility.
    """

    capability_id: UUID = Field(
        default_factory=uuid4,
        description="Unique capability identifier",
    )

    name: str = Field(
        default=..., description="Capability name", pattern="^[a-z][a-z0-9_]*$"
    )

    namespace: str = Field(
        default="onex",
        description="Capability namespace",
        pattern="^[a-z][a-z0-9._]*$",
    )

    version: ModelSemVer = Field(
        default_factory=lambda: ModelSemVer(major=1, minor=0, patch=0),
        description="Capability version",
    )

    display_name: str = Field(default=..., description="Human-readable capability name")

    description: str = Field(default=..., description="What this capability provides")

    category: str = Field(
        default="general",
        description="Capability category",
        pattern="^[a-z][a-z0-9_]*$",
    )

    dependencies: list[str] = Field(
        default_factory=list,
        description="Required capability names (namespace:name format)",
    )

    conflicts_with: list[str] = Field(
        default_factory=list,
        description="Conflicting capability names",
    )

    deprecated: bool = Field(default=False, description="Deprecation flag")

    deprecation_message: str | None = Field(
        default=None, description="Deprecation message"
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Creation timestamp",
    )

    expires_at: datetime | None = Field(
        default=None, description="Expiration timestamp"
    )

    tags: list[str] = Field(default_factory=list, description="Capability tags")

    def get_qualified_name(self) -> str:
        """Get fully qualified capability name."""
        return f"{self.namespace}:{self.name}"

    def matches(self, other: "ModelCapability") -> bool:
        """
        Check if this capability matches another.

        Args:
            other: Capability to compare

        Returns:
            True if capabilities match (name, namespace, version)
        """
        return (
            self.name == other.name
            and self.namespace == other.namespace
            and self.version == other.version
        )

    def is_compatible_with(self, other: "ModelCapability") -> bool:
        """
        Check if this capability is compatible with another.

        Args:
            other: Capability to check compatibility

        Returns:
            True if capabilities are compatible
        """
        # Check for conflicts
        if self.get_qualified_name() in other.conflicts_with:
            return False
        if other.get_qualified_name() in self.conflicts_with:
            return False

        # Same capability with different versions may be incompatible
        if self.name == other.name and self.namespace == other.namespace:
            # For now, only exact version match is compatible
            return self.version == other.version

        return True

    def is_expired(self) -> bool:
        """Check if capability has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    @classmethod
    def create_standard(cls, name: str, description: str) -> "ModelCapability":
        """
        Create a standard ONEX capability.

        Args:
            name: Capability name
            description: Capability description

        Returns:
            Standard capability with onex namespace
        """
        return cls(
            name=name,
            namespace="onex",
            display_name=name.replace("_", " ").title(),
            description=description,
            category="standard",
        )

    @classmethod
    def create_onex_capability(cls, name: str, description: str) -> "ModelCapability":
        """Factory method for ONEX core capabilities."""
        return cls(
            name=name,
            namespace="onex",
            display_name=name.replace("_", " ").title(),
            version=ModelSemVer(major=1, minor=0, patch=0),
            description=description,
            category="core",
        )

    # Common capability factories
    @classmethod
    def cli_interface(cls) -> "ModelCapability":
        """CLI interface capability."""
        return cls.create_onex_capability(
            "cli_interface",
            "Provides CLI interface for command execution",
        )

    @classmethod
    def event_bus(cls) -> "ModelCapability":
        """Event bus capability."""
        return cls.create_onex_capability("event_bus", "Provides event bus integration")

    @classmethod
    def introspection(cls) -> "ModelCapability":
        """Introspection capability."""
        return cls.create_onex_capability(
            "introspection",
            "Provides node introspection capabilities",
        )

    @classmethod
    def health_check(cls) -> "ModelCapability":
        """Health check capability."""
        return cls.create_onex_capability(
            "health_check",
            "Provides health check endpoints",
        )

    @classmethod
    def logging(cls) -> "ModelCapability":
        """Logging capability."""
        return cls.create_onex_capability("logging", "Provides structured logging")

    @classmethod
    def monitoring(cls) -> "ModelCapability":
        """Monitoring capability."""
        return cls.create_onex_capability(
            "monitoring",
            "Provides monitoring and metrics",
        )

    @classmethod
    def caching(cls) -> "ModelCapability":
        """Caching capability."""
        return cls.create_onex_capability("caching", "Provides caching functionality")

    @classmethod
    def persistence(cls) -> "ModelCapability":
        """Persistence capability."""
        return cls.create_onex_capability("persistence", "Provides data persistence")

    @classmethod
    def networking(cls) -> "ModelCapability":
        """Networking capability."""
        return cls.create_onex_capability(
            "networking",
            "Provides network communication",
        )

    @classmethod
    def security(cls) -> "ModelCapability":
        """Security capability."""
        return cls.create_onex_capability("security", "Provides security features")

    @classmethod
    def validation(cls) -> "ModelCapability":
        """Validation capability."""
        return cls.create_onex_capability("validation", "Provides data validation")

    @classmethod
    def transformation(cls) -> "ModelCapability":
        """Transformation capability."""
        return cls.create_onex_capability(
            "transformation",
            "Provides data transformation",
        )

    @classmethod
    def aggregation(cls) -> "ModelCapability":
        """Aggregation capability."""
        return cls.create_onex_capability("aggregation", "Provides data aggregation")

    @classmethod
    def routing(cls) -> "ModelCapability":
        """Routing capability."""
        return cls.create_onex_capability("routing", "Provides request routing")

    @classmethod
    def load_balancing(cls) -> "ModelCapability":
        """Load balancing capability."""
        return cls.create_onex_capability("load_balancing", "Provides load balancing")

    @classmethod
    def create_execution_capability(cls) -> "ModelCapability":
        """Execution capability for comprehensive testing."""
        return cls.create_onex_capability(
            "execution",
            "Provides node execution capabilities",
        )
