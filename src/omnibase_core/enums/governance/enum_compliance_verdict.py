# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Compliance Verdict Enum.

Verdict categories for handler contract compliance audits.
"""

from enum import Enum, unique


@unique
class EnumComplianceVerdict(str, Enum):
    """Verdict for a handler's contract compliance status.

    - COMPLIANT: Handler fully adheres to its contract declarations.
    - IMPERATIVE: Handler bypasses the contract system (hardcoded topics, etc.).
    - HYBRID: Handler partially uses contracts but has some imperative wiring.
    - ALLOWLISTED: Handler has known violations tracked in the allowlist.
    - MISSING_CONTRACT: No contract.yaml exists for the handler's node.
    """

    COMPLIANT = "compliant"
    """Handler fully adheres to its contract declarations."""

    IMPERATIVE = "imperative"
    """Handler bypasses the contract system."""

    HYBRID = "hybrid"
    """Handler partially uses contracts but has some imperative wiring."""

    ALLOWLISTED = "allowlisted"
    """Handler has known violations tracked in the allowlist."""

    MISSING_CONTRACT = "missing_contract"
    """No contract.yaml exists for the handler's node."""

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value
