# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Set arithmetic over typed hold scopes (OMN-19405, typed work ledger T4).

A scope covers a pull request when it names the PR, names its repository, or
sets ``all_repos``. It covers a repository at repository level when it names the
repository or sets ``all_repos``. Surfaces and lanes are plain sets. Every
function here is pure and reads typed fields only.
"""

from __future__ import annotations

from collections.abc import Sequence

from omnibase_core.models.events.work.model_hold_scope import ModelHoldScope
from omnibase_core.models.events.work.model_pr_key import ModelPrKey

__all__ = [
    "is_subscope",
    "scope_covers_pr",
    "scope_covers_repo",
    "scopes_cover_scope",
]


def scope_covers_pr(scope: ModelHoldScope, pr: ModelPrKey) -> bool:
    """True when ``scope`` covers pull request ``pr``."""
    return scope.all_repos or pr in scope.prs or pr.repo in scope.repos


def scope_covers_repo(scope: ModelHoldScope, repo: str) -> bool:
    """True when ``scope`` covers every pull request of ``repo``."""
    return scope.all_repos or repo.lower() in scope.repos


def is_subscope(part: ModelHoldScope, whole: ModelHoldScope) -> bool:
    """True when everything ``part`` covers is covered by ``whole``."""
    return (
        all(scope_covers_pr(whole, pr) for pr in part.prs)
        and all(scope_covers_repo(whole, repo) for repo in part.repos)
        and (not part.all_repos or whole.all_repos)
        and part.surfaces <= whole.surfaces
        and part.lanes <= whole.lanes
    )


def scopes_cover_scope(parts: Sequence[ModelHoldScope], whole: ModelHoldScope) -> bool:
    """True when the union of ``parts`` covers everything ``whole`` covers."""
    if not parts:
        return False
    surfaces: frozenset[str] = frozenset().union(*(part.surfaces for part in parts))
    lanes: frozenset[str] = frozenset().union(*(part.lanes for part in parts))
    return (
        all(any(scope_covers_pr(part, pr) for part in parts) for pr in whole.prs)
        and all(
            any(scope_covers_repo(part, repo) for part in parts) for repo in whole.repos
        )
        and (not whole.all_repos or any(part.all_repos for part in parts))
        and whole.surfaces <= surfaces
        and whole.lanes <= lanes
    )
