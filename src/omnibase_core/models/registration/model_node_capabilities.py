# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Node Capabilities Model.

ModelNodeCapabilities for strongly-typed node capabilities
in the ONEX 2-way registration pattern.

Note:
    This model does NOT use MixinDictLikeAccessors because it requires custom
    logic to differentiate between known model fields (model_fields) and custom
    capabilities stored in model_extra. The mixin's simple hasattr/getattr pattern
    would not correctly handle this distinction.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.core.model_feature_flags import ModelFeatureFlags
from omnibase_core.models.registration.model_mcp_contract_config import (
    ModelMCPContractConfig,
)
from omnibase_core.types import JsonType


class ModelNodeCapabilities(BaseModel):
    """Strongly-typed node capabilities model.

    Uses explicit capability fields instead of generic dictionaries.
    Uses extra="allow" to support custom capabilities while
    providing type safety for known fields.

    Known capability fields are typed explicitly. Additional custom
    capabilities can be added via the extra="allow" config, and they
    will be stored as model extra fields accessible via model_extra.

    Attributes:
        postgres: Whether node has PostgreSQL capability.
        read: Whether node has read capability.
        write: Whether node has write capability.
        database: Whether node has generic database capability.
        processing: Whether node has processing capability.
        batch_size: Optional batch size limit.
        max_batch: Optional maximum batch size.
        supported_types: List of supported data types.
        routing: Whether node has routing capability.
        config: Nested configuration dictionary (JSON-serializable values only).
        transactions: Whether node supports transactions.
        feature: Generic feature flag.

    Example:
        >>> caps = ModelNodeCapabilities(
        ...     postgres=True,
        ...     read=True,
        ...     write=True,
        ... )
        >>> caps.postgres
        True

        >>> # Custom capabilities via extra="allow"
        >>> caps = ModelNodeCapabilities(
        ...     custom_capability=True,  # type: ignore[call-arg]
        ...     another_field="value",  # type: ignore[call-arg]
        ... )
        >>> caps.model_extra["custom_capability"]
        True
    """

    model_config = ConfigDict(
        extra="allow",  # Accept additional fields not explicitly defined
        frozen=False,  # Allow updates (ModelNodeRegistration is mutable)
        from_attributes=True,
    )

    # Database capabilities
    postgres: bool = Field(default=False, description="PostgreSQL capability")
    read: bool = Field(default=False, description="Read capability")
    write: bool = Field(default=False, description="Write capability")
    database: bool = Field(default=False, description="Generic database capability")
    transactions: bool = Field(default=False, description="Transaction support")

    # Processing capabilities
    processing: bool = Field(default=False, description="Processing capability")
    batch_size: int | None = Field(default=None, description="Batch size limit")
    max_batch: int | None = Field(default=None, description="Maximum batch size")
    supported_types: list[str] = Field(
        default_factory=list, description="Supported data types"
    )

    # Network capabilities
    routing: bool = Field(default=False, description="Routing capability")

    # Generic feature flag (used in tests)
    feature: bool = Field(default=False, description="Generic feature flag")

    # Configuration (nested) - uses JsonType for JSON-serializable values.
    # Supports primitives (str, int, float, bool, None), lists, and nested dicts.
    config: dict[str, JsonType] = Field(
        default_factory=dict,
        description="Nested configuration (JSON-serializable values)",
    )

    # Contract-declared feature flags with current state
    feature_flags: ModelFeatureFlags = Field(
        default_factory=ModelFeatureFlags,
        description="Contract-declared feature flags with current state",
    )

    # MCP configuration for exposing node as AI agent tool
    # Only valid for ORCHESTRATOR nodes - ignored for other node types
    mcp: ModelMCPContractConfig | None = Field(
        default=None,
        description="MCP configuration for exposing node as AI agent tool. "
        "Only valid for ORCHESTRATOR_GENERIC nodes.",
    )

    def __getitem__(self, key: str) -> object:
        """Enable dict-like access to capabilities.

        Args:
            key: The capability name to retrieve.

        Returns:
            The capability value (from known field or model_extra).

        Raises:
            KeyError: If key is not found in known fields or model_extra.

        Example:
            >>> caps = ModelNodeCapabilities(postgres=True, custom=42)
            >>> caps["postgres"]
            True
            >>> caps["custom"]  # Custom capability from model_extra
            42
        """
        if key in type(self).model_fields:
            return getattr(self, key)
        extra = self.model_extra or {}
        if key in extra:
            return extra[key]
        raise KeyError(key)

    def __contains__(self, key: object) -> bool:
        """Enable membership testing for capabilities.

        Returns True if key is a known field OR exists in model_extra.

        Args:
            key: The capability name to check.

        Returns:
            True if the key exists as a known field or in model_extra.

        Example:
            >>> caps = ModelNodeCapabilities(postgres=True, custom=42)
            >>> "postgres" in caps
            True
            >>> "custom" in caps  # Custom capability in model_extra
            True
            >>> "unknown" in caps
            False
        """
        if not isinstance(key, str):
            return False

        # Check known fields first (access via class to avoid deprecation)
        if key in type(self).model_fields:
            return True

        # Check model_extra for custom capabilities
        return bool(self.model_extra and key in self.model_extra)

    def get(self, key: str, default: object = None) -> object:
        """Safely get a capability value with optional default.

        Args:
            key: The capability name to retrieve.
            default: Value to return if key is not found (defaults to None).

        Returns:
            The capability value if found, otherwise the default value.

        Example:
            >>> caps = ModelNodeCapabilities(postgres=True)
            >>> caps.get("postgres")
            True
            >>> caps.get("unknown", False)
            False
            >>> caps.get("unknown")  # Returns None by default
        """
        try:
            return self[key]
        except KeyError:
            return default


__all__ = [
    "ModelNodeCapabilities",
]
