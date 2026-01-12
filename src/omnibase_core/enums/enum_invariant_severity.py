# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Invariant severity levels - DEPRECATED.

.. deprecated:: 0.6.5
    EnumInvariantSeverity is deprecated. Use EnumSeverity from
    omnibase_core.enums.enum_severity instead.

    Migration (OMN-1311):
        # Before
        from omnibase_core.enums.enum_invariant_severity import EnumInvariantSeverity
        severity = EnumInvariantSeverity.WARNING

        # After
        from omnibase_core.enums.enum_severity import EnumSeverity
        severity = EnumSeverity.WARNING

    EnumInvariantSeverity values (INFO, WARNING, CRITICAL) are a subset of
    the canonical EnumSeverity values.
"""

from omnibase_core.enums.enum_severity import EnumSeverity

# Deprecated: use EnumSeverity directly (OMN-1311)
EnumInvariantSeverity = EnumSeverity

__all__ = ["EnumInvariantSeverity"]
