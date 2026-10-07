# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Indexed Git inputs and CLI for the node-home COMPUTE check (OMN-20702).

Checks the index against --base (HEAD by default), or prints the fixed
shrink-only inventory once with --print-baseline. Returns 0, 1 or 2.
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
import tomllib
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path, PurePosixPath

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.nodes.git_file_listing.model_git_file_listing_input import (
    ModelGitFileListingInput,
)
from omnibase_core.models.nodes.git_file_listing.model_git_file_listing_output import (
    ModelGitFileListingOutput,
)
from omnibase_core.models.validation.model_node_home_ratchet_request import (
    NODE_HOME_BASELINE,
    ModelNodeHomeRatchetRequest,
)
from omnibase_core.nodes.node_git_file_listing_effect.handler import (
    NodeGitFileListingEffect,
)
from omnibase_core.nodes.node_node_home_check_compute.handler import (
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
        "# Created once with --print-baseline; never regenerate or add entries.\n"
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
            raise ModelOnexError(
                message=f"pyproject.toml {key} must be a table",
                error_code=EnumCoreErrorCode.INVALID_CONFIGURATION,
            )
        table = value
    return frozenset(table)


def _snapshot(
    repo_root: Path, revision: str | None, paths: list[str] | None = None
) -> ModelGitFileListingOutput:
    output = NodeGitFileListingEffect().handle(
        ModelGitFileListingInput(
            root=repo_root,
            snapshot="index" if revision is None else "revision",
            base_ref=revision or "HEAD",
            blob_paths=paths or [],
        )
    )
    if output.has_unmerged_entries:
        raise ModelOnexError(
            message="resolve unmerged index entries before checking node homes",
            error_code=EnumCoreErrorCode.INVALID_STATE,
        )
    if output.revision_exists is False:
        raise ModelOnexError(
            message=f"base revision does not exist: {revision}",
            error_code=EnumCoreErrorCode.INVALID_PARAMETER,
        )
    return output


def read_request(
    repo_root: Path, base: str | None = "HEAD"
) -> ModelNodeHomeRatchetRequest:
    """Gather indexed and base-revision inputs through the Git EFFECT boundary."""
    paths = frozenset(_snapshot(repo_root, None).paths)
    blobs = _snapshot(
        repo_root, None, [*_python_paths(paths), NODE_HOME_BASELINE, "pyproject.toml"]
    ).blobs
    base_blob: bytes | None = None
    base_nodes: frozenset[str] = frozenset()
    base_entry_points: frozenset[str] = frozenset()
    if base is not None:
        base_paths = frozenset(_snapshot(repo_root, base).paths)
        base_blobs = _snapshot(
            repo_root,
            base,
            [*_python_paths(base_paths), NODE_HOME_BASELINE, "pyproject.toml"],
        ).blobs
        base_blob = base_blobs[NODE_HOME_BASELINE]
        base_entry_points = _entry_points(base_blobs["pyproject.toml"])
        if base_blob is None:
            base_nodes = frozenset(
                _node_directories(base_paths, _node_class_paths(base_blobs))
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
    """Check the index, or print the fixed initial baseline; return 0, 1 or 2."""
    parser = argparse.ArgumentParser(description="New ONEX nodes belong in omnimarket.")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--base", default="HEAD")
    parser.add_argument("--print-baseline", action="store_true")
    args = parser.parse_args(argv)
    try:
        request = read_request(
            args.repo_root, None if args.print_baseline else args.base
        )
        if args.print_baseline:
            committed = NodeGitFileListingEffect().handle(
                ModelGitFileListingInput(
                    root=args.repo_root,
                    snapshot="revision",
                    base_ref="HEAD",
                    blob_paths=[NODE_HOME_BASELINE],
                )
            )
            if (
                request.head_baseline_text is not None
                or committed.blobs[NODE_HOME_BASELINE] is not None
            ):
                raise ModelOnexError(
                    message=f"{NODE_HOME_BASELINE} exists; it can only shrink",
                    error_code=EnumCoreErrorCode.INVALID_OPERATION,
                )
            directories = NodeNodeHomeCheckCompute().handle(request).node_directories
            sys.stdout.write(render_baseline(directories))
            return 0
        result = NodeNodeHomeCheckCompute().handle(request)
    except (OSError, ValueError, SyntaxError, ModelOnexError) as exc:
        message = exc.message if isinstance(exc, ModelOnexError) else str(exc)
        sys.stderr.write(f"node-home ratchet: {message}\n")
        return 2
    for finding in result.findings:
        sys.stderr.write(f"{finding.format()}\n")
    return 1 if result.findings else 0


if __name__ == "__main__":
    sys.exit(main())
