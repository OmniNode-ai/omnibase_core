# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
CLI Invocation Model — invocation specification for registry-driven CLI commands.

Part of the cli.contribution.v1 contract schema.

.. versionadded:: 0.19.0  (OMN-2536)
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_cli_invocation_type import EnumCliInvocationType
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError

__all__ = ["ModelCliInvocation"]


class ModelCliInvocation(BaseModel):
    """Invocation specification for a CLI command.

    Describes how the CLI runtime dispatches the command when it is executed.

    Attributes:
        invocation_type: Dispatch mechanism (kafka_event, direct_call, etc.).
        topic: Kafka topic for KAFKA_EVENT invocations. Required when
            invocation_type is KAFKA_EVENT.
        endpoint: HTTP endpoint for HTTP_ENDPOINT invocations.
        callable_ref: Fully qualified Python callable for DIRECT_CALL.
        subprocess_cmd: Shell command string for SUBPROCESS.
    """

    invocation_type: EnumCliInvocationType = Field(
        ...,
        description="Dispatch mechanism for this command.",
    )
    topic: str | None = Field(
        default=None,
        description="Kafka topic for KAFKA_EVENT dispatch.",
    )
    endpoint: str | None = Field(
        default=None,
        description="HTTP endpoint URL for HTTP_ENDPOINT dispatch.",
    )
    callable_ref: str | None = Field(
        default=None,
        description="Fully qualified Python callable ref for DIRECT_CALL.",
    )
    subprocess_cmd: str | None = Field(
        default=None,
        description="Shell command string for SUBPROCESS dispatch.",
    )

    @model_validator(mode="after")
    def validate_invocation_target(self) -> ModelCliInvocation:
        """Ensure the required target field is set for the chosen invocation type."""
        itype = self.invocation_type
        if itype == EnumCliInvocationType.KAFKA_EVENT and not self.topic:
            raise ModelOnexError(
                message="topic is required for KAFKA_EVENT invocation",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                invocation_type=itype,
            )
        if itype == EnumCliInvocationType.HTTP_ENDPOINT and not self.endpoint:
            raise ModelOnexError(
                message="endpoint is required for HTTP_ENDPOINT invocation",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                invocation_type=itype,
            )
        if itype == EnumCliInvocationType.DIRECT_CALL and not self.callable_ref:
            raise ModelOnexError(
                message="callable_ref is required for DIRECT_CALL invocation",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                invocation_type=itype,
            )
        if itype == EnumCliInvocationType.SUBPROCESS and not self.subprocess_cmd:
            raise ModelOnexError(
                message="subprocess_cmd is required for SUBPROCESS invocation",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                invocation_type=itype,
            )
        return self

    model_config = ConfigDict(
        extra="forbid",
        from_attributes=True,
        str_strip_whitespace=True,
    )
