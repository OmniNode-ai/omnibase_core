"""
Lightweight violation record for event serialization.

This module provides a simplified, immutable representation of a validation
violation suitable for event streaming and Kafka serialization.

Location:
    ``omnibase_core.models.events.validation.model_violation_record``

Import Example:
    .. code-block:: python

        from omnibase_core.models.events.validation import ModelViolationRecord

.. versionadded:: 0.13.0
    Initial implementation as part of OMN-1776 cross-repo orchestrator.
"""

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelViolationRecord"]


class ModelViolationRecord(BaseModel):
    """
    Lightweight frozen violation record for event serialization.

    This is a simplified, immutable representation of a validation violation
    suitable for event streaming and Kafka serialization.

    Attributes:
        severity: Severity level of the violation.
        message: Human-readable violation description.
        code: Machine-readable error code.
        file_path: Path to file where violation was found (as string).
        line_number: Line number where violation was found.
        rule_name: Name of validation rule that triggered this violation.
        fingerprint: Unique fingerprint for baseline matching.

    .. versionadded:: 0.13.0
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    severity: str = Field(
        ...,
        description="Severity level of the violation (as string for serialization).",
    )

    message: str = Field(
        ...,
        description="Human-readable violation description.",
    )

    code: str | None = Field(
        default=None,
        description="Machine-readable error code.",
    )

    file_path: str | None = Field(
        default=None,
        description="Path to file where violation was found (as string).",
    )

    line_number: int | None = Field(
        default=None,
        description="Line number where violation was found.",
    )

    rule_name: str | None = Field(
        default=None,
        description="Name of validation rule that triggered this violation.",
    )

    fingerprint: str | None = Field(
        default=None,
        description="Unique fingerprint for baseline matching.",
    )

    suppressed: bool = Field(
        default=False,
        description="Whether this violation is suppressed by baseline.",
    )
