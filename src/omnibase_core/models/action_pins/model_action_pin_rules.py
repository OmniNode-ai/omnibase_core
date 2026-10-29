# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The rule data of the action-pin check, read from its validation contract (OMN-21518)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelActionPinRules"]


class ModelActionPinRules(BaseModel):
    """Patterns, workflow-file filter, remediation texts and message templates.

    Every field is a ``parameters`` entry of a row of
    ``validation/contracts/action_pin.validation.yaml``; the handler holds none.
    Message templates take ``location``, ``value``, ``reason``, ``uses`` and
    ``tag_pattern`` as named fields.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    report_validator_name: str = Field(min_length=1)
    workflow_dir: str = Field(min_length=1)
    workflow_suffixes: tuple[str, ...] = Field(min_length=1)
    local_prefixes: tuple[str, ...] = Field(min_length=1)
    block_uses_pattern: str = Field(min_length=1)
    flow_uses_pattern: str = Field(min_length=1)
    full_sha_pattern: str = Field(min_length=1)
    main_ref: str = Field(min_length=1)
    third_party_message: str = Field(min_length=1)
    third_party_remediation: str = Field(min_length=1)
    first_party_tag_message: str = Field(min_length=1)
    first_party_remediation: str = Field(min_length=1)
    first_party_main_message: str = Field(min_length=1)
    known_exception_message: str = Field(min_length=1)
    stale_exception_message: str = Field(min_length=1)
