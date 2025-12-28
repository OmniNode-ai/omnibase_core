"""
Projection Watermark Model - Tracks materialization progress for projections.

Watermarks enable lag detection and ensure eventually consistent reads in
event-driven projection materialization.

Version: 1.0.0
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.constants.constants_field_limits import MAX_IDENTIFIER_LENGTH


class ModelProjectionWatermark(BaseModel):
    """
    Projection materialization watermark for eventual consistency tracking.

    Watermarks track the progress of projection materialization from event streams.
    They enable:
    - Lag detection (current offset vs watermark offset)
    - Version gating (wait until projection reaches required version)
    - Health monitoring (projection staleness alerts)

    Core Concepts:
    - **partition_key**: Event stream partition (Kafka partition, shard ID, etc.)
    - **offset**: Last successfully processed event offset
    - **updated_at**: Timestamp of last watermark update (for lag calculation)

    Usage Pattern:
        1. Materializer processes StateCommitted event at offset N
        2. Materializer upserts projection + watermark atomically:
           ```sql
           BEGIN;
             -- Update projection
             UPSERT INTO workflow_projection ...;
             -- Update watermark
             UPDATE watermarks SET offset = GREATEST(offset, N);
           COMMIT;
           ```
        3. Projection Store checks watermark before reads:
           ```python
           watermark = await get_watermark(partition_key)
           if required_offset > watermark.offset:
               # Projection lagging, fallback or wait
           ```

    Example:
        ```python
        # Check projection lag
        watermark = await db.fetchrow(
            "SELECT * FROM projection_watermarks WHERE partition_key = $1",
            partition_key
        )
        lag_ms = (datetime.now(UTC) - watermark.updated_at).total_seconds() * 1000

        if lag_ms > 250:  # SLA threshold
            logger.warning(f"Projection lag: {lag_ms}ms on partition {partition_key}")
        ```

    ONEX v2.0 Compliance:
    - Suffix-based naming: ModelProjectionWatermark
    - Pydantic v2 with ConfigDict
    - Concrete model (not abstract - same across all backends)
    """

    model_config = ConfigDict(
        validate_assignment=True,
        str_strip_whitespace=True,
        use_enum_values=False,
        populate_by_name=True,
    )

    partition_key: str = Field(
        ...,
        description="Event stream partition identifier (Kafka partition, shard ID, etc.)",
        min_length=1,
        max_length=MAX_IDENTIFIER_LENGTH,
    )

    offset: int = Field(
        ...,
        description="Last successfully processed event offset",
        ge=0,
    )

    updated_at: datetime = Field(
        ...,
        description="Timestamp of last watermark update (for lag calculation)",
    )

    def calculate_lag_ms(self, now: datetime) -> float:
        """
        Calculate projection lag in milliseconds.

        Args:
            now: Current timestamp (usually datetime.now(UTC))

        Returns:
            Lag in milliseconds
        """
        return (now - self.updated_at).total_seconds() * 1000

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"ModelProjectionWatermark(partition_key={self.partition_key!r}, offset={self.offset}, updated_at={self.updated_at})"
