# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ValidatorCanonicalFileShape -- the generic-format entry for the canonical-file-shape rules (OMN-21515).

The rules are a pure checker (``checker_canonical_file_shape``) over typed facts
and a contract (``contracts/canonical_file_shape.validation.yaml``). The facts
are a repository's tracked tree at a revision, not a file glob, so this entry
has the git reader (``validator_git_repo.GitRepo``) that the node runtime
``node_canonical_file_shape_check_compute`` gathers them with; the COMPUTE node
package itself performs no I/O.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import ClassVar

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.common.model_validation_result import ModelValidationResult
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.validation.model_canonical_file_shape_facts import (
    ModelCanonicalFileShapeFacts,
)
from omnibase_core.validation.checker_canonical_file_shape import check, load_rule_set
from omnibase_core.validation.validator_base import ValidatorBase


def write_text_file(path: Path, text: str) -> None:
    """Write ``text`` to ``path``, creating parent directories (the baseline file)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class ValidatorCanonicalFileShape(ValidatorBase):
    """Run the canonical-file-shape checker over gathered repository facts."""

    validator_id: ClassVar[str] = "canonical_file_shape"

    def validate_facts(
        self, facts: ModelCanonicalFileShapeFacts
    ) -> ModelValidationResult[None]:
        """Check ``facts`` against this validator's contract."""
        issues = list(check(facts, load_rule_set(self.contract)))
        paths = sorted({str(issue.file_path) for issue in issues})
        return self._build_result(
            files_checked=[Path(path) for path in facts.head_tree.files],
            issues=issues,
            files_with_violations=paths,
            duration_ms=0,
        )

    def _validate_file(
        self,
        path: Path,
        contract: ModelValidatorSubcontract,
    ) -> tuple[ModelValidationIssue, ...]:
        """No per-file rule exists: the rules read a whole revision (``validate_facts``)."""
        return ()


if __name__ == "__main__":
    sys.exit(ValidatorCanonicalFileShape.main())
