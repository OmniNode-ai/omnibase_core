# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""A write the test-write guard judges: the kind of target and the target (OMN-19513)."""

from pydantic import BaseModel, ConfigDict

from omnibase_core.enums.enum_ledger_write_target import EnumLedgerWriteTarget

__all__ = ["ModelLedgerWriteGuardRequest"]


class ModelLedgerWriteGuardRequest(BaseModel):
    """A write the test-write guard judges: the kind of target and the target (OMN-19513)."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    target_kind: EnumLedgerWriteTarget
    target: str
