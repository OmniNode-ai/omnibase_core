# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ValidatorSingleClassPerFile -- the single-class refusal (OMN-22003).

The ``ValidatorBase`` entry reads one path and hands its path facts and bytes
with the contract's rule rows to the pure
``checker_single_class_per_file.check_single_class_per_file``. Exemptions, enum
base markers, thresholds and every message live in
``contracts/single_class_per_file.validation.yaml``.

Usage (pre-commit hook ``onex-single-class-per-file``)::

    python -m omnibase_core.nodes.node_validation_report_write_effect.runtime_validator_run omnibase_core.validation.validator_single_class_per_file:ValidatorSingleClassPerFile <paths...>
"""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.validation.checker_single_class_per_file import (
    check_single_class_per_file,
)
from omnibase_core.validation.validator_base import ValidatorBase

__all__ = ["ValidatorSingleClassPerFile"]


class ValidatorSingleClassPerFile(ValidatorBase):
    """Read one path and judge it against the contract's single-class rule rows."""

    validator_id: ClassVar[str] = "single_class_per_file"

    @classmethod
    def _validate_cli_path(cls, path: Path, context: str) -> Path | None:
        """Keep the caller's spelling after the base class checks path safety."""
        if super()._validate_cli_path(path, context) is None:
            return None
        return path

    def _resolve_targets(self, targets: list[Path]) -> list[Path]:
        """Expand targets without rewriting the legacy path-marker facts.

        Resolving a relative target would introduce parent directory markers
        that the old script never judged. Symlinked files are also retained,
        as in its directory scans; canonical exemptions still use resolved paths.
        """
        files: set[Path] = set()
        for target in targets:
            if target.is_file():
                files.add(target)
            elif target.is_dir():
                for pattern in self.contract.target_patterns:
                    files.update(
                        path for path in target.glob(pattern) if path.is_file()
                    )
        return sorted(files)

    def _validate_file(
        self,
        path: Path,
        contract: ModelValidatorSubcontract,
    ) -> tuple[ModelValidationIssue, ...]:
        resolved = path.resolve()
        try:
            repository_relative = resolved.relative_to(
                Path(__file__).resolve().parents[3]
            ).as_posix()
        except ValueError:
            repository_relative = None
        try:
            content = path.read_bytes()
        except OSError:
            # The legacy script skips unreadable files; other tools judge I/O errors.
            return ()
        return check_single_class_per_file(
            path,
            path.as_posix(),
            content,
            contract.rules,
            repository_relative_path=repository_relative,
        )
