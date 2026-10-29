# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ValidatorNoBareFeatureFlags -- the contract loader of the bare-feature-flag rules (OMN-21518).

The rules are the rule rows of ``contracts/no_bare_feature_flags.validation.yaml``. The
decisions are made by the pure handler of ``node_no_bare_feature_flags_check_compute``
over explicit ``(path, source)`` pairs, run by that node's runtime, so this entry holds
the contract only.
"""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.validation.validator_base import ValidatorBase


class ValidatorNoBareFeatureFlags(ValidatorBase):
    """Carries the validator contract the node runtime reads its rules from."""

    validator_id: ClassVar[str] = "no_bare_feature_flags"

    def _validate_file(
        self,
        path: Path,
        contract: ModelValidatorSubcontract,
    ) -> tuple[ModelValidationIssue, ...]:
        """No per-file rule runs here: the node runtime reads the sources (``handler_no_bare_feature_flags``)."""
        return ()


__all__ = ["ValidatorNoBareFeatureFlags"]
