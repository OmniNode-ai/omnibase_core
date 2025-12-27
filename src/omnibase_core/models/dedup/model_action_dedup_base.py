"""
Action Deduplication Base Model - Abstract base for idempotent action processing.

This abstract base class defines the interface for action deduplication
in at-least-once delivery systems.

Version: 1.0.0
"""

from typing import ClassVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.constants.constants_field_limits import MAX_NAME_LENGTH
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors import OnexError


class ModelActionDedupBase(BaseModel):
    """
    Abstract base class for action deduplication with TTL-based expiration.

    Prevents duplicate processing of actions in at-least-once delivery systems
    (Kafka, SQS, etc.). Uses composite key (key + action_id) for uniqueness and
    TTL-based expiration for automatic cleanup.

    Core Concepts:
    - **key**: Entity identifier (workflow_key, entity_id, etc.)
    - **action_id**: Unique action UUID (idempotency key)
    - **result_hash**: SHA256 hash of action result (for validation on replay)

    Usage Pattern:
        1. Before processing: Check if action already processed
           ```python
           if await dedup.exists(key, action_id):
               return  # Already processed, skip
           ```
        2. After processing: Record action + result hash
           ```python
           result_hash = hashlib.sha256(
               json.dumps(result, sort_keys=True).encode()
           ).hexdigest()
           await dedup.remember(key, action_id, result_hash)
           ```
        3. Cleanup: Periodic deletion of expired entries
           ```python
           await db.execute(
               "DELETE FROM action_dedup WHERE expires_at < NOW()"
           )
           ```

    Example:
        ```python
        # Concrete implementation in omnibase_infra
        class ModelActionDedup(ModelActionDedupBase):
            processed_at: datetime
            expires_at: datetime

            @classmethod
            def create_with_ttl(
                cls,
                key: str,
                action_id: UUID,
                result_hash: str,
                ttl_hours: int = 6
            ):
                now = datetime.now(UTC)
                return cls(
                    key=key,
                    action_id=action_id,
                    result_hash=result_hash,
                    processed_at=now,
                    expires_at=now + timedelta(hours=ttl_hours)
                )
        ```

    ONEX v2.0 Compliance:
    - Suffix-based naming: ModelActionDedupBase
    - Pydantic v2 with ConfigDict
    - Abstract pattern (implementations add timestamp/TTL fields)
    """

    model_config = ConfigDict(
        validate_assignment=True,
        str_strip_whitespace=True,
        use_enum_values=False,
        populate_by_name=True,
    )

    DEFAULT_TTL_HOURS: ClassVar[int] = 6
    """Default TTL for deduplication entries (6 hours)."""

    key: str = Field(
        ...,
        description="Entity identifier (workflow_key, entity_id, etc.)",
        min_length=1,
        max_length=MAX_NAME_LENGTH,
    )

    action_id: UUID = Field(
        ...,
        description="Unique action identifier for idempotency",
    )

    result_hash: str = Field(
        ...,
        description="SHA256 hash of action result (for validation on replay)",
        min_length=64,
        max_length=64,
    )

    @field_validator("result_hash")
    @classmethod
    def normalize_hash(cls, v: str) -> str:
        """Normalize hash to lowercase for consistency."""
        if not all(c in "0123456789abcdefABCDEF" for c in v):
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="result_hash must be a valid SHA256 hexadecimal string",
            )
        return v.lower()

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"ModelActionDedupBase(key={self.key!r}, action_id={self.action_id}, result_hash={self.result_hash[:8]}...)"
