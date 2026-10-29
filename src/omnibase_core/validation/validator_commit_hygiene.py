# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ValidatorCommitHygiene -- the commit refusals that never write (OMN-21498, K8).

``missing_final_newline``, ``extra_final_newline``, ``staged_tmp_file`` and
``ai_coauthor_trailer``: each refuses and none rewrites a file or a commit
message. The ``ValidatorBase`` entry reads one path (a staged file, or the commit
message file at the commit-msg stage) and hands its repository-relative path and
bytes with the contract's rule rows to the pure
``checker_commit_hygiene.check_commit_hygiene``. The trailer pattern, the refused
path pattern and every remediation text live in
``contracts/commit_hygiene.validation.yaml``.

Usage (pre-commit hooks ``commit-hygiene`` and ``commit-hygiene-message``)::

    python -m omnibase_core.validation.validator_commit_hygiene <paths...>
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import ClassVar

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.validation.checker_commit_hygiene import check_commit_hygiene
from omnibase_core.validation.validator_base import ValidatorBase

__all__ = ["ValidatorCommitHygiene"]


class ValidatorCommitHygiene(ValidatorBase):
    """Read one path and judge it against the contract's commit-hygiene rule rows."""

    validator_id: ClassVar[str] = "commit_hygiene"

    def _validate_file(
        self,
        path: Path,
        contract: ModelValidatorSubcontract,
    ) -> tuple[ModelValidationIssue, ...]:
        try:
            relative = path.resolve().relative_to(Path.cwd().resolve()).as_posix()
        except ValueError:
            relative = path.as_posix()
        return check_commit_hygiene(path, relative, path.read_bytes(), contract.rules)


if __name__ == "__main__":
    from omnibase_core.handlers.handler_validator_run import (
        build_validator_container,
        main,
    )

    sys.exit(main(ValidatorCommitHygiene, container_factory=build_validator_container))
