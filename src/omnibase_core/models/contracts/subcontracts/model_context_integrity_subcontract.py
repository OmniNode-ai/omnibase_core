# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Context Integrity Subcontract Model.

Dedicated subcontract model for WISC (Write-Input-Scope-Control) enforcement
metadata on ONEX handlers. Defines context budget constraints, memory scope,
tool scope, retrieval sources, return schema, and enforcement level for
context integrity auditing.

This model is composed into handler contracts that require context integrity
enforcement, enabling audit hooks to validate that dispatched tasks operate
within declared constraints.

Strict typing is enforced: No Any types allowed in implementation.
"""

from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.contracts.subcontracts.model_retrieval_source import (
    ModelRetrievalSource,
)
from omnibase_core.models.contracts.subcontracts.model_return_schema import (
    ModelReturnSchema,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelContextIntegritySubcontract(BaseModel):
    """
    Context integrity subcontract for WISC enforcement metadata.

    Provides configuration for context budget constraints, memory scope,
    tool scope, retrieval sources, return schema, and enforcement level.
    Designed for composition into handler contracts requiring context
    integrity auditing across ONEX node types.

    This subcontract enables audit hooks to:
    - Validate dispatched tasks operate within declared context budgets
    - Restrict tool access to declared tool scopes
    - Limit memory/retrieval to declared sources
    - Enforce return payload schemas
    - Apply enforcement levels (permissive through paranoid)

    Strict typing is enforced: No Any types allowed in implementation.
    """

    # Interface version for code generation stability
    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version (MUST be provided in YAML contract)",
    )

    # Context budget constraints
    context_budget_tokens: int | None = Field(
        default=None,
        ge=1,
        description=(
            "Maximum token budget for context window usage. "
            "None means no explicit budget constraint."
        ),
    )

    # Memory scope
    memory_scope: list[str] = Field(
        default_factory=list,
        description=(
            "Allowed memory namespaces/scopes this handler can access. "
            "Empty list means no memory access restrictions."
        ),
    )

    # Tool scope
    tool_scope: list[str] = Field(
        default_factory=list,
        description=(
            "Allowed tool names/patterns this handler can invoke. "
            "Empty list means no tool access restrictions."
        ),
    )

    # Retrieval sources
    retrieval_sources: list[ModelRetrievalSource] = Field(
        default_factory=list,
        description=(
            "Allowed retrieval sources for context augmentation. "
            "Empty list means no retrieval restrictions."
        ),
    )

    # Return schema constraints
    return_schema: ModelReturnSchema | None = Field(
        default=None,
        description=(
            "Schema constraints for return payloads. "
            "None means no return schema enforcement."
        ),
    )

    # Enforcement level (string reference to EnumAuditEnforcementLevel)
    enforcement_level: str = Field(
        default="WARN",
        description=(
            "Enforcement level for context integrity violations: "
            "PERMISSIVE, WARN, STRICT, or PARANOID"
        ),
    )

    # Compression thresholds
    compression_threshold_tokens: int | None = Field(
        default=None,
        ge=1,
        description=(
            "Token threshold at which context compression should be triggered. "
            "None means no automatic compression."
        ),
    )

    compression_time_limit_seconds: float | None = Field(
        default=None,
        gt=0.0,
        description=(
            "Maximum time in seconds allowed for context compression. "
            "None means no time limit on compression."
        ),
    )

    @field_validator("enforcement_level")
    @classmethod
    def validate_enforcement_level(cls, v: str) -> str:
        """Validate enforcement level is one of allowed values."""
        allowed = ["PERMISSIVE", "WARN", "STRICT", "PARANOID"]
        v_upper = v.upper()
        if v_upper not in allowed:
            msg = f"enforcement_level must be one of {allowed}, got '{v}'"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                        "allowed_values": ModelSchemaValue.from_value(allowed),
                        "provided_value": ModelSchemaValue.from_value(v),
                    },
                ),
            )
        return v_upper

    model_config = ConfigDict(
        extra="ignore",  # Allow extra fields from YAML contracts
        use_enum_values=False,  # Keep enum objects, don't convert to strings
        validate_assignment=True,
    )


__all__ = [
    "ModelContextIntegritySubcontract",
]
