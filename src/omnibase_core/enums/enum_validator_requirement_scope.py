# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Validator-requirement scope enumeration.

Constrains the ``pre_commit`` and ``ci_workflow`` scope fields on
``ModelValidatorRequirementEntry`` so that a spec typo (e.g. ``requird``)
surfaces as a Pydantic validation error at load time rather than silently
bypassing enforcement.

Related ticket: OMN-9115 (consumer), OMN-9051 (spec), parent OMN-9048.
"""

import enum

__all__ = ["EnumValidatorRequirementScope"]


@enum.unique
class EnumValidatorRequirementScope(enum.StrEnum):
    """Scope of a validator requirement.

    ``REQUIRED`` — repos matching ``applies_to_repos`` MUST wire this
    validator; a gap is reported if absent.
    ``OPTIONAL`` — repos MAY skip this validator without producing a gap.
    """

    REQUIRED = "required"
    OPTIONAL = "optional"
