# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ValidatorPublicCiPlacement -- ``check-public-runner-placement`` in the generic format (OMN-21503).

``ValidatorBase`` entry over :mod:`omnibase_core.validation.checker_public_runner_placement`.
It backs the ``check-public-runner-placement`` pre-commit hook, the reusable
``version-drift.yml`` workflow every repository inherits and manual runs. The
repository name and visibility are arguments; every pattern is a parameter of
``contracts/public_runner_placement.validation.yaml``.

    python -m omnibase_core.validation.validator_public_runner_placement --repo NAME [--visibility private] [paths...]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import ClassVar

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import (
    ModelSourceFile,
)
from omnibase_core.models.version_drift.model_public_runner_placement_input import (
    ModelPublicRunnerPlacementInput,
)
from omnibase_core.validation.checker_public_runner_placement import (
    check_public_runner_placement,
)
from omnibase_core.validation.validator_base import ValidatorBase


class ValidatorPublicCiPlacement(ValidatorBase):
    """Refuse every public-repository job that can run on a self-hosted runner."""

    validator_id: ClassVar[str] = "public_runner_placement"

    def __init__(
        self,
        contract: ModelValidatorSubcontract | None = None,
        *,
        repository: str = "",
        public: bool = True,
        root: Path | None = None,
    ) -> None:
        super().__init__(contract)
        self._root = (root or Path.cwd()).resolve()
        self._repository = repository or self._root.name
        self._public = public

    def _validate_file(
        self,
        path: Path,
        contract: ModelValidatorSubcontract,
    ) -> tuple[ModelValidationIssue, ...]:
        resolved = path.resolve()
        relative = (
            resolved.relative_to(self._root)
            if resolved.is_relative_to(self._root)
            else path
        )
        request = ModelPublicRunnerPlacementInput(
            repository=self._repository,
            public=self._public,
            files=(
                ModelSourceFile(
                    path=relative.as_posix(),
                    source=path.read_text(encoding="utf-8", errors="replace"),
                ),
            ),
        )
        return check_public_runner_placement(
            request, {r.rule_id: r for r in contract.rules}
        )

    @classmethod
    def main(cls) -> int:
        """CLI entry: the generic targets plus the repository name and visibility."""
        parser = argparse.ArgumentParser(
            description=f"Run {cls.validator_id} validator"
        )
        parser.add_argument("targets", nargs="*", type=Path)
        parser.add_argument("--root", type=Path, default=Path())
        parser.add_argument("--repo", default="")
        parser.add_argument(
            "--visibility",
            choices=("public", "private"),
            default="public",
        )
        args = parser.parse_args()
        validator = cls(
            repository=args.repo,
            public=args.visibility == "public",
            root=args.root,
        )
        result = validator.validate(args.targets or [args.root])
        for issue in result.issues:
            sys.stdout.write(f"{issue.severity.value.upper()}: {issue.message}\n")
        return validator.get_exit_code(result)


if __name__ == "__main__":
    sys.exit(ValidatorPublicCiPlacement.main())
