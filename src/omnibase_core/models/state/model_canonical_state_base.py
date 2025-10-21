"""
Canonical State Base Model - Abstract base for version-controlled state storage.

This abstract base class defines the interface for canonical state management
in the pure reducer pattern. Implementations provide concrete storage backends
(PostgreSQL, Redis, DynamoDB, etc.).

Author: ONEX Framework Team
Version: 1.0.0
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ModelCanonicalStateBase(BaseModel):
    """
    Abstract base class for canonical state storage with optimistic concurrency control.

    This model defines the core interface for version-controlled state management
    in event-driven reducer architectures. Concrete implementations in infrastructure
    layers (e.g., omnibase_infra) extend this with backend-specific fields.

    Core Concepts:
    - **key**: Unique identifier for the state entity
    - **version**: Optimistic concurrency control via monotonically increasing version
    - **state**: The actual state data (flexible JSONB-style storage)

    Usage Pattern:
        1. Read state with current version
        2. Apply pure reducer function: (state, action) → new_state
        3. Attempt commit with expected_version check
        4. Handle conflicts with retry + backoff

    Example:
        ```python
        # Concrete implementation in omnibase_infra
        class ModelCanonicalState(ModelCanonicalStateBase):
            updated_at: datetime
            schema_version: int
            provenance: dict[str, Any]

        # Usage in reducer service
        current = await store.get_state(key)
        result = await reducer.process(current.state, action)
        await store.try_commit(
            key=key,
            expected_version=current.version,
            state_prime=result.state
        )
        ```

    ONEX v2.0 Compliance:
    - Suffix-based naming: ModelCanonicalStateBase
    - Pydantic v2 with ConfigDict
    - Abstract pattern (no concrete backend specifics)
    """

    model_config = ConfigDict(
        validate_assignment=True,
        str_strip_whitespace=True,
        use_enum_values=False,
        populate_by_name=True,
    )

    key: str = Field(
        ...,
        description="Unique identifier for the state entity (workflow_key, entity_id, etc.)",
        min_length=1,
        max_length=255,
    )

    version: int = Field(
        ...,
        description="Monotonically increasing version number for optimistic concurrency control",
        ge=1,
    )

    state: dict[str, Any] = Field(
        ...,
        description="The actual state data (flexible structure, JSONB-style)",
        min_length=1,
    )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"ModelCanonicalStateBase(key={self.key!r}, version={self.version}, state_keys={list(self.state.keys())})"
