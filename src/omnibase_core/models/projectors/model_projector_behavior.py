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

import logging
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.models.projectors.model_idempotency_config import (
    ModelIdempotencyConfig,
)

_logger = logging.getLogger(__name__)


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

    Note:
        **Why from_attributes=True is Required**

        This model uses ``from_attributes=True`` in its ConfigDict to ensure
        pytest-xdist compatibility. When running tests with pytest-xdist,
        each worker process imports the class independently, creating separate
        class objects. The ``from_attributes=True`` flag enables Pydantic's
        "duck typing" mode, allowing fixtures from one worker to be validated
        in another.

        **Thread Safety**: This model is frozen (immutable) after creation,
        making it thread-safe for concurrent read access.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    mode: Literal["upsert", "insert_only", "append"] = Field(
        default="upsert",
        description="Projection mode: upsert, insert_only, or append",
    )

    upsert_key: str | None = Field(
        default=None,
        description=(
            "Column to use for upsert conflict detection. "
            "Only applicable when mode='upsert'. "
            "If None, defaults to the schema's primary_key (a warning is logged). "
            "Ignored when mode='insert_only' or 'append'."
        ),
    )

    idempotency: ModelIdempotencyConfig | None = Field(
        default=None,
        description="Idempotency configuration for exactly-once processing",
    )

    @model_validator(mode="after")
    def validate_upsert_key_for_mode(self) -> Self:
        """Validate that upsert_key is provided when mode is 'upsert'.

        When mode is 'upsert' and upsert_key is not specified, a warning is
        emitted to inform the user that the schema's primary key will be used
        as the default upsert key. This is informational only - the default
        behavior is valid and functional.

        Returns:
            Self: The validated model instance.
        """
        if self.mode == "upsert" and self.upsert_key is None:
            _logger.warning(
                "upsert_key not specified for mode='upsert'. "
                "Primary key will be used as the upsert key by default."
            )
        return self

    def __repr__(self) -> str:
        """Return a concise representation for debugging.

        Returns:
            String representation showing mode and upsert_key.

        Examples:
            >>> behavior = ModelProjectorBehavior(mode="upsert", upsert_key="node_id")
            >>> repr(behavior)
            "ModelProjectorBehavior(mode='upsert', upsert_key='node_id')"
        """
        return f"ModelProjectorBehavior(mode={self.mode!r}, upsert_key={self.upsert_key!r})"


__all__ = ["ModelProjectorBehavior"]
