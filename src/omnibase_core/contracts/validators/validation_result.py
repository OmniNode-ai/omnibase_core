# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ValidationResult — structured output of ticket contract validation. OMN-8916"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ValidationResult:
    """Structured result of validate_ticket_contract."""

    valid: bool
    errors: list[str] = field(default_factory=list)


__all__ = ["ValidationResult"]
