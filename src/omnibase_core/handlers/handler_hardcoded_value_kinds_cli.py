# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLI of the shrink-only hard-coded-value rules (OMN-21503, plan task T-Q6).

Runs one kind of hard-coded value over a tree, judges it against the kind's own
committed baseline and fails a finding the baseline does not cover, or a baseline
that grew against ``--previous-baseline``. The kinds that run through the
existing validators are:

* ``host_list``: the ``hardcoded_host_list`` rule of the hardcoded-topics validator.
* ``threshold``: the ``hardcoded_threshold`` rule of the contract-config-compliance
  validator.

Ruling stamps and model or host names are family S, M and D of the
hardcoded-model-config validator, whose baseline is its own committed file.
Usage::

    check-hardcoded-value-kind --kind threshold --baseline config/<file> src/
"""

from __future__ import annotations

import argparse
import ast
import sys
from collections.abc import Sequence
from pathlib import Path

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.handlers.handler_hardcoded_host_list import (
    add_baseline_arguments,
    apply_baseline_to_result,
)
from omnibase_core.handlers.handler_hardcoded_threshold import (
    EXCLUDED_PATH_PARTS,
    THRESHOLD_RULE_ID,
    load_contract_text,
    load_packaged_contract,
    threshold_findings,
    threshold_rule,
)
from omnibase_core.handlers.handler_shrink_only_baseline import (
    finding_fingerprint,
    load_fingerprint_baseline,
    unbaselined_mask,
    verdict_issues,
)
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.validation.model_contract_config_compliance_finding import (
    ModelContractConfigComplianceFinding,
)
from omnibase_core.validation.validator_hardcoded_topics import ValidatorHardcodedTopics
from omnibase_core.validators.contract_config_compliance import SUPPRESSION_MARKER

__all__ = ["main"]

HOST_LIST_RULE_ID = "hardcoded_host_list"
_KINDS = ("host_list", "threshold")


def _python_files(paths: Sequence[Path]) -> list[Path]:
    found: list[Path] = []
    for path in paths:
        if path.is_dir():
            found.extend(
                p
                for p in sorted(path.rglob("*.py"))
                if not EXCLUDED_PATH_PARTS & set(p.parts)
            )
        elif path.suffix == ".py":
            found.append(path)
    return found


def _run_host_list(args: argparse.Namespace) -> int:
    validator = ValidatorHardcodedTopics(
        contract=(
            load_contract_text(args.contract.read_text(encoding="utf-8"))
            if args.contract
            else None
        )
    )
    result = apply_baseline_to_result(
        validator.contract,
        validator.validate(list(args.paths)),
        args,
        HOST_LIST_RULE_ID,
    )
    own = [i for i in result.issues if i.code in {HOST_LIST_RULE_ID, "baseline_added"}]
    own += [i for i in result.issues if i.code == "baseline_raised"]
    for issue in own:
        sys.stderr.write(f"{issue.file_path}:{issue.line_number}: {issue.message}\n")
    return 1 if own else 0


def _run_threshold(args: argparse.Namespace) -> int:
    contract: ModelValidatorSubcontract = (
        load_contract_text(args.contract.read_text(encoding="utf-8"))
        if args.contract
        else load_packaged_contract("contract_config_compliance")
    )
    rule = threshold_rule(contract)
    if rule is None:
        return 0
    findings: list[ModelContractConfigComplianceFinding] = []
    for path in _python_files(args.paths):
        source = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError:
            continue
        findings.extend(
            threshold_findings(
                path=path,
                tree=tree,
                lines=source.splitlines(),
                rule=rule,
                suppression_marker=SUPPRESSION_MARKER,
            )
        )
    configured = (rule.parameters or {}).get("baseline_path")
    baseline_path = args.baseline or (
        Path(configured) if isinstance(configured, str) and configured else None
    )
    baseline = (
        load_fingerprint_baseline(baseline_path, THRESHOLD_RULE_ID)
        if baseline_path and (args.baseline or baseline_path.exists())
        else []
    )
    previous = (
        load_fingerprint_baseline(args.previous_baseline, THRESHOLD_RULE_ID)
        if args.previous_baseline
        else None
    )
    fingerprints = [finding_fingerprint(f.rule, f.path, f.line) for f in findings]
    mask, verdict = unbaselined_mask(
        THRESHOLD_RULE_ID, fingerprints, baseline, previous
    )
    new = [f for f, is_new in zip(findings, mask, strict=True) if is_new]
    for finding in new:
        sys.stderr.write(f"{finding.format()}\n")
    raised = verdict_issues(
        verdict.model_copy(update={"added": ()}), baseline_path=baseline_path
    )
    for issue in raised:
        sys.stderr.write(f"{issue.message}\n")
    return 1 if new or raised else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Hard-coded value kind ratchet")
    parser.add_argument("--kind", choices=_KINDS, required=True)
    parser.add_argument("paths", nargs="*", type=Path, default=[Path()])
    parser.add_argument("--contract", type=Path, default=None)
    add_baseline_arguments(parser)
    args = parser.parse_args(argv)
    try:
        return (
            _run_host_list(args) if args.kind == "host_list" else _run_threshold(args)
        )
    except (OSError, ValueError, ModelOnexError) as exc:
        sys.stderr.write(f"Baseline error: {exc}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
