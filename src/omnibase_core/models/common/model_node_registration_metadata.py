"""Node registration runtime metadata model.

This module provides strongly-typed metadata for node registration at runtime.
Separate from ModelNodeCapabilitiesMetadata (authorship/docs) - this is for
environment-specific, deployment-specific, mutable data captured during
node registration.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.enums.enum_environment import EnumEnvironment

# Pre-compiled pattern for k8s-style label key validation
# Simplified pattern: lowercase alphanumeric, hyphens, dots allowed
_LABEL_KEY_PATTERN = re.compile(
    r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?(\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*$"
)


class ModelNodeRegistrationMetadata(BaseModel):
    """Runtime/deployment metadata for node registration.

    Separate from ModelNodeCapabilitiesMetadata (authorship/docs).
    This is environment-specific, deployment-specific, mutable data
    captured during node registration.

    Attributes:
        environment: Deployment environment (dev, staging, prod, etc.)
        tags: Categorization tags (bounded list, normalized lowercase)
        labels: Kubernetes-style labels (str -> str, validated keys)
        release_channel: Optional release channel (stable, canary, beta)
        region: Optional deployment region (us-east-1, eu-west-1, etc.)
    """

    # frozen=True ensures immutability after creation
    # extra="forbid" rejects unknown fields
    # from_attributes=True allows Pydantic to accept objects with matching
    # attributes even when class identity differs (e.g., in pytest-xdist
    # parallel execution where model classes are imported in separate workers).
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    environment: EnumEnvironment = Field(
        ...,
        description="Deployment environment",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Categorization tags (max 20)",
        max_length=20,
    )
    labels: dict[str, str] = Field(
        default_factory=dict,
        description="Kubernetes-style labels (validated keys, max 50)",
    )
    release_channel: str | None = Field(
        default=None,
        description="Release channel (e.g., stable, canary, beta)",
    )
    region: str | None = Field(
        default=None,
        description="Deployment region (e.g., us-east-1)",
    )

    @field_validator("tags", mode="before")
    @classmethod
    def normalize_tags(cls, v: list[str] | None) -> list[str]:
        """Normalize tags to lowercase and deduplicate.

        Args:
            v: List of tag strings or None

        Returns:
            Deduplicated, lowercase, stripped tags
        """
        if not v:
            return []
        # Use dict.fromkeys for order-preserving deduplication
        return list(dict.fromkeys(tag.lower().strip() for tag in v if tag.strip()))

    @field_validator("labels", mode="before")
    @classmethod
    def validate_labels(cls, v: dict[str, str] | None) -> dict[str, str]:
        """Validate label keys follow k8s naming conventions.

        Args:
            v: Dictionary of label key-value pairs or None

        Returns:
            Validated and normalized labels dict

        Raises:
            ValueError: If more than 50 labels or invalid key format
        """
        if not v:
            return {}
        if len(v) > 50:
            # error-ok: Pydantic validator requires ValueError
            raise ValueError("Maximum 50 labels allowed")
        # Validate key format (simplified k8s pattern)
        for key in v:
            if not _LABEL_KEY_PATTERN.match(key.lower()):
                # error-ok: Pydantic validator requires ValueError
                raise ValueError(
                    f"Invalid label key format: '{key}'. "
                    f"Label keys must match pattern: {_LABEL_KEY_PATTERN.pattern} "
                    "(lowercase alphanumeric, hyphens, dots allowed)"
                )
        return {k.lower(): str(val) for k, val in v.items()}


__all__ = ["ModelNodeRegistrationMetadata"]
