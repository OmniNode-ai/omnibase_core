# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ValidatorPublicLabSelection -- ``check-public-lab-selection`` in the generic format (OMN-19998).

``ValidatorBase`` entry over :mod:`omnibase_core.validation.checker_public_lab_selection`.
The routes come from the ``contracts/public_lab_node_routes.yaml`` packaged with
this omnibase_core, so a calling repository cannot edit them.

    python -m omnibase_core.validation.validator_public_lab_selection --repo NAME [--visibility private]
        [--variables-json JSON] [--base-routes FILE] [paths...]
"""

from __future__ import annotations

import argparse
import json
import sys
from importlib import resources
from pathlib import Path
from typing import ClassVar

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import (
    ModelSourceFile,
)
from omnibase_core.models.version_drift.model_public_lab_node_routes import (
    ModelPublicLabNodeRoutes,
)
from omnibase_core.models.version_drift.model_public_lab_selection_input import (
    ModelPublicLabSelectionInput,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_mapping_no_duplicates
from omnibase_core.validation.checker_public_lab_selection import (
    check_public_lab_selection,
    check_routes_only_shrink,
    check_seam_values,
)
from omnibase_core.validation.validator_base import ValidatorBase

ROUTES_PACKAGE = "omnibase_core.contracts"
ROUTES_FILE = "public_lab_node_routes.yaml"


def _parse_routes(text: str, source: str) -> ModelPublicLabNodeRoutes:
    return ModelPublicLabNodeRoutes.model_validate(
        load_yaml_mapping_no_duplicates(text, source=source)
    )


def load_packaged_routes() -> ModelPublicLabNodeRoutes:
    """The typed routes shipped with this omnibase_core."""
    text = resources.files(ROUTES_PACKAGE).joinpath(ROUTES_FILE).read_text("utf-8")
    return _parse_routes(text, ROUTES_FILE)


class ValidatorPublicLabSelection(ValidatorBase):
    """Refuse a public-repository job selecting the lab without a typed route."""

    validator_id: ClassVar[str] = "public_lab_selection"

    def __init__(
        self,
        contract: ModelValidatorSubcontract | None = None,
        *,
        repository: str = "",
        public: bool = True,
        root: Path | None = None,
        routes: ModelPublicLabNodeRoutes | None = None,
    ) -> None:
        super().__init__(contract)
        self._root = (root or Path.cwd()).resolve()
        self._repository = repository or self._root.name
        self._public = public
        self._routes = routes if routes is not None else load_packaged_routes()

    def _request(
        self,
        files: tuple[ModelSourceFile, ...] = (),
        variables: dict[str, str] | None = None,
    ) -> ModelPublicLabSelectionInput:
        return ModelPublicLabSelectionInput(
            repository=self._repository,
            public=self._public,
            files=files,
            routes=self._routes,
            variables=variables or {},
        )

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
        source = ModelSourceFile(
            path=relative.as_posix(),
            source=path.read_text(encoding="utf-8", errors="replace"),
        )
        return check_public_lab_selection(
            self._request(files=(source,)), {r.rule_id: r for r in contract.rules}
        )

    def extra_issues(
        self,
        variables: dict[str, str],
        base_routes: ModelPublicLabNodeRoutes | None,
    ) -> tuple[ModelValidationIssue, ...]:
        """The checks over the whole repository: live seam values and route growth."""
        rules = {r.rule_id: r for r in self.contract.rules}
        issues = check_seam_values(self._request(variables=variables), rules)
        if base_routes is not None:
            issues += check_routes_only_shrink(
                base_routes, self._routes, rules, ROUTES_FILE
            )
        return issues

    @classmethod
    def main(cls) -> int:
        """CLI entry: the generic targets plus repository, visibility, variables and base routes."""
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
        parser.add_argument("--variables-json", default="")
        parser.add_argument("--base-routes", type=Path, default=None)
        args = parser.parse_args()
        validator = cls(
            repository=args.repo,
            public=args.visibility == "public",
            root=args.root,
        )
        result = validator.validate(args.targets or [args.root])
        variables = json.loads(args.variables_json) if args.variables_json else {}
        base_routes = (
            _parse_routes(
                args.base_routes.read_text(encoding="utf-8"), str(args.base_routes)
            )
            if args.base_routes is not None
            else None
        )
        extra = validator.extra_issues(variables, base_routes)
        for issue in (*result.issues, *extra):
            sys.stdout.write(f"{issue.severity.value.upper()}: {issue.message}\n")
        return validator.get_exit_code(result) or (1 if extra else 0)


if __name__ == "__main__":
    sys.exit(ValidatorPublicLabSelection.main())
