# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Validator-requirement emits enumeration (OMN-22003).

Declares, per ``required_validators`` entry in validator-requirements.yaml,
whether the validator must write its verdict through the validation report
writer (``required``) or is by nature not a core validator and so is not
judged (``exempt``, which carries a reason).

Related ticket: OMN-22003 (emits check), OMN-9115 (consumer), parent OMN-9048.
"""

import enum

__all__ = ["EnumValidatorRequirementEmits"]


@enum.unique
class EnumValidatorRequirementEmits(enum.StrEnum):
    """Whether a required validator must emit through the report writer."""

    REQUIRED = "required"
    EXEMPT = "exempt"
