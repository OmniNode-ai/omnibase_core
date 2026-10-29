# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLI of the omnimarket validator residency ratchet (OMN-21503, plan task T-Q6).

All I/O of the check happens here: listing the tree under the target directory,
loading the validator's contract, the inventory and the baseline, and handing
those facts to the pure ``handler_omnimarket_validator_residency``. A handler
module, not a ``validation/`` module, because the canonical-file-shape ratchet
refuses a new code file there. Run in omnimarket's required ``ci``::

    python -m omnibase_core.handlers.handler_omnimarket_validator_residency_cli \\
        --baseline config/<committed baseline> \\
        --previous-baseline <baseline at the PR's base> .

``--emit-baseline`` prints the baseline to commit from the packaged inventory.
Without ``--baseline`` the baseline is derived from the inventory. A baseline
that grew against ``--previous-baseline`` fails.
"""

from __future__ import annotations

import argparse
import fnmatch
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from omnibase_core.enums import EnumSeverity
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_validator_inventory_class import (
    EnumValidatorInventoryClass,
)
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.handlers.handler_hardcoded_threshold import (
    load_contract_text,
    load_packaged_contract,
)
from omnibase_core.handlers.handler_omnimarket_validator_residency import (
    check_validator_residency,
)
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    RuleParameterDict,
)
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.validation.model_omnimarket_validator_inventory import (
    ModelOmnimarketValidatorInventory,
)
from omnibase_core.models.validation.model_omnimarket_validator_inventory_entry import (
    ModelOmnimarketValidatorInventoryEntry,
)
from omnibase_core.models.validation.model_omnimarket_validator_residency_baseline import (
    ModelOmnimarketValidatorResidencyBaseline,
)
from omnibase_core.models.validation.model_omnimarket_validator_residency_policy import (
    ModelOmnimarketValidatorResidencyPolicy,
)
from omnibase_core.models.validation.model_omnimarket_validator_residency_result import (
    ModelOmnimarketValidatorResidencyResult,
)
from omnibase_core.utils.util_safe_yaml_loader import load_and_validate_yaml_model

__all__ = [
    "check_tree",
    "derive_baseline",
    "list_tree",
    "load_baseline",
    "load_inventory",
    "main",
    "policy_from_contract",
]

VALIDATOR_NAME = "omnimarket_validator_residency"
_RULE_ID = "validator_residency"
_PACKAGE_DIR = Path(__file__).parents[1] / "validation"


def _parameters(contract: ModelValidatorSubcontract) -> RuleParameterDict:
    for rule in contract.rules:
        if rule.rule_id == _RULE_ID and rule.parameters is not None:
            return dict(rule.parameters)
    raise ModelOnexError(
        message=f"contract {contract.validator_id} has no {_RULE_ID} parameters",
        error_code=EnumCoreErrorCode.INVALID_CONFIGURATION,
    )


def _strings(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ModelOnexError(
            message="expected a list of strings in the contract parameters",
            error_code=EnumCoreErrorCode.INVALID_CONFIGURATION,
        )
    return tuple(str(item) for item in value)


def policy_from_contract(
    contract: ModelValidatorSubcontract,
) -> ModelOmnimarketValidatorResidencyPolicy:
    """Build the checker's policy from the contract's rule parameters."""
    params = _parameters(contract)
    return ModelOmnimarketValidatorResidencyPolicy(
        script_globs=_strings(params["script_globs"]),
        node_root=str(params["node_root"]),
        node_name_patterns=_strings(params["node_name_patterns"]),
        child_ticket_severity=EnumSeverity(str(params["child_ticket_severity"])),
        acceptance_wave=int(str(params["acceptance_wave"])),
        wave_obligation=str(params["wave_obligation"]),
    )


def load_inventory(path: Path) -> tuple[ModelOmnimarketValidatorInventoryEntry, ...]:
    return load_and_validate_yaml_model(path, ModelOmnimarketValidatorInventory).entries


def load_baseline(path: Path) -> tuple[str, ...]:
    return load_and_validate_yaml_model(
        path, ModelOmnimarketValidatorResidencyBaseline
    ).resident_validators


def derive_baseline(
    inventory: Sequence[ModelOmnimarketValidatorInventoryEntry],
) -> tuple[str, ...]:
    """The validator entries of the inventory: the seed of a consumer's baseline."""
    return tuple(
        sorted(
            entry.path
            for entry in inventory
            if entry.validator_class is EnumValidatorInventoryClass.VALIDATOR
        )
    )


def _excluded(relative: str, patterns: Sequence[str]) -> bool:
    return any(fnmatch.fnmatchcase("/" + relative, pattern) for pattern in patterns)


def list_tree(root: Path, exclude_patterns: Sequence[str]) -> tuple[str, ...]:
    """Repository-relative POSIX paths of the files under ``root``, sorted."""
    found: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        base = Path(dirpath)
        dirnames[:] = sorted(
            d
            for d in dirnames
            if not _excluded(
                (base / d / "_").relative_to(root).as_posix(), exclude_patterns
            )
        )
        found.extend(
            relative
            for relative in (
                (base / name).relative_to(root).as_posix() for name in sorted(filenames)
            )
            if not _excluded(relative, exclude_patterns)
        )
    return tuple(found)


def check_tree(
    root: Path,
    *,
    contract: ModelValidatorSubcontract | None = None,
    inventory_path: Path | None = None,
    baseline_path: Path | None = None,
    previous_baseline_path: Path | None = None,
) -> ModelOmnimarketValidatorResidencyResult:
    """The I/O boundary: list, load, then hand the facts to the pure checker."""
    contract = contract or load_packaged_contract(VALIDATOR_NAME)
    params = _parameters(contract)
    inventory = load_inventory(
        inventory_path or _PACKAGE_DIR / str(params["inventory_path"])
    )
    return check_validator_residency(
        tree_paths=list_tree(root, contract.exclude_patterns),
        policy=policy_from_contract(contract),
        inventory=inventory,
        baseline_ids=(
            load_baseline(baseline_path)
            if baseline_path is not None
            else derive_baseline(inventory)
        ),
        previous_baseline_ids=(
            load_baseline(previous_baseline_path)
            if previous_baseline_path is not None
            else None
        ),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=VALIDATOR_NAME)
    parser.add_argument("root", type=Path, nargs="?", default=Path())
    parser.add_argument("--baseline", type=Path, default=None)
    parser.add_argument("--previous-baseline", type=Path, default=None)
    parser.add_argument("--inventory", type=Path, default=None)
    parser.add_argument("--contract", type=Path, default=None)
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument(
        "--emit-baseline",
        action="store_true",
        help="Print the baseline a consuming repository seeds from the inventory",
    )
    args = parser.parse_args(argv)

    contract = (
        load_contract_text(args.contract.read_text(encoding="utf-8"))
        if args.contract is not None
        else None
    )
    if args.emit_baseline:
        params = _parameters(contract or load_packaged_contract(VALIDATOR_NAME))
        emitted = derive_baseline(
            load_inventory(
                args.inventory or _PACKAGE_DIR / str(params["inventory_path"])
            )
        )
        sys.stdout.write("schema_version: 1\nresident_validators:\n")
        sys.stdout.writelines(f"  - {path}\n" for path in emitted)
        return 0
    result = check_tree(
        args.root,
        contract=contract,
        inventory_path=args.inventory,
        baseline_path=args.baseline,
        previous_baseline_path=args.previous_baseline,
    )
    if args.as_json:
        sys.stdout.write(result.canonical_json() + "\n")
    else:
        sys.stdout.write(f"{VALIDATOR_NAME}: {result.count} resident validator(s)\n")
        for issue in result.issues:
            sys.stderr.write(
                f"  [{issue.severity.value}] {issue.code}: {issue.message}\n"
            )
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
