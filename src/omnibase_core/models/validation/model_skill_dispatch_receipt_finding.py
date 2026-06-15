# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelSkillDispatchReceiptFinding — a finding from the skill-dispatch receipt-mode
validator (OMN-13098).

The validator enforces that dispatch-only shim skills are expressed as a single
receipt-mode CLI call (``onex skill`` / ``onex delegate``) with no inline glue,
no bare ``onex (run|node|run-node)`` invocations, no executable logic in the
skill directory, and no prompt instruction to surface the raw JSON. A ratchet
allowlist tolerates not-yet-migrated skills at gate-introduction time while
forbidding the allowlist from growing.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from omnibase_core.enums.enum_skill_receipt_rule import EnumSkillReceiptRule


class ModelSkillDispatchReceiptFinding(BaseModel):
    """A single finding from the skill-dispatch receipt-mode validator."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    skill_name: str
    path: Path
    rule: EnumSkillReceiptRule
    message: str
    line: int | None = None

    def format(self) -> str:
        loc = f"{self.path}" if self.line is None else f"{self.path}:{self.line}"
        return f"{loc}: [{self.rule.value}] {self.skill_name}: {self.message}"
