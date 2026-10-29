# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLI runtime for the cross-repository dependency-direction check (OMN-19998).

Backs the ``check-dependency-direction`` pre-commit hook, the reusable
``dependency-direction.yml`` workflow every repository inherits, and manual
runs. All I/O happens here, at the CLI boundary: the tracked-file listing
(``node_git_file_listing_effect``), file reads (``node_source_file_gather_effect``),
the layer map and baseline YAML, the base-ref baseline read for the
shrink-only ratchet, and the report write (``node_validation_report_write_effect``,
which also writes the validator run and fire events beside ``--report-json``).
The verdict is the pure ``HandlerDependencyDirection``.

Usage::

    check-dependency-direction                          # full tree, repo inferred
    check-dependency-direction --repo omnibase_infra --root ../omnibase_infra
    check-dependency-direction path/a.py Dockerfile     # pre-commit staged files
    check-dependency-direction --ratchet-base-ref origin/dev --report-json r.json
    check-dependency-direction --write-baseline --ticket OMN-19998

Exit codes: 0 -- PASS or WARN only; 1 -- FAIL/ERROR, or the baseline grew.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Final

import yaml

from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.dependency_direction.model_dependency_direction_baseline import (
    ModelDependencyDirectionBaseline,
)
from omnibase_core.models.dependency_direction.model_dependency_direction_baseline_entry import (
    ModelDependencyDirectionBaselineEntry,
)
from omnibase_core.models.dependency_direction.model_dependency_direction_check_input import (
    ModelDependencyDirectionCheckInput,
)
from omnibase_core.models.dependency_direction.model_dependency_direction_rules import (
    ModelDependencyDirectionRules,
)
from omnibase_core.models.dependency_direction.model_repo_layer_map import (
    ModelRepoLayerMap,
)
from omnibase_core.models.nodes.git_file_listing.model_git_file_listing_input import (
    ModelGitFileListingInput,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import (
    ModelSourceFile,
)
from omnibase_core.models.nodes.source_file_gather.model_source_file_gather_input import (
    ModelSourceFileGatherInput,
)
from omnibase_core.models.nodes.validation_report_write.model_validation_report_write_input import (
    ModelValidationReportWriteInput,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.nodes.node_dependency_direction_check_effect.handler_dependency_direction import (
    HandlerDependencyDirection,
)
from omnibase_core.nodes.node_dependency_direction_check_effect.matcher_dependency_direction import (
    VALIDATOR_ID,
    extract_references,
    is_candidate,
)
from omnibase_core.nodes.node_git_file_listing_effect.handler import (
    NodeGitFileListingEffect,
)
from omnibase_core.nodes.node_source_file_gather_effect.handler import (
    NodeSourceFileGatherEffect,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler import (
    NodeValidationReportWriteEffect,
)
from omnibase_core.utils.util_run_coro_sync import run_coro_sync
from omnibase_core.utils.util_safe_yaml_loader import (
    load_yaml_content_as_model,
)
from omnibase_core.validation.checker_dependency_direction import (
    infer_repo,
    load_dependency_direction_rules,
    load_layer_map,
)

__all__ = ["main"]

DEFAULT_BASELINE: Final[str] = ".onex_ratchets/dependency_direction_baseline.yaml"


def parse_baseline(
    text: str | None,
) -> tuple[ModelDependencyDirectionBaselineEntry, ...]:
    """Baseline entries from the YAML text of a baseline file (None means absent)."""
    if not text:
        return ()
    return load_yaml_content_as_model(text, ModelDependencyDirectionBaseline).violations


def gather(
    root: Path, filenames: list[str], rules: ModelDependencyDirectionRules
) -> tuple[list[ModelSourceFile], list[str]]:
    """Repository-relative (path, source) pairs of the candidate files."""
    if filenames:
        relative = [f for f in filenames if is_candidate(f, rules)]
    else:
        listing = NodeGitFileListingEffect().handle(
            ModelGitFileListingInput(root=root, scope="tracked")
        )
        relative = [p for p in listing.paths if is_candidate(p, rules)]
    output = NodeSourceFileGatherEffect().handle(
        ModelSourceFileGatherInput(
            root=str(root),
            explicit_paths=[str(root / p) for p in relative],
            include_patterns=["*"],
            decode_errors="replace",
        )
    )
    prefix = str(root) + "/"
    files = [
        ModelSourceFile(path=f.path.removeprefix(prefix), source=f.source)
        for f in output.files
    ]
    errors = [
        f"{s.path.removeprefix(prefix)}: {s.reason}"
        for s in output.skipped
        if s.reason.startswith("read error:")
    ]
    return files, errors


def _ref_exists(root: Path, ref: str) -> bool:
    return (
        subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "rev-parse",
                "--verify",
                "--quiet",
                f"{ref}^{{commit}}",
            ],
            capture_output=True,
            text=True,
            check=False,
        ).returncode
        == 0
    )


def _base_baseline(root: Path, ref: str, baseline: str) -> str | None:
    shown = subprocess.run(
        ["git", "-C", str(root), "show", f"{ref}:{baseline}"],
        capture_output=True,
        text=True,
        check=False,
    )
    return shown.stdout if shown.returncode == 0 else None


def baseline_growth(
    current: tuple[ModelDependencyDirectionBaselineEntry, ...],
    base: tuple[ModelDependencyDirectionBaselineEntry, ...] | None,
    rules: ModelDependencyDirectionRules,
) -> list[str]:
    """Entries the current baseline adds over the base (shrink-only ratchet).

    A base with no baseline file (None) is the introduction and adds nothing.
    """
    if base is None:
        return []
    base_keys = {entry.key() for entry in base}
    return [
        rules.baseline_grew_message.format(
            path=e.path, channel=e.channel.value, target=e.target
        )
        for e in current
        if e.key() not in base_keys
    ]


def render_baseline(
    repo: str,
    files: list[ModelSourceFile],
    layer_map: ModelRepoLayerMap,
    ticket: str,
    rules: ModelDependencyDirectionRules,
) -> str:
    """A baseline YAML recording every current violation of ``repo``."""
    own = layer_map.get(repo)
    layers = {e.repo: e.layer for e in layer_map.repos}
    keys: set[tuple[str, str, str]] = set()
    for file in files:
        for channel, target, _line, _evidence in extract_references(
            file.path, file.source, layer_map, repo, rules
        ):
            if own is not None and layers[target] >= own.layer:
                keys.add((file.path, channel.value, target))
    violations = [
        {"path": p, "channel": c, "target": t, "ticket": ticket}
        for p, c, t in sorted(keys)
    ]
    return rules.baseline_header + yaml.safe_dump(
        {"repo": repo, "violations": violations}, sort_keys=False
    )


def _out(line: str) -> None:
    sys.stdout.write(line + "\n")


def build_container() -> ModelONEXContainer:
    """The composition root: a container with the report writer registered."""
    container = ModelONEXContainer(enable_service_registry=False)
    registry = container.initialize_service_registry()
    run_coro_sync(
        registry.register_instance(
            NodeValidationReportWriteEffect, NodeValidationReportWriteEffect()
        )
    )
    return container


def _write_report(
    container: ModelONEXContainer, path: str | None, report: ModelValidationReport
) -> None:
    if path is not None:
        container.get_service(NodeValidationReportWriteEffect).handle(
            ModelValidationReportWriteInput(report_path=path, report=report)
        )


def main(
    argv: list[str] | None = None, container: ModelONEXContainer | None = None
) -> int:
    """CLI entry. Returns 0 on PASS/WARN, 1 on FAIL/ERROR or baseline growth."""
    parser = argparse.ArgumentParser(
        prog="check-dependency-direction",
        description=(
            "Refuse a dependency on a repository at the same or a higher layer "
            "(OMN-19998)."
        ),
    )
    parser.add_argument("filenames", nargs="*", help="Staged files (pre-commit mode).")
    parser.add_argument("--root", default=".", help="Repository root (default: .)")
    parser.add_argument(
        "--repo", default=None, help="Repository name (default: inferred)"
    )
    parser.add_argument(
        "--baseline",
        default=DEFAULT_BASELINE,
        help=f"Baseline path relative to --root (default: {DEFAULT_BASELINE})",
    )
    parser.add_argument(
        "--ratchet-base-ref",
        default=None,
        help="Refuse baseline entries this ref's baseline does not have.",
    )
    parser.add_argument(
        "--report-json", default=None, help="Write the report JSON here."
    )
    parser.add_argument(
        "--write-baseline",
        action="store_true",
        help="Print a baseline recording every current violation, then exit 0.",
    )
    parser.add_argument(
        "--ticket", default="OMN-19998", help="Ticket for --write-baseline"
    )
    parsed = parser.parse_args(argv)

    rules = load_dependency_direction_rules()
    container = container or build_container()
    root = Path(parsed.root).resolve()
    layer_map = load_layer_map()
    repo = parsed.repo or infer_repo(root, layer_map, rules)
    files, read_errors = gather(root, parsed.filenames, rules)

    if parsed.write_baseline:
        sys.stdout.write(render_baseline(repo, files, layer_map, parsed.ticket, rules))
        return 0

    baseline_file = root / parsed.baseline
    baseline_text = (
        baseline_file.read_text("utf-8") if baseline_file.is_file() else None
    )
    baseline = parse_baseline(baseline_text)

    runtime_errors = list(read_errors)
    if parsed.ratchet_base_ref and not _ref_exists(root, parsed.ratchet_base_ref):
        runtime_errors.append(
            rules.ratchet_ref_missing_message.format(ref=parsed.ratchet_base_ref)
        )
    elif parsed.ratchet_base_ref:
        base_text = _base_baseline(root, parsed.ratchet_base_ref, parsed.baseline)
        base = parse_baseline(base_text) if base_text is not None else None
        runtime_errors.extend(baseline_growth(baseline, base, rules))
    if not parsed.filenames and not files:
        runtime_errors.append(rules.zero_files_message.format(root=root))
    if runtime_errors:
        report = ModelValidationReport.from_runtime_errors(
            VALIDATOR_ID, tuple(runtime_errors)
        )
        _write_report(container, parsed.report_json, report)
        for message in runtime_errors:
            _out(f"ERROR: {message}")
        return 1

    report = HandlerDependencyDirection().handle(
        ModelDependencyDirectionCheckInput(
            repo=repo,
            layer_map=layer_map,
            files=tuple(files),
            baseline=baseline,
            rules=rules,
            report_stale_baseline=not parsed.filenames,
        )
    )
    _write_report(container, parsed.report_json, report)

    for finding in report.findings:
        _out(f"{finding.severity}: {finding.message}")
    if report.overall_status in ("PASS", "WARN"):
        _out(rules.ok_message.format(repo=repo, count=len(files)))
        return 0
    _out(rules.fail_message.format(status=report.overall_status, repo=repo))
    return 1


if __name__ == "__main__":
    sys.exit(main())
