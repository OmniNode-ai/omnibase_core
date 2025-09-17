"""
Instance Metadata Model

Additional metadata for node instances including deployment information,
version details, and custom attributes.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_semver import ModelSemVer


class ModelInstanceMetadata(BaseModel):
    """
    Additional metadata for node instances.

    This model provides deployment information, version details,
    and custom attributes for node instances.
    """

    deployment_id: str | None = Field(
        None,
        description="Deployment identifier",
        pattern="^[a-z][a-z0-9-]*$",
    )

    deployment_environment: str = Field(
        default="development",
        description="Deployment environment",
        pattern="^[a-z][a-z0-9-]*$",
    )

    deployment_region: str | None = Field(
        None,
        description="Deployment region or zone",
        pattern="^[a-z][a-z0-9-]*$",
    )

    node_version: ModelSemVer = Field(
        default_factory=lambda: ModelSemVer(major=1, minor=0, patch=0),
        description="Node software version",
    )

    runtime_version: str | None = Field(
        None,
        description="Runtime version (e.g., Python 3.9.0)",
    )

    host_info: dict[str, str] = Field(
        default_factory=dict,
        description="Host information (OS, kernel, etc.)",
    )

    labels: dict[str, str] = Field(
        default_factory=dict,
        description="Custom labels for categorization",
    )

    annotations: dict[str, str] = Field(
        default_factory=dict,
        description="Custom annotations",
    )

    tags: list[str] = Field(
        default_factory=list,
        description="Tags for filtering and grouping",
    )

    owner: str | None = Field(None, description="Owner or team responsible")

    cost_center: str | None = Field(None, description="Cost center for billing")

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Instance creation timestamp",
    )

    last_updated: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last metadata update timestamp",
    )

    maintenance_window: str | None = Field(
        None,
        description="Maintenance window specification",
    )

    sla_tier: str | None = Field(
        None,
        description="SLA tier (e.g., gold, silver, bronze)",
    )

    custom_attributes: dict[str, str] = Field(
        default_factory=dict,
        description="Additional custom attributes",
    )

    def add_label(self, key: str, value: str) -> None:
        """Add or update a label."""
        self.labels[key] = value

    def add_annotation(self, key: str, value: str) -> None:
        """Add or update an annotation."""
        self.annotations[key] = value

    def add_tag(self, tag: str) -> None:
        """Add a tag if not already present."""
        if tag not in self.tags:
            self.tags.append(tag)

    def has_label(self, key: str, value: str | None = None) -> bool:
        """
        Check if instance has a label.

        Args:
            key: Label key to check
            value: Optional value to match

        Returns:
            True if label exists (and matches value if provided)
        """
        if key not in self.labels:
            return False
        if value is None:
            return True
        return self.labels[key] == value

    def has_tag(self, tag: str) -> bool:
        """Check if instance has a tag."""
        return tag in self.tags

    def matches_selector(self, selector: dict[str, str]) -> bool:
        """
        Check if instance matches label selector.

        Args:
            selector: Label selector dictionary

        Returns:
            True if all selector labels match
        """
        return all(self.has_label(key, value) for key, value in selector.items())
