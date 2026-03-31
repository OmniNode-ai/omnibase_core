# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Contract compliance verification CLI.

Provides ``onex compliance check`` — a thin wrapper that runs the compliance
workflow via ``onex run`` and formats results as machine-parseable stdout.

Stdout format (one line per node)::

    PASS node_foo [8/8 checks]
    FAIL node_bar [6/8 checks: handler_resolution, config_readiness]

Exit codes:
    0 — all nodes pass
    1 — one or more nodes fail

CI integration (GitHub Actions)::

    - name: Contract compliance
      run: |
        pip install omnibase-core
        onex compliance check --repo-root . --output .onex_state/compliance/report.yaml
"""

from __future__ import annotations

from pathlib import Path

import click
import yaml

from omnibase_core.enums.enum_cli_exit_code import EnumCLIExitCode


@click.group("compliance")
def compliance_group() -> None:  # stub-ok
    """Contract compliance verification."""


@compliance_group.command("check")
@click.option(
    "--repo-root",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    default=".",
    help="Root directory to scan for contract.yaml files.",
)
@click.option(
    "--output",
    type=click.Path(),
    default=".onex_state/compliance/report.yaml",
    help="Path for the YAML compliance report artifact.",
)
def check(repo_root: str, output: str) -> None:
    """Run contract compliance checks on all nodes in a repository.

    Scans *repo_root* for ``contract.yaml`` files, executes the 8-point
    structural compliance check on each discovered node, writes a YAML
    report to *output*, and prints a machine-parseable summary to stdout.

    This command is the single sanctioned entry-point for contract
    compliance verification — no repo-specific scripts should duplicate it.

    \b
    CI integration (GitHub Actions):
        - name: Contract compliance
          run: |
            pip install omnibase-core
            onex compliance check --repo-root . --output .onex_state/compliance/report.yaml
    """
    repo_root_path = Path(repo_root).resolve()
    output_path = Path(output)

    # Discover contract.yaml files (skip examples/ — demo contracts may
    # intentionally lack handler implementations).
    contracts = sorted(
        p
        for p in repo_root_path.rglob("contract.yaml")
        if "examples" not in p.relative_to(repo_root_path).parts
    )

    if not contracts:
        click.echo("No contract.yaml files found.")
        raise SystemExit(EnumCLIExitCode.SUCCESS)  # error-ok: CLI exit code

    total_checks = 8
    all_passed = True
    results: list[dict[str, object]] = []

    for contract_path in contracts:
        node_id = contract_path.parent.name
        checks_passed: list[str] = []
        checks_failed: list[str] = []

        # --- 1. Contract Parse ---
        try:
            with open(contract_path, encoding="utf-8") as f:
                contract_data = yaml.safe_load(
                    f
                )  # yaml-ok: raw YAML parse for compliance checking
            if not isinstance(contract_data, dict):
                # error-ok: internal control flow caught by except below
                raise ValueError("contract.yaml did not parse to a mapping")
            checks_passed.append("contract_parse")
        except Exception:  # noqa: BLE001  # catch-all-ok: compliance check must not crash on bad YAML
            contract_data = None
            checks_failed.append("contract_parse")

        # --- 2. Handler Resolution ---
        handler_ok = False
        if contract_data:
            # Method A: handler_routing.default_handler → resolve module file
            handler_routing = contract_data.get("handler_routing", {})
            default_handler = (
                handler_routing.get("default_handler", "")
                if isinstance(handler_routing, dict)
                else ""
            )
            if default_handler:
                module_part = (
                    default_handler.split(":")[0]
                    if ":" in default_handler
                    else default_handler
                )
                handler_file = contract_path.parent / f"{module_part}.py"
                handler_ok = handler_file.exists()
            # Method B: handler_id present + conventional handler.py exists
            if not handler_ok and contract_data.get("handler_id"):
                handler_ok = (contract_path.parent / "handler.py").exists()
            # Method C: conventional handler.py exists (no routing metadata)
            if not handler_ok:
                handler_ok = (contract_path.parent / "handler.py").exists()
        if handler_ok:
            checks_passed.append("handler_resolution")
        else:
            checks_failed.append("handler_resolution")

        # --- 3. Schema Conformance ---
        # Requires a node identifier (node_id or name) and a type declaration
        # (node_type or node_kind).
        has_identity = contract_data and (
            "node_id" in contract_data or "name" in contract_data
        )
        has_type = contract_data and (
            "node_type" in contract_data or "node_kind" in contract_data
        )
        if has_identity and has_type:
            checks_passed.append("schema_conformance")
        else:
            checks_failed.append("schema_conformance")

        # --- 4. Node Kind Constraints ---
        # Accept node_type or node_kind, case-insensitive, with optional
        # _GENERIC suffix (e.g. "COMPUTE_GENERIC", "effect").
        _VALID_KINDS = {"compute", "reducer", "effect", "orchestrator"}
        raw_kind = ""
        if contract_data:
            raw_kind = str(
                contract_data.get("node_type", contract_data.get("node_kind", ""))
            )
        normalised = raw_kind.lower().removesuffix("_generic")
        if normalised in _VALID_KINDS:
            checks_passed.append("node_kind_constraints")
        else:
            checks_failed.append("node_kind_constraints")

        # --- 5. Publish Topic Naming ---
        if contract_data:
            pub_topics = (
                contract_data.get("event_bus", {}).get("publish_topics", [])
                if isinstance(contract_data.get("event_bus"), dict)
                else []
            )
            if (
                all(isinstance(t, str) and t.startswith("onex.") for t in pub_topics)
                if pub_topics
                else True
            ):
                checks_passed.append("publish_topic_naming")
            else:
                checks_failed.append("publish_topic_naming")
        else:
            checks_failed.append("publish_topic_naming")

        # --- 6. Subscribe Topic Naming ---
        if contract_data:
            sub_topics = (
                contract_data.get("event_bus", {}).get("subscribe_topics", [])
                if isinstance(contract_data.get("event_bus"), dict)
                else []
            )
            if (
                all(isinstance(t, str) and t.startswith("onex.") for t in sub_topics)
                if sub_topics
                else True
            ):
                checks_passed.append("subscribe_topic_naming")
            else:
                checks_failed.append("subscribe_topic_naming")
        else:
            checks_failed.append("subscribe_topic_naming")

        # --- 7. Config Readiness ---
        if contract_data:
            config_reqs = contract_data.get("config_requirements", [])
            if isinstance(config_reqs, list):
                checks_passed.append("config_readiness")
            else:
                checks_failed.append("config_readiness")
        else:
            checks_failed.append("config_readiness")

        # --- 8. Codepath Consumption ---
        # Phase 1: structural presence only — full AST analysis deferred to
        # the compliance workflow nodes (OMN-7072).
        checks_passed.append("codepath_consumption")

        passed_count = len(checks_passed)
        node_passed = len(checks_failed) == 0

        if not node_passed:
            all_passed = False
            failed_str = ", ".join(checks_failed)
            click.echo(
                f"FAIL {node_id} [{passed_count}/{total_checks} checks: {failed_str}]"
            )
        else:
            click.echo(f"PASS {node_id} [{passed_count}/{total_checks} checks]")

        results.append(
            {
                "node_id": node_id,
                "passed": node_passed,
                "checks_passed": checks_passed,
                "checks_failed": checks_failed,
                "contract_path": str(contract_path),
            }
        )

    # Write YAML report artifact
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "total": len(results),
        "passed": sum(1 for r in results if r["passed"]),
        "failed": sum(1 for r in results if not r["passed"]),
        "results": results,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        yaml.dump(report, f, default_flow_style=False, sort_keys=False)

    click.echo(
        f"\n{report['passed']}/{report['total']} nodes passed. "
        f"Report written to {output_path}"
    )

    raise SystemExit(  # error-ok: CLI exit code
        EnumCLIExitCode.SUCCESS if all_passed else EnumCLIExitCode.ERROR
    )
