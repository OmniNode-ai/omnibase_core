"""
Tag Model

User-defined tag model that replaces hardcoded tag enums
with flexible, extensible tagging system.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ModelTag(BaseModel):
    """
    User-defined tag model.

    This model allows users and third-party nodes to define custom tags
    beyond hardcoded enums, enabling flexible categorization.
    """

    tag_id: UUID = Field(default_factory=uuid4, description="Unique tag identifier")

    name: str = Field(default=..., description="Tag name", pattern="^[a-z][a-z0-9-]*$")

    namespace: str = Field(default="user", description="Tag namespace")

    display_name: str = Field(default=..., description="Display name")

    description: str | None = Field(default=None, description="Tag description")

    color: str | None = Field(
        default=None,
        description="Hex color code",
        pattern="^#[0-9A-Fa-f]{6}$",
    )

    icon: str | None = Field(default=None, description="Icon identifier")

    created_by: str = Field(default=..., description="Creator identifier")

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Creation timestamp",
    )

    is_system: bool = Field(default=False, description="System-defined tag")

    parent_tag: str | None = Field(
        default=None,
        description="Parent tag for hierarchical organization",
    )

    def get_qualified_name(self) -> str:
        """Get fully qualified tag name."""
        return f"{self.namespace}:{self.name}"

    def matches(self, other: "ModelTag") -> bool:
        """Check if tags match."""
        return self.name == other.name and self.namespace == other.namespace

    @classmethod
    def create_system_tag(
        cls,
        name: str,
        display_name: str,
        color: str | None = None,
    ) -> "ModelTag":
        """Create a system-defined tag."""
        return cls(
            name=name,
            namespace="onex",
            display_name=display_name,
            created_by="system",
            is_system=True,
            color=color,
        )

    # Factory methods for common tags
    @classmethod
    def core(cls) -> "ModelTag":
        """Core functionality tag."""
        return cls.create_system_tag("core", "Core", "#0066cc")

    @classmethod
    def plugin(cls) -> "ModelTag":
        """Plugin tag."""
        return cls.create_system_tag("plugin", "Plugin", "#9933cc")

    @classmethod
    def experimental(cls) -> "ModelTag":
        """Experimental feature tag."""
        return cls.create_system_tag("experimental", "Experimental", "#ff9900")

    @classmethod
    def deprecated(cls) -> "ModelTag":
        """Deprecated feature tag."""
        return cls.create_system_tag("deprecated", "Deprecated", "#cc0000")

    @classmethod
    def security(cls) -> "ModelTag":
        """Security-related tag."""
        return cls.create_system_tag("security", "Security", "#cc0000")

    @classmethod
    def performance(cls) -> "ModelTag":
        """Performance-related tag."""
        return cls.create_system_tag("performance", "Performance", "#00cc00")

    @classmethod
    def testing(cls) -> "ModelTag":
        """Testing-related tag."""
        return cls.create_system_tag("testing", "Testing", "#666666")

    @classmethod
    def documentation(cls) -> "ModelTag":
        """Documentation tag."""
        return cls.create_system_tag("documentation", "Documentation", "#0099cc")

    @classmethod
    def integration(cls) -> "ModelTag":
        """Integration tag."""
        return cls.create_system_tag("integration", "Integration", "#6600cc")

    @classmethod
    def utility(cls) -> "ModelTag":
        """Utility tag."""
        return cls.create_system_tag("utility", "Utility", "#999999")
