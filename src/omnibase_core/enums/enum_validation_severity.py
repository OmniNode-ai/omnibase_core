# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Validation severity levels - DEPRECATED.

.. deprecated:: 0.6.5
    EnumValidationSeverity is deprecated. Use EnumSeverity from
    omnibase_core.enums.enum_severity instead.

    Migration (OMN-1311):
        # Before
        from omnibase_core.enums.enum_validation_severity import EnumValidationSeverity
        severity = EnumValidationSeverity.WARNING

        # After
        from omnibase_core.enums.enum_severity import EnumSeverity
        severity = EnumSeverity.WARNING

    EnumValidationSeverity values (INFO, WARNING, ERROR, CRITICAL) map directly
    to the canonical EnumSeverity values.
"""

from omnibase_core.enums.enum_severity import EnumSeverity

# Deprecated: use EnumSeverity directly (OMN-1311)
EnumValidationSeverity = EnumSeverity

__all__ = ["EnumValidationSeverity"]
