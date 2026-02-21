# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Performance Requirements Model.

Performance SLA specifications for contract-driven behavior providing:
- Measurable performance targets and resource constraints
- Runtime validation and optimization specifications
- Single operation and batch operation timing requirements
- Memory and CPU usage limits with validation
- Explicit timeout configuration for database, external service, and projection reader operations

Strict typing is enforced: No Any types allowed in implementation.
"""

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ModelPerformanceRequirements(BaseModel):
    """
    Performance SLA specifications for contract-driven behavior.

    Defines measurable performance targets and resource constraints
    for runtime validation and optimization, including explicit timeout
    configuration fields that enable contract-driven timeout behavior
    across the ONEX ecosystem.

    Timeout fields (OMN-1548):
        database_query_timeout_ms: Timeout for individual database queries. Must be
            <= single_operation_max_ms when both are set.
        external_service_timeout_ms: Timeout for external service calls (APIs, etc.).
        projection_reader_timeout_ms: Timeout for projection reader operations.
        circuit_breaker_recovery_timeout_s: Circuit breaker recovery timeout in seconds.

    Constraint tension — single_operation_max_ms vs database_query_timeout_ms:
        single_operation_max_ms has a minimum of 1ms (ge=1), while
        database_query_timeout_ms has a minimum of 100ms (ge=100). When
        single_operation_max_ms is set to any value in [1, 99], it becomes
        impossible to also set database_query_timeout_ms because the smallest
        valid value for that field (100ms) already exceeds the SLA. Any attempt
        to assign database_query_timeout_ms in that state will raise a
        ValidationError from the cross-field validator. This is intentional: a
        sub-100ms single-operation SLA implies database queries are not expected
        to be performed within the same operation boundary.
    """

    single_operation_max_ms: int | None = Field(
        default=None,
        description="Maximum execution time for single operation in milliseconds",
        ge=1,
    )

    batch_operation_max_s: int | None = Field(
        default=None,
        description="Maximum execution time for batch operations in seconds",
        ge=1,
    )

    memory_limit_mb: int | None = Field(
        default=None,
        description="Maximum memory usage in megabytes",
        ge=1,
    )

    cpu_limit_percent: int | None = Field(
        default=None,
        description="Maximum CPU usage percentage",
        ge=1,
        le=100,
    )

    throughput_min_ops_per_second: float | None = Field(
        default=None,
        description="Minimum throughput in operations per second",
        ge=0.0,
    )

    database_query_timeout_ms: int | None = Field(
        default=None,
        description="Timeout for individual database queries in milliseconds",
        ge=100,
    )

    external_service_timeout_ms: int | None = Field(
        default=None,
        description="Timeout for external service calls (APIs, etc.) in milliseconds",
        ge=100,
    )

    projection_reader_timeout_ms: int | None = Field(
        default=None,
        description="Timeout for projection reader operations in milliseconds",
        ge=100,
    )

    circuit_breaker_recovery_timeout_s: int | None = Field(
        default=None,
        description="Circuit breaker recovery timeout in seconds",
        ge=1,
    )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    @model_validator(mode="after")
    def validate_timeout_vs_operation_sla(self) -> Self:
        """Validate that database_query_timeout_ms does not exceed single_operation_max_ms.

        When both fields are set, the database query timeout must be less than or
        equal to the single operation SLA to ensure consistent behavior between
        declared SLA and actual timeout enforcement.
        """
        if (
            self.database_query_timeout_ms is not None
            and self.single_operation_max_ms is not None
            and self.database_query_timeout_ms > self.single_operation_max_ms
        ):
            raise ValueError(
                f"database_query_timeout_ms ({self.database_query_timeout_ms}) "
                f"must be <= single_operation_max_ms ({self.single_operation_max_ms})"
            )
        return self
