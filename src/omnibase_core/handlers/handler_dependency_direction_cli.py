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
import re
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Final

import yaml

from omnibase_core.handlers.handler_dependency_direction import (
    HandlerDependencyDirection,
)
from omnibase_core.handlers.handler_dependency_direction_rules import (
    VALIDATOR_ID,
    extract_references,
    is_candidate,
)
from omnibase_core.models.dependency_direction.model_dependency_direction_baseline import (
    ModelDependencyDirectionBaseline,
)
from omnibase_core.models.dependency_direction.model_dependency_direction_baseline_entry import (
    ModelDependencyDirectionBaselineEntry,
)
from omnibase_core.models.dependency_direction.model_dependency_direction_check_input import (
    ModelDependencyDirectionCheckInput,
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
from omnibase_core.nodes.node_git_file_listing_effect.handler import (
    NodeGitFileListingEffect,
)
from omnibase_core.nodes.node_source_file_gather_effect.handler import (
    NodeSourceFileGatherEffect,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler import (
    NodeValidationReportWriteEffect,
)
from omnibase_core.utils.util_safe_yaml_loader import (
    load_and_validate_yaml_model,
    load_yaml_content_as_model,
)

__all__ = ["main"]

DEFAULT_BASELINE: Final[str] = ".onex_ratchets/dependency_direction_baseline.yaml"
LAYER_MAP_PATH: Final[Path] = (
    Path(__file__).parent.parent / "contracts" / "repo_layers.yaml"
)


def load_layer_map(path: Path = LAYER_MAP_PATH) -> ModelRepoLayerMap:
    """Read the declared layer order."""
    return load_and_validate_yaml_model(path, ModelRepoLayerMap)


def parse_baseline(
    text: str | None,
) -> tuple[ModelDependencyDirectionBaselineEntry, ...]:
    """Baseline entries from the YAML text of a baseline file (None means absent)."""
    if not text:
        return ()
    return load_yaml_content_as_model(text, ModelDependencyDirectionBaseline).violations


def infer_repo(root: Path, layer_map: ModelRepoLayerMap) -> str:
    """The repository at ``root``: pyproject distribution, then origin URL, then dirname."""
    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        name = (
            tomllib.loads(pyproject.read_text("utf-8")).get("project", {}).get("name")
        )
        if isinstance(name, str):
            norm = re.sub(r"[-_.]+", "-", name).lower()
            for entry in layer_map.repos:
                dists = {re.sub(r"[-_.]+", "-", d).lower() for d in entry.distributions}
                if norm in dists:
                    return entry.repo
    origin = subprocess.run(
        ["git", "-C", str(root), "config", "--get", "remote.origin.url"],
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()
    if origin:
        return re.sub(r"\.git$", "", origin.rstrip("/").rsplit("/", 1)[-1])
    return root.resolve().name


def gather(root: Path, filenames: list[str]) -> tuple[list[ModelSourceFile], list[str]]:
    """Repository-relative (path, source) pairs of the candidate files."""
    if filenames:
        relative = [f for f in filenames if is_candidate(f)]
    else:
        listing = NodeGitFileListingEffect().handle(
            ModelGitFileListingInput(root=root, scope="tracked")
        )
        relative = [p for p in listing.paths if is_candidate(p)]
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
) -> list[str]:
    """Entries the current baseline adds over the base (shrink-only ratchet).

    A base with no baseline file (None) is the introduction and adds nothing.
    """
    if base is None:
        return []
    base_keys = {entry.key() for entry in base}
    return [
        f"baseline grew: {e.path} {e.channel.value} {e.target} is not in the base baseline"
        for e in current
        if e.key() not in base_keys
    ]


def render_baseline(
    repo: str,
    files: list[ModelSourceFile],
    layer_map: ModelRepoLayerMap,
    ticket: str,
) -> str:
    """A baseline YAML recording every current violation of ``repo``."""
    own = layer_map.get(repo)
    layers = {e.repo: e.layer for e in layer_map.repos}
    keys: set[tuple[str, str, str]] = set()
    for file in files:
        for channel, target, _line, _evidence in extract_references(
            file.path, file.source, layer_map, repo
        ):
            if own is not None and layers[target] >= own.layer:
                keys.add((file.path, channel.value, target))
    violations = [
        {"path": p, "channel": c, "target": t, "ticket": ticket}
        for p, c, t in sorted(keys)
    ]
    header = (
        "# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.\n"
        "# SPDX-License-Identifier: MIT\n"
        "# Cross-repository dependency-direction baseline (OMN-19998).\n"
        "# Shrink-only: CI refuses an entry the base branch does not have.\n"
        "# Each entry is a pre-existing violation and the ticket that removes it.\n"
    )
    return header + yaml.safe_dump(
        {"repo": repo, "violations": violations}, sort_keys=False
    )


def _out(line: str) -> None:
    sys.stdout.write(line + "\n")


def _write_report(path: str | None, report: ModelValidationReport) -> None:
    if path is not None:
        NodeValidationReportWriteEffect().handle(
            ModelValidationReportWriteInput(report_path=path, report=report)
        )


def main(argv: list[str] | None = None) -> int:
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

    root = Path(parsed.root).resolve()
    layer_map = load_layer_map()
    repo = parsed.repo or infer_repo(root, layer_map)
    files, read_errors = gather(root, parsed.filenames)

    if parsed.write_baseline:
        sys.stdout.write(render_baseline(repo, files, layer_map, parsed.ticket))
        return 0

    baseline_file = root / parsed.baseline
    baseline_text = (
        baseline_file.read_text("utf-8") if baseline_file.is_file() else None
    )
    baseline = parse_baseline(baseline_text)

    runtime_errors = list(read_errors)
    if parsed.ratchet_base_ref and not _ref_exists(root, parsed.ratchet_base_ref):
        runtime_errors.append(
            f"ratchet base ref {parsed.ratchet_base_ref!r} is not in the clone; fetch "
            "it, since a ratchet with no base is never a pass"
        )
    elif parsed.ratchet_base_ref:
        base_text = _base_baseline(root, parsed.ratchet_base_ref, parsed.baseline)
        base = parse_baseline(base_text) if base_text is not None else None
        runtime_errors.extend(baseline_growth(baseline, base))
    if not parsed.filenames and not files:
        runtime_errors.append(
            f"zero candidate files under {root}: a full-tree run that scans "
            "nothing is ERROR, never PASS"
        )
    if runtime_errors:
        report = ModelValidationReport.from_runtime_errors(
            VALIDATOR_ID, tuple(runtime_errors)
        )
        _write_report(parsed.report_json, report)
        for message in runtime_errors:
            _out(f"ERROR: {message}")
        return 1

    report = HandlerDependencyDirection().handle(
        ModelDependencyDirectionCheckInput(
            repo=repo,
            layer_map=layer_map,
            files=tuple(files),
            baseline=baseline,
            report_stale_baseline=not parsed.filenames,
        )
    )
    _write_report(parsed.report_json, report)

    for finding in report.findings:
        _out(f"{finding.severity}: {finding.message}")
    if report.overall_status in ("PASS", "WARN"):
        _out(
            f"OK: {repo} depends on no repository at its own or a higher layer "
            f"outside its baseline ({len(files)} files scanned)"
        )
        return 0
    _out(
        f"{report.overall_status}: {repo} depends on a repository at its own or a "
        "higher layer; see omnibase_core contracts/repo_layers.yaml"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
