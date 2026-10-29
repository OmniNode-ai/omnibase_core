# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ValidatorProtocolBinding -- refuse a protocol bound to its implementation in code (OMN-21533, T0.5, K5).

The ``ValidatorBase`` entry of the protocol-binding rules: it reads one Python file or one node
contract and hands the parsed facts with the contract's rule rows to the pure
``checker_protocol_binding``. The scan set, the baseline path and every rule value live in
``contracts/protocol_binding.validation.yaml``.

Usage (pre-commit hook)::

    python -m omnibase_core.nodes.node_validation_report_write_effect.runtime_validator_run omnibase_core.validation.validator_protocol_binding:ValidatorProtocolBinding <files...>
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import ClassVar

import yaml

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_mapping_no_duplicates
from omnibase_core.validation.checker_protocol_binding import (
    check_protocol_binding,
    check_setting_two_homes,
    contract_setting_keys,
    parse_baseline,
)
from omnibase_core.validation.validator_base import ValidatorBase

__all__ = ["ValidatorProtocolBinding"]


class ValidatorProtocolBinding(ValidatorBase):
    """Read one source or contract file and judge it against the contract rule rows."""

    validator_id: ClassVar[str] = "protocol_binding"

    def __init__(
        self,
        contract: ModelValidatorSubcontract | None = None,
        *,
        baseline: Mapping[str, int] | None = None,
        root: Path | None = None,
    ) -> None:
        super().__init__(contract)
        self._baseline = dict(baseline) if baseline is not None else None
        self._root = (root or Path.cwd()).resolve()
        self._homes: dict[str, list[str]] = {}

    @classmethod
    def with_baseline_file(cls, path: Path) -> ValidatorProtocolBinding:
        """The validator held to the per-file baseline in ``path`` (the hook's ``--baseline``)."""
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise ModelOnexError(
                message=f"{path}: cannot read baseline: {exc}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            ) from exc
        return cls(baseline=parse_baseline(text))

    def _key(self, path: Path) -> Path:
        resolved = path.resolve()
        if resolved.is_relative_to(self._root):
            return resolved.relative_to(self._root)
        return path

    def _validate_file(
        self,
        path: Path,
        contract: ModelValidatorSubcontract,
    ) -> tuple[ModelValidationIssue, ...]:
        key = self._key(path)
        try:
            source = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise ModelOnexError(
                message=f"{path}: cannot read: {exc}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            ) from exc
        if path.suffix == ".py":
            issues = check_protocol_binding(
                key, source, contract.rules, self._baseline or {}
            )
            return tuple(i.model_copy(update={"file_path": path}) for i in issues)
        try:
            document = load_yaml_mapping_no_duplicates(source, source=str(path))
        except (yaml.YAMLError, ValueError) as exc:
            raise ModelOnexError(
                message=f"{path}: invalid YAML: {exc}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            ) from exc
        keys = contract_setting_keys(
            {str(k): v for k, v in document.items()}, contract.rules
        )
        issues = check_setting_two_homes(key, keys, self._homes, contract.rules)
        for setting in keys:
            self._homes.setdefault(setting, []).append(key.as_posix())
        return tuple(i.model_copy(update={"file_path": path}) for i in issues)
