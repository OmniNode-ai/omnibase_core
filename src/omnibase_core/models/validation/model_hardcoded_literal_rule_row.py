# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelHardcodedLiteralRuleRow -- one enabled rule row of K6 families O, G, F, P, S, H and B (OMN-21537)."""

from __future__ import annotations

from dataclasses import dataclass

from omnibase_core.enums.enum_severity import EnumSeverity


@dataclass(frozen=True, slots=True)
class ModelHardcodedLiteralRuleRow:
    """One enabled rule row: the family it judges, its id, severity and remediation text."""

    family: str
    rule_name: str
    severity: EnumSeverity
    remediation: str


__all__ = ["ModelHardcodedLiteralRuleRow"]
