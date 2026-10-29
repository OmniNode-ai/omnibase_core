# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Execute and memoize declared parity tests for the active scope."""

from __future__ import annotations

import importlib
import sys
from collections.abc import Callable

from omnibase_core.models.flip_bundle.model_parity_verdict import ModelParityVerdict
from omnibase_core.validation.validator_flip_git import _git_repo_root
from omnibase_core.validation.validator_flip_scope import SCOPE

ParityExecutor = Callable[[str, tuple[str, ...]], ModelParityVerdict]
_PARITY_CACHE: dict[tuple[str, str, tuple[str, ...]], ModelParityVerdict] = {}


def default_parity_executor(
    node_id: str, test_ids: tuple[str, ...]
) -> ModelParityVerdict:
    """Execute the declared parity ids against the working tree; all must PASS."""
    cache_key = (str(SCOPE.src_root), node_id, test_ids)
    cached = _PARITY_CACHE.get(cache_key)
    if cached is not None:
        return cached
    try:
        try:
            from scripts.ci import parity_replay
        except ImportError:
            sys.path.insert(0, str(SCOPE.repo_root / "scripts" / "ci"))
            parity_replay = importlib.import_module("parity_replay")
    except ImportError as exc:
        return ModelParityVerdict(
            executed=False, green=False, detail=f"parity engine unavailable: {exc}"
        )
    repo_root = _git_repo_root(SCOPE.src_root)
    if repo_root is None:
        verdict = ModelParityVerdict(
            executed=False,
            green=False,
            detail=f"cannot resolve a git repo root from {SCOPE.src_root} to run parity tests",
        )
        _PARITY_CACHE[cache_key] = verdict
        return verdict
    run = parity_replay.run_on_head(repo_root, SCOPE.src_root, test_ids)
    if not run.executed:
        verdict = ModelParityVerdict(executed=False, green=False, detail=run.detail)
    elif run.all_passed:
        verdict = ModelParityVerdict(
            executed=True,
            green=True,
            detail=f"{len(run.results)} declared parity id(s) executed GREEN on HEAD",
        )
    else:
        offenders = "; ".join(
            f"{r.test_id} -> {r.outcome.value}"
            for r in run.results
            if r.outcome.value != "passed"
        )
        verdict = ModelParityVerdict(
            executed=True,
            green=False,
            detail=f"declared parity id(s) NOT green on HEAD: {offenders}",
        )
    _PARITY_CACHE[cache_key] = verdict
    return verdict
