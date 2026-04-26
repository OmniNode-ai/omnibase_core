# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Validator mode enum (OMN-9767, parent OMN-9757).

Phase 3 of the corpus classification and normalization layer.

Selects the validation mode applied to a contract YAML file:

- ``STRICT``         → enforces all required fields; the gate applied to
                       new or edited contracts (CI hard fail on missing
                       required fields).
- ``MIGRATION_AUDIT`` → relaxed mode used for batch sweeps over the
                        legacy corpus during normalization; tolerates the
                        well-known set of historically-optional fields so
                        legacy files surface only their substantive
                        validation failures, not pre-existing schema
                        debt.
"""

from __future__ import annotations

from enum import Enum, unique


@unique
class EnumValidatorMode(str, Enum):
    """Mode flag for the corpus contract validator.

    Inherits from ``str`` so values JSON-serialize without extra logic.
    """

    STRICT = "strict"
    MIGRATION_AUDIT = "migration_audit"


__all__ = ["EnumValidatorMode"]
