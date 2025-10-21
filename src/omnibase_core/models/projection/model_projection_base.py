"""
Projection Base Model - Abstract base for read-optimized state projections.

This abstract base class defines the interface for projection state management
in CQRS architectures with eventual consistency guarantees.

Author: ONEX Framework Team
Version: 1.0.0
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ModelProjectionBase(BaseModel):
    """
    Abstract base class for read-optimized projections.

    Projections are materialized views of canonical state, optimized for read
    operations. They support eventual consistency via watermark tracking and
    provide fallback to canonical state when projection lag exceeds thresholds.

    Core Concepts:
    - **key**: Maps to canonical state key
    - **version**: Matches canonical state version when up-to-date
    - Concrete implementations add domain-specific indexed fields

    Usage Pattern:
        1. Projection Materializer subscribes to StateCommitted events
        2. Materializer upserts projection with domain-specific fields
        3. Projection Store reads with version gating or fallback to canonical

    Example:
        ```python
        # Concrete implementation in omninode_bridge
        class ModelWorkflowProjection(ModelProjectionBase):
            tag: str  # PENDING, PROCESSING, COMPLETED (indexed)
            namespace: str  # Multi-tenant isolation (indexed)
            updated_at: datetime
            indices: Optional[dict[str, Any]]

        # Usage in projection store
        projection = await proj_store.get_state(
            key=workflow_key,
            required_version=5,  # Wait until projection reaches v5
            max_wait_ms=100
        )
        if projection is None:
            # Projection lagging, fallback to canonical
            canonical = await canonical_store.get_state(key)
        ```

    ONEX v2.0 Compliance:
    - Suffix-based naming: ModelProjectionBase
    - Pydantic v2 with ConfigDict
    - Abstract pattern (domain-specific fields in implementations)
    """

    model_config = ConfigDict(
        validate_assignment=True,
        str_strip_whitespace=True,
        use_enum_values=False,
        populate_by_name=True,
    )

    key: str = Field(
        ...,
        description="Unique identifier matching canonical state key",
        min_length=1,
        max_length=255,
    )

    version: int = Field(
        ...,
        description="Version number matching canonical state (for consistency checks)",
        ge=1,
    )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"ModelProjectionBase(key={self.key!r}, version={self.version})"
