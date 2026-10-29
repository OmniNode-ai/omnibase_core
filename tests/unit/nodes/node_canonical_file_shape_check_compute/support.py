# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Fixture-repository helpers shared by the canonical-file-shape tests (OMN-21515)."""

from __future__ import annotations

import subprocess
from collections.abc import Iterable
from pathlib import Path

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.validation.model_canonical_file_shape_rule_set import (
    ModelCanonicalFileShapeRuleSet,
)
from omnibase_core.nodes.node_canonical_file_shape_check_compute.runtime_canonical_file_shape_check import (
    INDEX,
    GitRepo,
    gather_facts,
    resolve_revisions,
)
from omnibase_core.validation.checker_canonical_file_shape import check, load_rule_set
from omnibase_core.validation.validator_canonical_file_shape import (
    ValidatorCanonicalFileShape,
)
from omnibase_core.validators.no_unguarded_git_subprocess import (
    scrub_git_location_env,
)

IDENTITY = ("-c", "user.name=t", "-c", "user.email=t@example.com")
RULES = load_rule_set(ValidatorCanonicalFileShape().contract)
BASELINE = RULES.parameters.baseline_path
NODE_HOME_BASELINE = RULES.parameters.node_home_baseline_path


def git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", *IDENTITY, *args],
        cwd=repo,
        env=scrub_git_location_env(),
        check=True,
        capture_output=True,
    )


def write(repo: Path, rel: str, text: str) -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def baseline_text(paths: Iterable[str]) -> str:
    return RULES.parameters.baseline_header + "".join(
        f"{path}\n" for path in sorted(set(paths))
    )


def init_repo(root: Path, baselined: Iterable[str] = ()) -> Path:
    """A repository whose single commit carries a baseline listing ``baselined``."""
    git(root, "init", "-q", "-b", "dev")
    write(root, BASELINE, baseline_text(baselined))
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "base")
    return root


def stage(repo: Path) -> None:
    git(repo, "add", "-A")


def issues(
    repo: Path,
    base: str | None = None,
    head: str | None = None,
    commit_message: str | None = None,
    rules: ModelCanonicalFileShapeRuleSet = RULES,
) -> tuple[ModelValidationIssue, ...]:
    """Every issue for the index (or ``head``) against ``base`` (``HEAD`` by default)."""
    git_repo = GitRepo(
        root=repo,
        env=scrub_git_location_env(),
        cat_file_timeout_s=RULES.parameters.cat_file_timeout_s,
    )
    resolved_head, resolved_base = resolve_revisions(git_repo, base, head)
    facts = gather_facts(
        git_repo, rules.parameters, resolved_head, resolved_base, commit_message
    )
    return check(facts, rules)


def rules_hit(
    repo: Path,
    base: str | None = None,
    head: str | None = None,
    commit_message: str | None = None,
) -> list[str]:
    found = issues(repo, base=base, head=head, commit_message=commit_message)
    return sorted(issue.code or "" for issue in found)


__all__ = [
    "BASELINE",
    "INDEX",
    "NODE_HOME_BASELINE",
    "RULES",
    "baseline_text",
    "git",
    "init_repo",
    "issues",
    "rules_hit",
    "stage",
    "write",
]
