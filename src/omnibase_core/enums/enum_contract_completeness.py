# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Contract Completeness Enum.

Defines the completeness level of a ticket contract:
- STUB: skeleton generated at ticket creation time (minimal fields only)
- ENRICHED: contract has dod_evidence and evidence_requirements populated
- FULL: contract is fully specified with all fields, ready for execution
"""

from __future__ import annotations

from enum import Enum


class EnumContractCompleteness(str, Enum):
    """Completeness level of a ModelTicketContract.

    Used by the contract_completeness field on ModelTicketContract (OMN-9582).
    Values are uppercase strings to match YAML serialization convention used
    across on-disk contracts in onex_change_control.
    """

    STUB = "STUB"
    ENRICHED = "ENRICHED"
    FULL = "FULL"


__all__ = [
    "EnumContractCompleteness",
]
