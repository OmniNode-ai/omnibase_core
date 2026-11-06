# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ValidatorProviderImportSurface -- a provider change removes nothing its consumers import (OMN-22478).

``ValidatorBase`` entry over :mod:`omnibase_core.validation.checker_provider_import_surface`.

    python -m omnibase_core.validation.validator_provider_import_surface
        --provider-package NAME --provider-head SRC --provider-base SRC consumer_src [consumer_src...]
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
from omnibase_core.models.validation.model_provider_import_surface_input import (
    ModelProviderImportSurfaceInput,
)
from omnibase_core.models.validation.model_provider_module_fact import (
    ModelProviderModuleFact,
)
from omnibase_core.validation.checker_provider_import_surface import (
    check_provider_import_surface,
    check_something_read,
    provider_module_fact,
)
from omnibase_core.validation.validator_base import ValidatorBase


def read_provider_tree(
    source_root: Path, package: str
) -> tuple[ModelProviderModuleFact, ...]:
    """Every module under ``source_root/package``, with a directory holding source as a module.

    A directory holding only compiled leftovers is not a module: that is what a removed
    package looks like in a clone that synced past its removal.
    """
    facts: dict[str, ModelProviderModuleFact] = {}
    package_dir = source_root / package
    for path in sorted(package_dir.rglob("*.py")):
        parts = path.relative_to(source_root).with_suffix("").parts
        is_init = parts[-1] == "__init__"
        module = ".".join(parts[:-1] if is_init else parts)
        facts[module] = provider_module_fact(
            module, path.read_text(encoding="utf-8", errors="replace")
        )
        for depth in range(1, len(parts)):
            parent = ".".join(parts[:depth])
            facts.setdefault(parent, ModelProviderModuleFact(module=parent))
    return tuple(facts.values())


class ValidatorProviderImportSurface(ValidatorBase):
    """Refuse a provider head that removes what consumer source imports."""

    validator_id: ClassVar[str] = "provider_import_surface"

    def __init__(
        self,
        contract: ModelValidatorSubcontract | None = None,
        *,
        provider_package: str = "",
        head: tuple[ModelProviderModuleFact, ...] = (),
        base: tuple[ModelProviderModuleFact, ...] = (),
    ) -> None:
        super().__init__(contract)
        self._provider_package = provider_package
        self._head = head
        self._base = base

    def _request(
        self, consumers: tuple[ModelSourceFile, ...]
    ) -> ModelProviderImportSurfaceInput:
        return ModelProviderImportSurfaceInput(
            provider_package=self._provider_package,
            head=self._head,
            base=self._base,
            consumers=consumers,
        )

    def _validate_file(
        self,
        path: Path,
        contract: ModelValidatorSubcontract,
    ) -> tuple[ModelValidationIssue, ...]:
        source = ModelSourceFile(
            path=path.as_posix(),
            source=path.read_text(encoding="utf-8", errors="replace"),
        )
        return check_provider_import_surface(
            self._request((source,)), {r.rule_id: r for r in contract.rules}
        )

    def nothing_read_issues(self, files_read: int) -> tuple[ModelValidationIssue, ...]:
        """The check over the whole run: each tree it was given held something."""
        marker = ModelSourceFile(path=self._provider_package, source="")
        return check_something_read(
            self._request((marker,) if files_read else ()),
            {r.rule_id: r for r in self.contract.rules},
        )

    @classmethod
    def main(cls) -> int:
        """CLI entry: the consumer roots, the provider package and its two trees."""
        parser = argparse.ArgumentParser(
            description=f"Run {cls.validator_id} validator"
        )
        parser.add_argument("targets", nargs="+", type=Path)
        parser.add_argument("--provider-package", required=True)
        parser.add_argument("--provider-head", required=True, type=Path)
        parser.add_argument("--provider-base", required=True, type=Path)
        args = parser.parse_args()
        validator = cls(
            provider_package=args.provider_package,
            head=read_provider_tree(args.provider_head, args.provider_package),
            base=read_provider_tree(args.provider_base, args.provider_package),
        )
        result = validator.validate(args.targets)
        files_read = result.metadata.files_processed if result.metadata else 0
        extra = validator.nothing_read_issues(files_read or 0)
        for issue in (*result.issues, *extra):
            sys.stdout.write(f"{issue.severity.value.upper()}: {issue.message}\n")
        return validator.get_exit_code(result) or (1 if extra else 0)


if __name__ == "__main__":
    sys.exit(ValidatorProviderImportSurface.main())
