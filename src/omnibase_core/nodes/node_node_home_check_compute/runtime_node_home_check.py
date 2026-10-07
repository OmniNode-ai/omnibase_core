# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Indexed Git inputs and CLI for the node-home COMPUTE check (OMN-20702).

Checks the index against --base (HEAD by default), or creates the fixed
shrink-only inventory once with --write-baseline. Returns 0, 1 or 2.
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

from omnibase_core.models.validation.model_node_home_ratchet_request import (
    ModelNodeHomeRatchetRequest,
)
from omnibase_core.nodes.node_node_home_check_compute.handler import (
    NODE_HOME_BASELINE,
    NodeNodeHomeCheckCompute,
    _eligible,
    _node_directories,
)

_NODE_CLASS = re.compile(r"^Node[A-Z]\w*$")


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
            directories = NodeNodeHomeCheckCompute().handle(request).node_directories
            baseline.parent.mkdir(parents=True, exist_ok=True)
            with baseline.open("x", encoding="utf-8") as stream:
                stream.write(render_baseline(directories))
            sys.stdout.write(
                f"wrote {len(directories)} entries to {NODE_HOME_BASELINE}\n"
            )
            return 0
        result = NodeNodeHomeCheckCompute().handle(request)
    except (OSError, ValueError, SyntaxError, subprocess.SubprocessError) as exc:
        sys.stderr.write(f"node-home ratchet: {exc}\n")
        return 2
    for finding in result.findings:
        sys.stderr.write(f"{finding.format()}\n")
    return 1 if result.findings else 0


if __name__ == "__main__":
    sys.exit(main())
