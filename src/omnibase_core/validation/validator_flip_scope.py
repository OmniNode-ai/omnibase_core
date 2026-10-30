# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Package scoping and historical baseline loading for flip verification."""

from __future__ import annotations

import ast
import importlib.util
import os
from pathlib import Path

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.flip_bundle.model_flip_scope import ModelFlipScope
from omnibase_core.validation.validator_flip_git import (
    _git_ref_exists,
    _git_repo_root,
    _git_show,
)

# Default stem of a package's handler-shape baseline module beside the CI scripts. A
# consuming repository names its own baseline with an explicit ``--baseline`` argument.
_BASELINE_STEM = "flip_shape_baseline"
_REPO_ROOT = Path(__file__).resolve().parents[3]
_CI_DIR = _REPO_ROOT / "scripts" / "ci"
SCOPE = ModelFlipScope(
    package="omnibase_core",
    repo_root=_REPO_ROOT,
    src_root=_REPO_ROOT / "src",
    nodes_glob="omnibase_core/**/nodes/**/contract.yaml",
    baseline_path=_CI_DIR / f"{_BASELINE_STEM}.py",
    receipts_dir=_CI_DIR / "adequacy_receipts",
    base_ref="origin/dev",
)


def _resolve_scope(
    package: str,
    src_root: Path | None,
    nodes_glob: str | None,
    baseline: Path | None,
    receipts_dir: Path | None,
) -> tuple[Path, str, Path, Path]:
    """Compute ``(src_root, nodes_glob, baseline_path, receipts_dir)`` for a scope.

    Every argument defaults to the omnibase_core value already in effect on the
    module (``SCOPE.src_root``/``SCOPE.baseline_path``/``SCOPE.receipts_dir``), so calling this
    with ``package="omnibase_core"`` and all other args ``None`` reproduces
    today's constants exactly. A non-default ``package`` with no explicit
    ``--baseline``/``--receipts-dir`` gets a package-suffixed path in the CI
    directory rather than silently clobbering omnibase_core's own committed
    baseline/receipts.
    """
    resolved_src_root = src_root if src_root is not None else SCOPE.src_root
    resolved_glob = nodes_glob or f"{package}/**/nodes/**/contract.yaml"
    if baseline is not None:
        resolved_baseline = baseline
    elif package == "omnibase_core":
        resolved_baseline = SCOPE.baseline_path
    else:
        resolved_baseline = _CI_DIR / f"{_BASELINE_STEM}_{package}.py"
    if receipts_dir is not None:
        resolved_receipts = receipts_dir
    elif package == "omnibase_core":
        resolved_receipts = SCOPE.receipts_dir
    else:
        resolved_receipts = _CI_DIR / f"adequacy_receipts_{package}"
    return resolved_src_root, resolved_glob, resolved_baseline, resolved_receipts


def load_baseline(path: Path | None = None) -> list[str]:
    """Return the grandfathered non-canonical node ids.

    No baseline file means no grandfathered node: the gate is a plain check and
    every non-canonical node fails (OMN-20559). That is the fail-closed reading,
    since an absent file can only make the gate stricter.
    """
    path = path if path is not None else SCOPE.baseline_path
    if not path.exists():
        return []
    spec = importlib.util.spec_from_file_location("flip_scope_baseline", path)
    if spec is None or spec.loader is None:
        raise ModelOnexError(
            message=f"Cannot load baseline module from {path}",
            error_code=EnumCoreErrorCode.IMPORT_ERROR,
        )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return [str(n) for n in getattr(module, "NON_CANONICAL", ())]


def _parse_non_canonical(source: str) -> list[str]:
    """Extract the ``NON_CANONICAL`` string tuple from baseline source, no exec()."""
    tree = ast.parse(source)
    for node in tree.body:
        target_names: list[str] = []
        value: ast.expr | None = None
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            target_names = [node.target.id]
            value = node.value
        elif isinstance(node, ast.Assign):
            target_names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            value = node.value
        if "NON_CANONICAL" in target_names and value is not None:
            evaluated = ast.literal_eval(value)
            return [str(n) for n in evaluated]
    return []


def load_base_baseline(baseline_path: Path, base_ref: str) -> list[str] | None:
    """Load ``NON_CANONICAL`` as it existed at ``base_ref`` (the git BASE).

    Returns:
      * the base entries when resolvable;
      * ``[]`` when the baseline file did NOT exist at ``base_ref`` (a brand-new
        baseline file legitimately has no prior entries — nothing to protect);
      * ``None`` when the base cannot be determined at all (no git, unknown ref).
        A ``None`` disables the removal/growth check for that run WITHOUT
        hard-failing — mirrors the existing diff-unavailable tolerance. In CI the
        PR base (origin/dev) is always present, so the check is live there.
    """
    repo_root = _git_repo_root(baseline_path)
    if repo_root is None:
        return None
    if not _git_ref_exists(repo_root, base_ref):
        return None
    try:
        rel = baseline_path.resolve().relative_to(repo_root.resolve())
    except ValueError:
        return None
    source = _git_show(repo_root, base_ref, str(rel).replace(os.sep, "/"))
    if source is None:
        # ref exists but file absent at base -> new baseline file, no prior entries.
        return []
    try:
        return _parse_non_canonical(source)
    except (SyntaxError, ValueError):
        return None
