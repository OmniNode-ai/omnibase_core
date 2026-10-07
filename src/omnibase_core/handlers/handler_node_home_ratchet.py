# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Shrink-only node-home ratchet (OMN-20702): new nodes belong in omnimarket.

``handle`` checks supplied snapshots without I/O. The CLI reads the git index,
including Python sources and entry points, against ``--base`` (HEAD by
default). Every node directory in the tracked tree counts, including nested
nodes. Test, fixture, example, cache, docs and hidden paths are ignored.
There are no exceptions or renames: remove a retired node's baseline entry;
move new capability to omnimarket.

Usage::

    python -m omnibase_core.handlers.handler_node_home_ratchet
    python -m omnibase_core.handlers.handler_node_home_ratchet --base origin/dev
    python -m omnibase_core.handlers.handler_node_home_ratchet --write-baseline

The fixed baseline can be created once, never regenerated or widened.
"""

from __future__ import annotations

import argparse
import ast
import re
import subprocess
import sys
import tomllib
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path, PurePosixPath

from omnibase_core.models.validation.model_node_home_ratchet_finding import (
    ModelNodeHomeRatchetFinding,
)
from omnibase_core.models.validation.model_node_home_ratchet_request import (
    ModelNodeHomeRatchetRequest,
)
from omnibase_core.models.validation.model_node_home_ratchet_result import (
    ModelNodeHomeRatchetResult,
)

NODE_HOME_BASELINE = ".onex_ratchets/node_home_baseline.txt"
_IGNORED_COMPONENTS = frozenset(
    {"tests", "test", "fixtures", "examples", "__pycache__", "docs"}
)
_NODE_CLASS = re.compile(r"^Node[A-Z]\w*$")


def _eligible(path: PurePosixPath) -> bool:
    return not (_IGNORED_COMPONENTS & set(path.parts)) and not any(
        component.startswith(".") for component in path.parts
    )


def _node_directories(
    tracked_paths: Iterable[str], node_class_paths: Iterable[str]
) -> tuple[str, ...]:
    files = {
        posix_path
        for path in tracked_paths
        if _eligible(posix_path := PurePosixPath(path))
    }
    contracts = {path.parent for path in files if path.name == "contract.yaml"}
    direct_handlers = {
        path.parent
        for path in files
        if path.suffix == ".py"
        and (path.name.startswith("handler") or path.name == "node.py")
    }
    handler_subdirs = {
        parent.parent
        for path in files
        if path.suffix == ".py"
        for parent in path.parents
        if parent.name == "handlers"
    }
    nodes = {
        directory
        for directory in contracts
        if directory in direct_handlers
        or directory in handler_subdirs
        or "nodes" in directory.parts
    }
    nodes.update(
        path.parent
        for text_path in node_class_paths
        if (path := PurePosixPath(text_path)) in files
        and path.suffix == ".py"
        and (path.parent.name.startswith("node_") or path.parent in contracts)
    )
    nodes = {directory for directory in nodes if _eligible(directory)}
    return tuple(sorted(directory.as_posix() for directory in nodes))


def _entries(text: str | None) -> set[str]:
    return {
        line.strip()
        for line in (text or "").splitlines()
        if line.strip() and not line.strip().startswith("#")
    }


def handle(request: ModelNodeHomeRatchetRequest) -> ModelNodeHomeRatchetResult:
    """Check node placement and baseline shrinking using only the supplied inputs."""
    directories = _node_directories(request.tracked_paths, request.node_class_paths)
    findings: list[ModelNodeHomeRatchetFinding] = []
    nodes = set(directories)
    baseline = _entries(request.head_baseline_text)
    for path in sorted(nodes - baseline):
        findings.append(
            ModelNodeHomeRatchetFinding(
                code="node-outside-market",
                path=path,
                message="new or renamed node directory; the node moves to omnimarket instead",
            )
        )
    for path in sorted(baseline - nodes):
        findings.append(
            ModelNodeHomeRatchetFinding(
                code="baseline-stale",
                path=NODE_HOME_BASELINE,
                message=f"entry '{path}' is no longer a node directory; delete the line; a renamed node moves to omnimarket instead",
            )
        )
    allowed_baseline = (
        _entries(request.base_baseline_text)
        if request.base_baseline_text is not None
        else request.base_node_directories
    )
    for path in sorted(baseline - allowed_baseline):
        findings.append(
            ModelNodeHomeRatchetFinding(
                code="baseline-growth",
                path=NODE_HOME_BASELINE,
                message=f"entry '{path}' is new; the baseline only shrinks and bootstraps from base-revision nodes; the node moves to omnimarket instead",
            )
        )
    if request.base_baseline_text is not None and request.head_baseline_text is None:
        findings.append(
            ModelNodeHomeRatchetFinding(
                code="baseline-removed",
                path=NODE_HOME_BASELINE,
                message="the baseline file must remain, even when empty; it can only shrink",
            )
        )
    for name in sorted(request.head_entry_points - request.base_entry_points):
        findings.append(
            ModelNodeHomeRatchetFinding(
                code="entry-point-outside-market",
                path=f'pyproject.toml:project.entry-points."onex.nodes".{name}',
                message="a new onex.nodes registration outside omnimarket; register the node in omnimarket instead",
            )
        )
    return ModelNodeHomeRatchetResult(
        node_directories=directories, findings=tuple(findings)
    )


def render_baseline(paths: Iterable[str]) -> str:
    """Render the sorted initial inventory with its shrink-only instructions."""
    header = (
        "# Node-home baseline (OMN-20702). Shrink-only.\n"
        "# Pre-existing ONEX node directories outside omnimarket, one per line.\n"
        "# Delete an entry when its node is removed. New or renamed nodes move\n"
        "# to omnimarket instead. No allowlist, suppression or per-entry exemption.\n"
        "# Created once with --write-baseline; never regenerate or add entries.\n"
    )
    return header + "".join(f"{path}\n" for path in sorted(set(paths)))


def _has_node_class(blob: bytes) -> bool:
    tree = ast.parse(blob)
    return any(
        isinstance(statement, ast.ClassDef)
        and _NODE_CLASS.fullmatch(statement.name) is not None
        for statement in tree.body
    )


def _python_paths(paths: frozenset[str]) -> list[str]:
    return sorted(
        path
        for path in paths
        if path.endswith(".py")
        and _eligible(posix_path := PurePosixPath(path))
        and (
            posix_path.parent.name.startswith("node_")
            or (posix_path.parent / "contract.yaml").as_posix() in paths
        )
    )


def _node_class_paths(blobs: Mapping[str, bytes | None]) -> frozenset[str]:
    return frozenset(
        path
        for path, blob in blobs.items()
        if path.endswith(".py") and blob is not None and _has_node_class(blob)
    )


def _entry_points(blob: bytes | None) -> frozenset[str]:
    if blob is None:
        return frozenset()
    table = tomllib.loads(blob.decode("utf-8"))
    for key in ("project", "entry-points", "onex.nodes"):
        value = table.get(key, {})
        if not isinstance(value, dict):
            raise ValueError(f"pyproject.toml {key} must be a table")
        table = value
    return frozenset(table)


def read_request(
    repo_root: Path, base: str | None = "HEAD"
) -> ModelNodeHomeRatchetRequest:
    """Gather indexed and base-revision node inventories and registrations."""
    # Reuse the established batched git adapter. Its module imports our fixed
    # baseline constant, so load it only at the CLI boundary, never in handle.
    from omnibase_core.validators.canonical_file_shape import INDEX, GitRepo

    repo = GitRepo(root=repo_root)
    repo.run("rev-parse", "--show-toplevel")
    if repo.run("ls-files", "-u"):
        raise ValueError("resolve unmerged index entries before checking node homes")
    paths = frozenset(repo.list_files(INDEX))
    blobs = repo.read_blobs(
        INDEX, [*_python_paths(paths), NODE_HOME_BASELINE, "pyproject.toml"]
    )
    base_blob: bytes | None = None
    base_nodes: frozenset[str] = frozenset()
    base_entry_points: frozenset[str] = frozenset()
    if base is not None:
        if not repo.has_revision(base):
            raise ValueError(f"base revision does not exist: {base}")
        base_blobs = repo.read_blobs(base, [NODE_HOME_BASELINE, "pyproject.toml"])
        base_blob = base_blobs[NODE_HOME_BASELINE]
        base_entry_points = _entry_points(base_blobs["pyproject.toml"])
        if base_blob is None:
            base_paths = frozenset(repo.list_files(base))
            base_python = repo.read_blobs(base, _python_paths(base_paths))
            base_nodes = frozenset(
                _node_directories(base_paths, _node_class_paths(base_python))
            )
    head_blob = blobs[NODE_HOME_BASELINE]
    return ModelNodeHomeRatchetRequest(
        tracked_paths=paths,
        node_class_paths=_node_class_paths(blobs),
        head_baseline_text=None if head_blob is None else head_blob.decode("utf-8"),
        base_baseline_text=None if base_blob is None else base_blob.decode("utf-8"),
        base_node_directories=base_nodes,
        head_entry_points=_entry_points(blobs["pyproject.toml"]),
        base_entry_points=base_entry_points,
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Check the index, or create the fixed baseline once; return 0, 1 or 2."""
    parser = argparse.ArgumentParser(description="New ONEX nodes belong in omnimarket.")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--base", default="HEAD")
    parser.add_argument("--write-baseline", action="store_true")
    args = parser.parse_args(argv)
    try:
        request = read_request(
            args.repo_root, None if args.write_baseline else args.base
        )
        if args.write_baseline:
            from omnibase_core.validators.canonical_file_shape import GitRepo

            baseline = args.repo_root / NODE_HOME_BASELINE
            repo = GitRepo(root=args.repo_root)
            committed_baseline = (
                repo.read_blobs("HEAD", [NODE_HOME_BASELINE])[NODE_HOME_BASELINE]
                if repo.has_revision("HEAD")
                else None
            )
            if (
                baseline.exists()
                or request.head_baseline_text is not None
                or committed_baseline is not None
            ):
                raise ValueError(f"{NODE_HOME_BASELINE} exists; it can only shrink")
            directories = handle(request).node_directories
            baseline.parent.mkdir(parents=True, exist_ok=True)
            with baseline.open("x", encoding="utf-8") as stream:
                stream.write(render_baseline(directories))
            sys.stdout.write(
                f"wrote {len(directories)} entries to {NODE_HOME_BASELINE}\n"
            )
            return 0
        result = handle(request)
    except (OSError, ValueError, SyntaxError, subprocess.SubprocessError) as exc:
        sys.stderr.write(f"node-home ratchet: {exc}\n")
        return 2
    for finding in result.findings:
        sys.stderr.write(f"{finding.format()}\n")
    return 1 if result.findings else 0


if __name__ == "__main__":
    sys.exit(main())
