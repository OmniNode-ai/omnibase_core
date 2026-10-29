# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Rule loader of the dependency-direction check (OMN-19998, OMN-21518).

Every pattern, file-classification list and message template of the check is a
``parameters`` entry of a rule row of ``contracts/dependency_direction.validation.yaml``;
this module reads them into the typed ``ModelDependencyDirectionRules`` the pure
node handler takes in its request. It holds no rule data itself.
"""

from __future__ import annotations

import re
import subprocess
import tomllib
from collections.abc import Mapping
from functools import cache
from importlib import resources
from pathlib import Path

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.dependency_direction.model_dependency_direction_rules import (
    ModelDependencyDirectionRules,
)
from omnibase_core.models.dependency_direction.model_repo_layer_map import (
    ModelRepoLayerMap,
)
from omnibase_core.utils.util_safe_yaml_loader import (
    load_yaml_content_as_model,
)
from omnibase_core.validation.checker_rule_parameters import (
    rule_int,
    rule_string,
    rule_strings,
)

RULE_CHANNELS = "reference_channels"
RULE_UPWARD = "upward_dependency"
RULE_UNDECLARED = "repo_not_in_layer_map"
RULE_STALE = "stale_baseline_entry"
RULE_RATCHET = "baseline_ratchet"
RULE_SUMMARY = "run_summary"

__all__ = [
    "RULE_CHANNELS",
    "RULE_RATCHET",
    "RULE_STALE",
    "RULE_SUMMARY",
    "RULE_UNDECLARED",
    "RULE_UPWARD",
    "infer_repo",
    "load_dependency_direction_contract",
    "load_dependency_direction_rules",
    "load_layer_map",
    "rules_from_rows",
]


@cache
def load_dependency_direction_contract() -> ModelValidatorSubcontract:
    """The validator contract shipped inside the package."""
    raw = resources.files("omnibase_core.validation").joinpath(
        "contracts/dependency_direction.validation.yaml"
    )
    return load_yaml_content_as_model(raw.read_text("utf-8"), ModelValidatorSubcontract)


def _row(rows: Mapping[str, ModelValidatorRule], rule_id: str) -> ModelValidatorRule:
    row = rows.get(rule_id)
    if row is None:
        raise ModelOnexError(
            message=f"dependency_direction contract has no rule row {rule_id!r}",
            error_code=EnumCoreErrorCode.INVALID_CONFIGURATION,
        )
    return row


def rules_from_rows(
    rows: Mapping[str, ModelValidatorRule],
) -> ModelDependencyDirectionRules:
    """The typed rules from ``{rule_id: row}``; a missing row or parameter raises."""
    channels = _row(rows, RULE_CHANNELS)
    upward = _row(rows, RULE_UPWARD)
    undeclared = _row(rows, RULE_UNDECLARED)
    stale = _row(rows, RULE_STALE)
    ratchet = _row(rows, RULE_RATCHET)
    summary = _row(rows, RULE_SUMMARY)
    return ModelDependencyDirectionRules(
        install_or_fetch_pattern=rule_string(channels, "install_or_fetch_pattern"),
        repository_pattern=rule_string(channels, "repository_pattern"),
        requirement_name_pattern=rule_string(channels, "requirement_name_pattern"),
        name_separator_pattern=rule_string(channels, "name_separator_pattern"),
        token_before_pattern=rule_string(channels, "token_before_pattern"),
        token_after_pattern=rule_string(channels, "token_after_pattern"),
        slug_repo_pattern=rule_string(channels, "slug_repo_pattern"),
        script_suffixes=rule_strings(channels, "script_suffixes"),
        makefile_names=rule_strings(channels, "makefile_names"),
        workflow_dir_prefix=rule_string(channels, "workflow_dir_prefix"),
        workflow_suffixes=rule_strings(channels, "workflow_suffixes"),
        dockerfile_prefixes=rule_strings(channels, "dockerfile_prefixes"),
        dockerfile_suffixes=rule_strings(channels, "dockerfile_suffixes"),
        requirements_prefixes=rule_strings(channels, "requirements_prefixes"),
        requirements_suffixes=rule_strings(channels, "requirements_suffixes"),
        python_suffix=rule_string(channels, "python_suffix"),
        pyproject_name=rule_string(channels, "pyproject_name"),
        script_dirs=rule_strings(channels, "script_dirs"),
        script_excluded_dirs=rule_strings(channels, "script_excluded_dirs"),
        fixture_dirs=rule_strings(channels, "fixture_dirs"),
        comment_prefix=rule_string(channels, "comment_prefix"),
        evidence_limit=rule_int(channels, "evidence_limit"),
        remediation=rule_string(upward, "remediation"),
        violation_message=rule_string(upward, "violation_message"),
        direction_same=rule_string(upward, "direction_same"),
        direction_above=rule_string(upward, "direction_above"),
        baselined_message=rule_string(upward, "baselined_message"),
        undeclared_repo_message=rule_string(undeclared, "undeclared_repo_message"),
        stale_message=rule_string(stale, "stale_message"),
        ratchet_ref_missing_message=rule_string(ratchet, "ratchet_ref_missing_message"),
        baseline_grew_message=rule_string(ratchet, "baseline_grew_message"),
        zero_files_message=rule_string(ratchet, "zero_files_message"),
        baseline_header=(
            f"# SPDX-FileCopyrightText: {rule_string(ratchet, 'baseline_spdx_copyright')}\n"
            f"# SPDX-License-Identifier: {rule_string(ratchet, 'baseline_spdx_license')}\n"
            + rule_string(ratchet, "baseline_header")
        ),
        ok_message=rule_string(summary, "ok_message"),
        fail_message=rule_string(summary, "fail_message"),
    )


@cache
def load_dependency_direction_rules() -> ModelDependencyDirectionRules:
    """The rules shipped inside the package."""
    contract = load_dependency_direction_contract()
    return rules_from_rows({row.rule_id: row for row in contract.rules})


def load_layer_map() -> ModelRepoLayerMap:
    """Read the declared layer order shipped inside the package."""
    return load_yaml_content_as_model(
        resources.files("omnibase_core")
        .joinpath("contracts/repo_layers.yaml")
        .read_text("utf-8"),
        ModelRepoLayerMap,
    )


def infer_repo(
    root: Path,
    layer_map: ModelRepoLayerMap,
    rules: ModelDependencyDirectionRules | None = None,
) -> str:
    """The repository at ``root``: pyproject distribution, then origin URL, then dirname."""
    rules = rules or load_dependency_direction_rules()
    separator = rules.name_separator_pattern
    pyproject = root / rules.pyproject_name
    if pyproject.is_file():
        name = (
            tomllib.loads(pyproject.read_text("utf-8")).get("project", {}).get("name")
        )
        if isinstance(name, str):
            norm = re.sub(separator, "-", name).lower()
            for entry in layer_map.repos:
                dists = {re.sub(separator, "-", d).lower() for d in entry.distributions}
                if norm in dists:
                    return entry.repo
    origin = subprocess.run(
        ["git", "-C", str(root), "config", "--get", "remote.origin.url"],
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()
    if origin:
        return origin.rstrip("/").rsplit("/", 1)[-1].removesuffix(".git")
    return root.resolve().name
