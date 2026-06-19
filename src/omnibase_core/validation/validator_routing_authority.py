# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ValidatorRoutingAuthority — pre-commit CLI wrapper for the routing-authority gate.

Thin EFFECT boundary: reads files from the filesystem and delegates to the pure
COMPUTE handler ``NodeRoutingAuthorityCheckCompute``. The handler itself never
reads the filesystem (COMPUTE purity constraint).

This file replaces omnimarket/scripts/ci/check_routing_authority.py.
The canonical logic now lives in:
    omnibase_core.nodes.node_routing_authority_check_compute.handler

See: OMN-13306 (W6b), OMN-12821, OMN-12877, OMN-12883

Suppression: add ``# contract-config-ok`` on an exempted line.

Usage (pre-commit hook):
    python -m omnibase_core.validation.validator_routing_authority \\
        --repo-root . \\
        --contract src/omnimarket/nodes/node_generation_consumer/contract.yaml \\
        --source src/omnimarket/nodes/node_generation_consumer/handlers/handler_generation_consumer.py \\
        --bifrost src/omnimarket/configs/bifrost_delegation.yaml

Usage (enforce mode, exit 1 on failure):
    python -m omnibase_core.validation.validator_routing_authority --enforce

Usage (JSON evidence packet):
    python -m omnibase_core.validation.validator_routing_authority --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import cast

from omnibase_core.nodes.node_routing_authority_check_compute.handler import (
    ModelResidueEntry,
    ModelRoutingAuthorityCheckOutput,
    check_routing_authority_at_path,
)

__all__ = ["main"]

# ---------------------------------------------------------------------------
# Default omnimarket configuration (used when no --contract/--source args given)
# ---------------------------------------------------------------------------

_DEFAULT_CONTRACTS: tuple[str, ...] = (
    "src/omnimarket/nodes/node_generation_consumer/contract.yaml",
)

_DEFAULT_SOURCES: tuple[str, ...] = (
    "src/omnimarket/nodes/node_generation_consumer/handlers/handler_generation_consumer.py",
    "src/omnimarket/nodes/node_llm_delegation_call_effect/handlers/handler_inference_intent.py",
    "src/omnimarket/adapters/llm/bifrost/config_loader_bifrost_delegation.py",
)

_DEFAULT_BIFROST = "src/omnimarket/configs/bifrost_delegation.yaml"

_DEFAULT_RESIDUE: tuple[ModelResidueEntry, ...] = (
    ModelResidueEntry(
        file_rel="src/omnimarket/inference/bridge_config_loader.py",
        baseline_count=2,
        debt_ticket="OMN-12877",
        description="bootstrap config loader reads LLM_*_URL and LLM_*_MODEL_NAME from env vars",
    ),
    ModelResidueEntry(
        file_rel="src/omnimarket/cli/cli_ab_compare_suite.py",
        baseline_count=2,
        debt_ticket="OMN-12877",
        description="CLI A/B compare suite reads LLM_GLM_URL and LLM_GLM_MODEL_NAME directly",
    ),
)

_DEFAULT_YAML_RESIDUE: tuple[ModelResidueEntry, ...] = (
    ModelResidueEntry(
        file_rel="src/omnimarket/model_policy.yaml",
        baseline_count=6,
        debt_ticket="OMN-12877",
        description=(
            "model_policy.yaml carries 6 env_var declarations superseded by bifrost authority"
        ),
    ),
)


# ---------------------------------------------------------------------------
# Repo-root detection
# ---------------------------------------------------------------------------


def _find_repo_root(start: Path) -> Path:
    candidate = start
    while candidate != candidate.parent:
        if (candidate / ".git").exists():
            return candidate
        candidate = candidate.parent
    return start


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------


def _print_result(result: ModelRoutingAuthorityCheckOutput) -> None:
    if result.passed:
        entries = cast(
            list[dict[str, object]], result.positive_proof.get("entries", [])
        )
        residue_files = len(cast(list[object], result.residue_audit.get("files", [])))
        shape_backends = len(
            cast(
                list[object],
                result.provider_endpoint_shape_audit.get("backends", []),
            )
        )
        print(
            "[routing-authority-gate] PASS — "
            f"{len(entries)} demo-path entry(ies) resolve from authority; "
            f"negative audit clean; "
            f"{residue_files} residue file(s) within baseline; "
            f"{shape_backends} backend(s) shape-compliant."
        )
        for entry in entries:
            print(
                f"  {entry['contract']}: provider={entry['provider']!r} "
                f"model={entry['model']!r} endpoint_ref={entry['endpoint_ref']!r} "
                f"route_source={entry['route_source']!r}"
            )
        return

    print("[routing-authority-gate] FAIL")
    positive_errors = cast(list[object], result.positive_proof.get("errors", []))
    negative_errors = cast(list[object], result.negative_audit.get("errors", []))
    negative_files = cast(
        list[dict[str, object]], result.negative_audit.get("files", [])
    )
    residue_errors = cast(list[object], result.residue_audit.get("errors", []))
    residue_violations = cast(
        list[object], result.residue_audit.get("new_violations", [])
    )
    shape_violations = cast(
        list[object], result.provider_endpoint_shape_audit.get("violations", [])
    )
    for err in positive_errors:
        print(f"  positive-proof error: {err}")
    for err in negative_errors:
        print(f"  negative-audit error: {err}")
    for fr in negative_files:
        violations = cast(list[object], fr.get("violations", []))
        for v in violations:
            print(f"  negative-audit violation: {v}")
    for err in residue_errors:
        print(f"  residue-audit error: {err}")
    for v in residue_violations:
        print(f"  residue-audit new violation: {v}")
    for v in shape_violations:
        print(f"  shape-audit violation: {v}")
    print(
        "\nFix: every demo-path routing field must resolve from contract / "
        "overlay / routing authority; no env reads / provider literals / "
        "fallback endpoint strings on the demo path. Residue files must not "
        "exceed their baselined violation counts. Bifrost backends must "
        "respect provider-class endpoint URL shape rules (OMN-12815/13160)."
    )


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Routing-authority verification gate (OMN-13306/12821/12877/12883)"
    )
    parser.add_argument(
        "--repo-root",
        default="",
        help="Repository root. Defaults to auto-detected git root from cwd.",
    )
    parser.add_argument(
        "--contract",
        dest="contracts",
        action="append",
        default=[],
        metavar="REL",
        help="Demo-path contract to verify (relative to repo-root). "
        "Repeatable. Defaults to omnimarket defaults when omitted.",
    )
    parser.add_argument(
        "--source",
        dest="sources",
        action="append",
        default=[],
        metavar="REL",
        help="Demo-path source file for negative audit (relative to repo-root). "
        "Repeatable. Defaults to omnimarket defaults when omitted.",
    )
    parser.add_argument(
        "--bifrost",
        default="",
        metavar="REL",
        help="Bifrost delegation config relative to repo-root. "
        f"Defaults to {_DEFAULT_BIFROST!r}.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print full evidence packet as JSON (gate exit code still applies).",
    )
    parser.add_argument(
        "--emit",
        default="",
        metavar="PATH",
        help="Write evidence packet JSON to PATH.",
    )
    parser.add_argument(
        "--no-default-residue",
        action="store_true",
        help="Suppress the default omnimarket residue ratchet entries.",
    )
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root) if args.repo_root else _find_repo_root(Path.cwd())

    contracts: tuple[str, ...] = (
        tuple(args.contracts) if args.contracts else _DEFAULT_CONTRACTS
    )
    sources: tuple[str, ...] = tuple(args.sources) if args.sources else _DEFAULT_SOURCES
    bifrost_rel = args.bifrost or _DEFAULT_BIFROST
    residue = () if args.no_default_residue else _DEFAULT_RESIDUE
    yaml_residue = () if args.no_default_residue else _DEFAULT_YAML_RESIDUE

    result = check_routing_authority_at_path(
        repo_root=repo_root,
        demo_path_contracts=contracts,
        demo_path_sources=sources,
        residue_entries=residue,
        yaml_policy_residue=yaml_residue,
        bifrost_config_rel=bifrost_rel,
    )

    if args.emit:
        out = Path(args.emit)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps(result.model_dump(), indent=2, sort_keys=True), encoding="utf-8"
        )

    if args.json:
        print(json.dumps(result.model_dump(), indent=2, sort_keys=True))
        return 0 if result.passed else 1

    _print_result(result)
    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
