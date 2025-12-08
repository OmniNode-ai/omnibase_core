"""
Effect Subcontract Model - ONEX Standards Compliant.

VERSION: 1.0.0 - INTERFACE LOCKED FOR CODE GENERATION

Defines declarative effect operations with:
- Discriminated union IO configs (type-safe per handler)
- Idempotency-aware retry policies
- Process-local circuit breaker configuration
- DB-only transaction boundaries

Implements:
- OMN-524: ModelEffectOperation and supporting models
- OMN-525: ModelEffectSubcontract with validators
"""

from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer

from .model_effect_circuit_breaker import ModelEffectCircuitBreaker
from .model_effect_contract_metadata import ModelEffectContractMetadata
from .model_effect_input_schema import ModelEffectInputSchema
from .model_effect_observability import ModelEffectObservability
from .model_effect_operation import ModelEffectOperation
from .model_effect_retry_policy import ModelEffectRetryPolicy
from .model_effect_transaction_config import ModelEffectTransactionConfig

__all__ = ["ModelEffectSubcontract"]


class ModelEffectSubcontract(BaseModel):
    """
    Effect Subcontract - defines all I/O operations declaratively.

    VERSION: 1.0.0 - Sequential operations, abort-on-first-failure

    CRITICAL VALIDATIONS:
    1. Transaction enabled only for DB-only operations with same connection
    2. Retry enabled only for idempotent operations
    3. All IO configs validated against handler type
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # Interface version for code generation stability
    INTERFACE_VERSION: ModelSemVer = Field(
        default_factory=lambda: ModelSemVer(major=1, minor=0, patch=0)
    )

    # Contract metadata for tooling and RSD compatibility
    metadata: ModelEffectContractMetadata = Field(
        default_factory=ModelEffectContractMetadata
    )

    # Identity
    subcontract_name: str = Field(..., min_length=1, max_length=100)
    version: ModelSemVer = Field(
        default_factory=lambda: ModelSemVer(major=1, minor=0, patch=0)
    )
    description: str | None = Field(default=None, max_length=1000)

    # Execution semantics - EXPLICIT in contract
    execution_mode: Literal["sequential_abort", "sequential_continue"] = Field(
        default="sequential_abort",
        description=(
            "Controls failure handling behavior:\n\n"
            "**sequential_abort** (default):\n"
            "- Stop on first operation failure\n"
            "- RAISES ModelOnexError immediately\n"
            "- Partial ModelEffectOutput available in exception context\n"
            "- Use when atomicity matters: 'all succeed or fail fast'\n\n"
            "**sequential_continue**:\n"
            "- Run all operations regardless of failures\n"
            "- NEVER raises for operation failures\n"
            "- Returns complete ModelEffectOutput with all results\n"
            "- failed_operation and operation success flags indicate failures\n"
            "- Use for best-effort: 'run everything, report all outcomes'"
        ),
    )

    # Operations (sequential execution per execution_mode)
    operations: list[ModelEffectOperation] = Field(..., min_length=1, max_length=50)

    # Global resilience defaults
    default_retry_policy: ModelEffectRetryPolicy = Field(
        default_factory=ModelEffectRetryPolicy
    )
    default_circuit_breaker: ModelEffectCircuitBreaker = Field(
        default_factory=ModelEffectCircuitBreaker
    )
    transaction: ModelEffectTransactionConfig = Field(
        default_factory=ModelEffectTransactionConfig
    )

    # Observability
    observability: ModelEffectObservability = Field(
        default_factory=ModelEffectObservability
    )

    # Correlation
    correlation_id: UUID = Field(default_factory=uuid4)

    # Reserved: Input schema (v1.1 - validation not enforced in v1.0)
    input_schema: ModelEffectInputSchema | None = Field(
        default=None,
        description="Optional input schema. Reserved for v1.1 - structure only in v1.0.",
    )

    # Reserved: Determinism flag (important for RSD replay)
    deterministic: bool = Field(
        default=False,
        description=(
            "Indicates if effect is deterministic for same input. "
            "Non-deterministic effects (HTTP, time-sensitive queries) may not be safely replayable.\n\n"
            "**Runtime Consequences**:\n"
            "- deterministic=true: Effect results may be cached and replayed by ONEX infrastructure\n"
            "- deterministic=false: Effect is excluded from replay, snapshotting, and caching systems\n"
            "- Default false is conservative (safe)\n\n"
            "**Examples**:\n"
            "- HTTP GET with stable response: deterministic=true\n"
            "- HTTP POST creating resource: deterministic=false\n"
            "- DB SELECT on immutable table: deterministic=true\n"
            "- DB SELECT with NOW(): deterministic=false"
        ),
    )

    # Reserved for forward compatibility (v1.1+)
    future: dict[str, object] = Field(
        default_factory=dict,
        description=(
            "Reserved for ONEX-provided extensions. "
            "User-defined keys not supported in v1.0.\n\n"
            "**Namespace Rules**:\n"
            "- ONEX-owned keys MUST use `ONEX_` prefix\n"
            "- User-defined keys (v1.1+) will use no prefix or custom prefix\n"
            "- Collision prevention: ONEX will never use un-prefixed keys\n\n"
            "**Expected ONEX Extensions**:\n"
            "- `ONEX_response_cache_ttl_ms`: Response caching configuration\n"
            "- `ONEX_callgraph_annotation`: Dependency tracking metadata\n"
            "- `ONEX_replay_policy`: Replay and snapshot behavior hints"
        ),
    )

    @model_validator(mode="after")
    def validate_transaction_scope(self) -> "ModelEffectSubcontract":
        """
        Validate transaction is only enabled for DB operations with same connection.

        RULE: Transactions only make sense for:
        1. All operations are DB operations
        2. All operations use the same connection_name
        """
        if not self.transaction.enabled:
            return self

        # Check all operations are DB
        non_db_ops = [op for op in self.operations if op.handler_type != "db"]
        if non_db_ops:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Transaction enabled but found non-DB operations: {[op.operation_name for op in non_db_ops]}. "
                f"Transactions only supported for DB handler type.",
            )

        # Check all use same connection
        connection_names = {
            op.io_config.connection_name  # type: ignore[union-attr]
            for op in self.operations
        }
        if len(connection_names) > 1:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Transaction enabled but operations use different connections: {connection_names}. "
                f"All DB operations in a transaction must use the same connection.",
            )

        return self

    @model_validator(mode="after")
    def validate_idempotency_retry_interaction(self) -> "ModelEffectSubcontract":
        """
        Validate retry policies respect idempotency.

        RULE: Cannot retry non-idempotent operations.
        """
        for op in self.operations:
            # Get effective retry policy
            retry_policy = op.retry_policy or self.default_retry_policy

            if retry_policy.enabled and retry_policy.max_retries > 0:
                if not op.get_effective_idempotency():
                    raise ModelOnexError(
                        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                        message=f"Operation '{op.operation_name}' is not idempotent but has retry enabled. "
                        f"Set idempotent=true or disable retries to prevent duplicate side effects.",
                    )

        return self

    @model_validator(mode="after")
    def validate_select_retry_in_transaction(self) -> "ModelEffectSubcontract":
        """
        Prevent retrying SELECT inside transaction with snapshot-sensitive isolation.

        In PostgreSQL repeatable_read/serializable, the first SELECT defines the
        transaction's snapshot. Retrying a SELECT would NOT see changes made by
        concurrent transactions (expected in repeatable_read), but the retry loop
        resets internal state, potentially causing the application to behave as if
        the snapshot changed. This creates subtle consistency bugs.

        RULE: Cannot retry SELECT operations inside repeatable_read or serializable
        transactions. Either use read_committed (where retries are safe) or disable
        retry for SELECT operations.
        """
        if not self.transaction.enabled:
            return self

        isolation = self.transaction.isolation_level
        if isolation in ["read_uncommitted", "read_committed"]:
            return self  # Safe to retry - each query sees fresh data

        # Check for SELECT operations with retry enabled in strict isolation
        for op in self.operations:
            if op.handler_type == "db":
                if op.io_config.operation == "select":  # type: ignore[union-attr]
                    retry = op.retry_policy or self.default_retry_policy
                    if retry.enabled and retry.max_retries > 0:
                        raise ModelOnexError(
                            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                            message=f"Operation '{op.operation_name}' is a SELECT with retry enabled "
                            f"inside a {isolation} transaction. This violates snapshot semantics. "
                            f"Either disable retry for this operation or use read_committed isolation.",
                        )

        return self

    @model_validator(mode="after")
    def validate_no_raw_in_transaction(self) -> "ModelEffectSubcontract":
        """
        Disallow raw DB operations inside transactions.

        Raw operations (stored procedures, multi-statement batches) may have
        unpredictable side effects that break transactional semantics:
        - Stored procedures may issue their own COMMIT/ROLLBACK
        - Multi-statement batches may have partial failure modes
        - Side effects (temp tables, session variables) may leak across transaction boundaries

        Route complex transactional logic through dedicated patterns:
        - Use individual operations (select/insert/update/delete/upsert) instead
        - Decompose stored procedures into discrete, observable steps
        - Use application-level orchestration for complex multi-step logic
        """
        if not self.transaction.enabled:
            return self

        raw_ops = [
            op
            for op in self.operations
            if op.handler_type == "db" and op.io_config.operation == "raw"  # type: ignore[union-attr]
        ]

        if raw_ops:
            raw_names = [op.operation_name for op in raw_ops]
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Raw DB operations not allowed inside transactions: {raw_names}. "
                f"Raw operations (stored procedures, multi-statement batches) may have "
                f"side effects that break transactional semantics. "
                f"Use dedicated subcontracts or explicit application logic instead.",
            )

        return self
