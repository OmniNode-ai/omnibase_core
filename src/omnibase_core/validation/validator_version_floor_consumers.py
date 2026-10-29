# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Generic entry for check-version-floor-consumers (OMN-19998, OMN-21503).

All I/O lives here: read the changed pyproject, git show its base and each
registry consumer's origin default branch. The pure checker judges the facts.

    python -m omnibase_core.validation.validator_version_floor_consumers --repo NAME --base-ref REF
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import ClassVar

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.handlers.handler_dependency_direction_cli import (
    infer_repo,
    load_layer_map,
)
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.version_drift.model_consumer_pyproject import (
    ModelConsumerPyproject,
)
from omnibase_core.models.version_drift.model_version_floor_check_input import (
    ModelVersionFloorCheckInput,
)
from omnibase_core.validation.checker_version_floor_consumers import (
    RULE_FLOOR,
    check_version_floor_consumers,
)
from omnibase_core.validation.validator_base import ValidatorBase

PYPROJECT = "pyproject.toml"


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def _default_consumers_root(root: Path) -> Path:
    """The directory holding this repository's canonical clone (the registry root)."""
    common = _git(root, "rev-parse", "--path-format=absolute", "--git-common-dir")
    if common.returncode == 0 and common.stdout.strip():
        return Path(common.stdout.strip()).parent.parent
    return root.parent


def _read_consumer(consumers_root: Path, repo: str) -> ModelConsumerPyproject:
    """A consumer's pyproject at its origin default branch.

    A clone whose default branch has no pyproject.toml declares no Python
    dependency and reads as empty text; a missing clone or an unresolvable
    default branch reads as None (unreadable).
    """
    clone = consumers_root / repo
    if not clone.is_dir():
        return ModelConsumerPyproject(repo=repo, ref="absent", pyproject=None)
    head = _git(clone, "symbolic-ref", "--short", "refs/remotes/origin/HEAD")
    ref = head.stdout.strip()
    if head.returncode != 0 or not ref:
        return ModelConsumerPyproject(repo=repo, ref="origin/HEAD", pyproject=None)
    if _git(clone, "cat-file", "-e", f"{ref}:{PYPROJECT}").returncode != 0:
        return ModelConsumerPyproject(repo=repo, ref=ref, pyproject="")
    shown = _git(clone, "show", f"{ref}:{PYPROJECT}")
    text = shown.stdout if shown.returncode == 0 else None
    return ModelConsumerPyproject(repo=repo, ref=ref, pyproject=text)


def _base_ref(root: Path, given: str | None) -> tuple[str | None, str | None]:
    """The base commit and an error message, one of them None."""
    if given:
        if _git(
            root, "rev-parse", "--verify", "--quiet", f"{given}^{{commit}}"
        ).returncode:
            return None, (
                f"base ref {given!r} is not in the clone; fetch it, since a floor "
                "comparison with no base is never a pass"
            )
        return given, None
    for upstream in ("origin/HEAD", "origin/dev", "origin/main"):
        merge_base = _git(root, "merge-base", "HEAD", upstream)
        if merge_base.returncode == 0 and merge_base.stdout.strip():
            return merge_base.stdout.strip(), None
    return None, (
        "no --base-ref and no merge-base with origin/HEAD, origin/dev or "
        "origin/main; pass --base-ref"
    )


class ValidatorVersionFloorConsumers(ValidatorBase):
    """Refuse a raised sibling floor ahead of its registry consumers."""

    validator_id: ClassVar[str] = "version_floor_consumers"

    def __init__(
        self,
        contract: ModelValidatorSubcontract | None = None,
        *,
        repository: str = "",
        root: Path | None = None,
        base_ref: str | None = None,
        consumers_root: Path | None = None,
    ) -> None:
        super().__init__(contract)
        self._root = (root or Path.cwd()).resolve()
        self._repository = repository
        self._base_ref = base_ref
        self._consumers_root = consumers_root

    def _validate_file(
        self,
        path: Path,
        contract: ModelValidatorSubcontract,
    ) -> tuple[ModelValidationIssue, ...]:
        layer_map = load_layer_map()
        repo = self._repository or infer_repo(self._root, layer_map)
        base, error = _base_ref(self._root, self._base_ref)
        if error is not None or base is None:
            raise ModelOnexError(message=error or "no base ref")
        shown = _git(self._root, "show", f"{base}:{PYPROJECT}")
        base_text = shown.stdout if shown.returncode == 0 else None
        consumers_root = (
            self._consumers_root.resolve()
            if self._consumers_root is not None
            else _default_consumers_root(self._root)
        )
        request = ModelVersionFloorCheckInput(
            repo=repo,
            layer_map=layer_map,
            base_pyproject=base_text,
            head_pyproject=path.read_text(encoding="utf-8"),
            consumers=tuple(
                _read_consumer(consumers_root, entry.repo)
                for entry in layer_map.repos
                if entry.repo != repo
            ),
        )
        return check_version_floor_consumers(
            request, {r.rule_id: r for r in contract.rules}
        )

    @classmethod
    def main(cls, argv: list[str] | None = None) -> int:
        """CLI entry: pre-commit filenames and repository comparison arguments."""
        parser = argparse.ArgumentParser(
            description=f"Run {cls.validator_id} validator"
        )
        parser.add_argument("filenames", nargs="*", type=Path)
        parser.add_argument("--root", type=Path, default=Path())
        parser.add_argument("--repo", default="")
        parser.add_argument("--base-ref", default=None)
        parser.add_argument("--consumers-root", type=Path, default=None)
        args = parser.parse_args(argv)
        if args.filenames and not any(p.name == PYPROJECT for p in args.filenames):
            return 0
        root = args.root.resolve()
        head_file = root / PYPROJECT
        if not head_file.is_file():
            sys.stdout.write(
                f"OK: {args.repo or root.name} has no {PYPROJECT}; it raises no floor\n"
            )
            return 0
        validator = cls(
            repository=args.repo,
            root=root,
            base_ref=args.base_ref,
            consumers_root=args.consumers_root,
        )
        try:
            result = validator.validate(head_file)
        except (ModelOnexError, OSError) as exc:
            sys.stdout.write(f"ERROR: {exc}\n")
            return 1
        for issue in result.issues:
            status = "FAIL" if issue.code == RULE_FLOOR else "ERROR"
            sys.stdout.write(f"{status}: {issue.message}\n")
        if result.is_valid:
            sys.stdout.write(
                f"OK: {args.repo or root.name} raises no sibling floor ahead of a registry consumer\n"
            )
        return 0 if result.is_valid else 1


__all__ = ["ValidatorVersionFloorConsumers", "load_layer_map"]


if __name__ == "__main__":
    sys.exit(ValidatorVersionFloorConsumers.main())
