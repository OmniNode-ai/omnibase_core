# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Validator-requirement compliance gap kind enumeration.

Classifies violations found by ValidatorRequirementsConsumer when comparing
a repo's ``.pre-commit-config.yaml`` + ``.github/workflows/*.yml`` against
``architecture-handshakes/validator-requirements.yaml``.

Related ticket: OMN-9115 (consumer), OMN-9051 (spec), parent OMN-9048.
"""

import enum

__all__ = ["EnumValidatorRequirementGapKind"]


@enum.unique
class EnumValidatorRequirementGapKind(enum.StrEnum):
    """Kind of validator-requirement compliance gap."""

    MISSING_PRE_COMMIT = "MISSING_PRE_COMMIT"
    MISSING_CI_WORKFLOW = "MISSING_CI_WORKFLOW"
    SILENT_SKIP_WRAPPER = "SILENT_SKIP_WRAPPER"
