# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ValidatorDepProvenance -- the dependency provenance check in the generic validator format (OMN-22011, T2.3).

The ``ValidatorBase`` entry of the dependency provenance rules: it reads one ``pyproject.toml``
and hands it with the contract's rule rows and the shared dev-merge tag pattern to the pure
``checker_dep_provenance.check_dep_provenance``. The governed packages, the admitted shapes and
every message live in ``contracts/dep_provenance.validation.yaml``. The shape of a dev-merge tag
has one definition, the ``first_party_ref`` contract, read through ``dev_tag_pattern``; the
identity of a tag is the ``dev_tag_lineage`` validator and its hook id.

Usage (pre-commit hook)::

    python -m omnibase_core.nodes.node_validation_report_write_effect.runtime_validator_run omnibase_core.validation.validator_dep_provenance:ValidatorDepProvenance <pyproject.toml...>
"""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.dep_provenance.model_dep_provenance_rules import (
    ModelDepProvenanceRules,
)
from omnibase_core.validation.checker_dep_provenance import check_dep_provenance
from omnibase_core.validation.validator_base import ValidatorBase
from omnibase_core.validation.validator_first_party_ref import dev_tag_pattern

__all__ = ["ValidatorDepProvenance"]


class ValidatorDepProvenance(ValidatorBase):
    """Read one pyproject and judge its package sources against the contract rule rows."""

    validator_id: ClassVar[str] = "dep_provenance"

    def _load_contract(self) -> ModelValidatorSubcontract:
        contract = super()._load_contract()
        ModelDepProvenanceRules.from_contract(contract)
        return contract

    def _validate_file(
        self,
        path: Path,
        contract: ModelValidatorSubcontract,
    ) -> tuple[ModelValidationIssue, ...]:
        rules = ModelDepProvenanceRules.from_contract(contract)
        try:
            source = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise ModelOnexError(
                message=f"{path}: cannot read pyproject: {exc}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            ) from exc
        return check_dep_provenance(path, source, rules, dev_tag_pattern())
