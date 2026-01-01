# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Projector Behavior Configuration Model.

Provides configuration for how a projector handles data during projection.
The behavior determines whether records are upserted, inserted, or appended.

Mode Options:
    - ``upsert``: Insert new records or update existing ones based on upsert_key
    - ``insert_only``: Only insert new records, skip if key exists
    - ``append``: Always append records (no deduplication)

Example Usage:
    >>> from omnibase_core.models.projectors import ModelProjectorBehavior
    >>>
    >>> # Default upsert behavior
    >>> behavior = ModelProjectorBehavior()
    >>> behavior.mode
    'upsert'
    >>>
    >>> # Upsert with specific key
    >>> behavior = ModelProjectorBehavior(mode="upsert", upsert_key="node_id")
    >>> behavior.upsert_key
    'node_id'
    >>>
    >>> # Append mode (e.g., for event logs)
    >>> behavior = ModelProjectorBehavior(mode="append")
    >>> behavior.mode
    'append'

Thread Safety:
    This model is immutable (frozen=True) after creation, making it
    thread-safe for concurrent read access.

.. versionadded:: 0.4.0
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.projectors.model_idempotency_config import (
    ModelIdempotencyConfig,
)


class ModelProjectorBehavior(BaseModel):
    """
    Projection behavior configuration.

    Determines how the projector handles data during projection operations.
    The mode controls insert/update semantics while idempotency configuration
    enables exactly-once processing guarantees.

    Attributes:
        mode: The projection mode. Options are:
            - "upsert": Insert or update based on upsert_key (default)
            - "insert_only": Insert only, skip existing records
            - "append": Always append without deduplication
        upsert_key: The field to use for upsert conflict detection.
            Required when mode is "upsert" and you want to update
            existing records. Typically a primary key or unique identifier.
        idempotency: Optional idempotency configuration for exactly-once
            processing. When enabled, tracks processed events to prevent
            duplicate processing on retries or replay.

    Examples:
        Default upsert behavior:

        >>> behavior = ModelProjectorBehavior()
        >>> behavior.mode
        'upsert'

        Upsert with node_id as conflict key:

        >>> behavior = ModelProjectorBehavior(mode="upsert", upsert_key="node_id")
        >>> behavior.upsert_key
        'node_id'

        Append mode for event logs:

        >>> behavior = ModelProjectorBehavior(mode="append")
        >>> behavior.mode
        'append'

        With idempotency enabled:

        >>> from omnibase_core.models.projectors import ModelIdempotencyConfig
        >>> idempotency = ModelIdempotencyConfig(enabled=True, key="event_id")
        >>> behavior = ModelProjectorBehavior(mode="upsert", idempotency=idempotency)
        >>> behavior.idempotency.enabled
        True
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    mode: Literal["upsert", "insert_only", "append"] = Field(
        default="upsert",
        description="Projection mode: upsert, insert_only, or append",
    )

    upsert_key: str | None = Field(
        default=None,
        description="Field to use for upsert conflict detection",
    )

    idempotency: ModelIdempotencyConfig | None = Field(
        default=None,
        description="Idempotency configuration for exactly-once processing",
    )


__all__ = ["ModelProjectorBehavior"]
