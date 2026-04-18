# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ValidatorRequirementsConsumer — enforcement consumer for validator-requirements.yaml.

OMN-9051 shipped ``architecture-handshakes/validator-requirements.yaml`` as the
single source of truth for which validators every repo must have wired on
pre-commit + CI. OMN-9115 wires this consumer so the spec is actually
enforced rather than a paper spec.

The consumer reads the spec and, for a given target repo directory, scans:

  - ``.pre-commit-config.yaml`` for every validator whose ``applies_to_repos``
    includes the target repo and whose ``pre_commit: required``.
  - ``.github/workflows/*.yml`` step names / run lines for every validator
    whose ``ci_workflow: required``.

Any missing registration, or any hook wrapped in a ``|| true`` / ``; exit 0``
silent-skip shim, is reported as a ``ModelValidatorRequirementGap``. The CLI
exits non-zero when any gap is found (blocking gate per
``feedback_no_informational_gates``).

Usage::

    # Programmatic
    from omnibase_core.validation.validator_requirements_consumer import (
        ValidatorRequirementsConsumer,
    )

    consumer = ValidatorRequirementsConsumer.from_canonical()
    gaps = consumer.scan_repo(repo_name="omnibase_core", repo_root=Path("."))

    # CLI
    uv run python -m omnibase_core.validation.validator_requirements_consumer \\
        --repo omnibase_core --repo-root .

Exit codes:
    0 — no gaps
    2 — one or more gaps detected
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Final

import yaml
from pydantic import ValidationError

from omnibase_core.enums.enum_validator_requirement_gap_kind import (
    EnumValidatorRequirementGapKind,
)
from omnibase_core.enums.enum_validator_requirement_scope import (
    EnumValidatorRequirementScope,
)
from omnibase_core.models.validation.model_validator_requirement_entry import (
    ModelValidatorRequirementEntry,
)
from omnibase_core.models.validation.model_validator_requirement_gap import (
    ModelValidatorRequirementGap,
)

__all__ = ["ValidatorRequirementsConsumer"]

_CANONICAL_SPEC_PATH: Final[Path] = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "architecture-handshakes"
    / "validator-requirements.yaml"
)

# Regex matching silent-skip wrappers in a pre-commit hook entry. Catches
# formatting variants: ``|| true``, ``||true``, ``|| exit 0``, ``;exit 0``,
# ``&& : || true`` etc. feedback_no_informational_gates: every check blocks;
# any of these turn a failure into a pass and are forbidden.
_SILENT_SKIP_RE: Final[re.Pattern[str]] = re.compile(
    r"(\|\||;)\s*(true\b|exit\s*0\b|:(?:\s|$|[^A-Za-z0-9_]))",
)

# Internal carrier for a single ``repos[*].hooks[*]`` entry from
# ``.pre-commit-config.yaml``. Kept as a plain tuple (hook_id, entry) so the
# enforcement consumer file stays single-class (per onex-single-class-per-file).
_PreCommitHook = tuple[str, str]


def _hook_is_silent_skip(hook: _PreCommitHook) -> bool:
    return _SILENT_SKIP_RE.search(hook[1]) is not None


class ValidatorRequirementsConsumer:
    """Read validator-requirements.yaml and enforce repo compliance.

    This is the OMN-9115 consumer for the OMN-9051 spec. Prefer
    ``ValidatorRequirementsConsumer.from_canonical()`` when scanning from
    omnibase_core itself; use ``from_spec_path()`` when the spec lives under
    a worktree or downstream checkout.
    """

    def __init__(
        self,
        validators: dict[str, ModelValidatorRequirementEntry],
        known_repos: frozenset[str] = frozenset(),
    ) -> None:
        self.validators = validators
        self._known_repos = known_repos

    # ---------------------------------------------------------------
    # Constructors
    # ---------------------------------------------------------------

    @classmethod
    def from_canonical(cls) -> ValidatorRequirementsConsumer:
        """Construct from the canonical spec under this repo's
        ``architecture-handshakes/`` directory."""
        return cls.from_spec_path(_CANONICAL_SPEC_PATH)

    @classmethod
    def from_spec_path(cls, spec_path: Path) -> ValidatorRequirementsConsumer:
        """Construct from an arbitrary spec path.

        Raises:
            FileNotFoundError: If ``spec_path`` does not exist.
            ValueError: If the spec is malformed.
        """
        if not spec_path.exists():
            raise FileNotFoundError(  # error-ok: standard stdlib for missing file
                f"validator-requirements.yaml missing at {spec_path}"
            )
        with spec_path.open() as fh:
            raw = yaml.safe_load(fh)
        if not isinstance(raw, dict):
            raise ValueError(  # error-ok: spec shape validation at load boundary
                "spec root must be a mapping"
            )
        raw_validators = raw.get("required_validators")
        if not isinstance(raw_validators, dict):
            raise ValueError(  # error-ok: spec shape validation at load boundary
                "spec.required_validators must be a mapping"
            )
        typed: dict[str, ModelValidatorRequirementEntry] = {}
        for name, entry in raw_validators.items():
            try:
                typed[name] = ModelValidatorRequirementEntry.model_validate(entry)
            except ValidationError as exc:
                raise ValueError(  # error-ok: spec shape validation at load boundary
                    f"spec.required_validators[{name!r}] is malformed: {exc}"
                ) from exc
        # known_repos is the canonical governed-repo list. Missing => permissive.
        raw_known = raw.get("known_repos")
        known: frozenset[str]
        if isinstance(raw_known, list) and all(isinstance(r, str) for r in raw_known):
            known = frozenset(raw_known)
        else:
            known = frozenset()
        return cls(validators=typed, known_repos=known)

    # ---------------------------------------------------------------
    # Scan entry point
    # ---------------------------------------------------------------

    def scan_repo(
        self,
        *,
        repo_name: str,
        repo_root: Path,
    ) -> list[ModelValidatorRequirementGap]:
        """Scan a target repo's pre-commit and CI configuration.

        Raises:
            ValueError: If ``repo_name`` is not listed in the spec's
                ``known_repos`` (typos fail loud). When the spec omits that
                key the check is permissive.
        """
        if self._known_repos and repo_name not in self._known_repos:
            raise ValueError(  # error-ok: CLI argument validation at call boundary
                f"unknown repo {repo_name!r}; expected one of "
                f"{sorted(self._known_repos)}"
            )

        pre_commit_hooks = self._load_pre_commit_hooks(repo_root)
        ci_haystack = self._load_ci_haystack(repo_root)

        gaps: list[ModelValidatorRequirementGap] = []
        for validator_name, entry in self.validators.items():
            if not _applies_to(entry, repo_name):
                continue
            gaps.extend(
                _check_validator(
                    repo_name=repo_name,
                    validator_name=validator_name,
                    entry=entry,
                    pre_commit_hooks=pre_commit_hooks,
                    ci_haystack=ci_haystack,
                )
            )
        return gaps

    # ---------------------------------------------------------------
    # Internals
    # ---------------------------------------------------------------

    def _load_pre_commit_hooks(self, repo_root: Path) -> list[_PreCommitHook]:
        config_path = repo_root / ".pre-commit-config.yaml"
        if not config_path.exists():
            return []
        with config_path.open() as fh:
            raw = yaml.safe_load(fh) or {}
        if not isinstance(raw, dict):
            return []
        hooks: list[_PreCommitHook] = []
        for block in raw.get("repos", []) or []:
            if not isinstance(block, dict):
                continue
            for hook in block.get("hooks", []) or []:
                if not isinstance(hook, dict):
                    continue
                hook_id = hook.get("id")
                if not isinstance(hook_id, str):
                    continue
                raw_entry = hook.get("entry", "") or ""
                entry_text = raw_entry if isinstance(raw_entry, str) else str(raw_entry)
                hooks.append((hook_id, entry_text))
        return hooks

    def _load_ci_haystack(self, repo_root: Path) -> str:
        workflows_dir = repo_root / ".github" / "workflows"
        if not workflows_dir.is_dir():
            return ""
        chunks: list[str] = []
        for path in sorted(workflows_dir.glob("*.y*ml")):
            try:
                chunks.append(path.read_text(encoding="utf-8"))
            except OSError:
                continue
        return "\n".join(chunks)


def _applies_to(entry: ModelValidatorRequirementEntry, repo_name: str) -> bool:
    applies = entry.applies_to_repos
    if isinstance(applies, str):
        return applies == "all"
    return repo_name in applies


def _check_validator(
    *,
    repo_name: str,
    validator_name: str,
    entry: ModelValidatorRequirementEntry,
    pre_commit_hooks: list[_PreCommitHook],
    ci_haystack: str,
) -> Iterable[ModelValidatorRequirementGap]:
    hook_ids = entry.pre_commit_hook_ids
    ci_keywords = entry.ci_workflow_keywords

    matched_hooks = [h for h in pre_commit_hooks if _any_substring(h[0], hook_ids)]

    if entry.pre_commit is EnumValidatorRequirementScope.REQUIRED and not matched_hooks:
        yield ModelValidatorRequirementGap(
            repo=repo_name,
            validator=validator_name,
            kind=EnumValidatorRequirementGapKind.MISSING_PRE_COMMIT,
            detail=f"no .pre-commit-config.yaml hook id matched any of {hook_ids}",
        )

    # Silent-skip wrappers are a violation regardless of pre_commit scope
    # (feedback_no_informational_gates — no advisory modes).
    for hook_id, hook_entry in matched_hooks:
        if _hook_is_silent_skip((hook_id, hook_entry)):
            yield ModelValidatorRequirementGap(
                repo=repo_name,
                validator=validator_name,
                kind=EnumValidatorRequirementGapKind.SILENT_SKIP_WRAPPER,
                detail=(
                    f"pre-commit hook {hook_id!r} wraps execution in a "
                    f"silent-skip shim: {hook_entry!r}"
                ),
            )

    if (
        entry.ci_workflow is EnumValidatorRequirementScope.REQUIRED
        and not _any_substring(ci_haystack, ci_keywords)
    ):
        yield ModelValidatorRequirementGap(
            repo=repo_name,
            validator=validator_name,
            kind=EnumValidatorRequirementGapKind.MISSING_CI_WORKFLOW,
            detail=f"no .github/workflows/*.yml referenced any of {ci_keywords}",
        )


def _any_substring(haystack: str, needles: list[str]) -> bool:
    return any(needle and needle in haystack for needle in needles)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _format_gaps(gaps: list[ModelValidatorRequirementGap]) -> str:
    lines = [f"{len(gaps)} validator-requirement gap(s):"]
    for gap in gaps:
        lines.append(
            f"  [{gap.kind.value}] {gap.repo} :: {gap.validator} — {gap.detail}"
        )
    return "\n".join(lines)


def _load_baseline(path: Path) -> set[tuple[str, str, str]]:
    """Load an accepted-gap baseline as a set of ``(repo, validator, kind)`` tuples.

    The baseline is YAML shaped as a list of mapping entries. Unknown kind
    values fail loudly to prevent silent drift.
    """
    if not path.exists():
        return set()
    with path.open() as fh:
        raw = yaml.safe_load(fh) or []
    if not isinstance(raw, list):
        raise ValueError(  # error-ok: baseline shape validation at load boundary
            f"baseline {path} must be a list of mappings"
        )
    accepted: set[tuple[str, str, str]] = set()
    valid_kinds = {k.value for k in EnumValidatorRequirementGapKind}
    for idx, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(  # error-ok: baseline shape validation at load boundary
                f"baseline[{idx}] must be a mapping"
            )
        try:
            repo = str(item["repo"])
            validator = str(item["validator"])
            kind = str(item["kind"])
        except KeyError as exc:
            raise ValueError(  # error-ok: baseline shape validation at load boundary
                f"baseline[{idx}] missing field: {exc}"
            ) from exc
        if kind not in valid_kinds:
            raise ValueError(  # error-ok: baseline shape validation at load boundary
                f"baseline[{idx}].kind invalid: {kind}"
            )
        accepted.add((repo, validator, kind))
    return accepted


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Enforce validator-requirements.yaml (OMN-9115)."
    )
    parser.add_argument(
        "--repo",
        required=True,
        help="Target repo name (must match a key in validator-requirements.yaml applies_to_repos)",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Path to target repo's working tree (default: cwd)",
    )
    parser.add_argument(
        "--spec",
        type=Path,
        default=None,
        help="Path to validator-requirements.yaml (default: canonical path under omnibase_core)",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=None,
        help=(
            "Optional baseline YAML listing accepted gaps as "
            "[{repo, validator, kind}, ...]. Any gap NOT in the baseline fails "
            "the check. Baseline entries NOT reproduced by the scan also fail "
            "(stale baseline). Mirrors the validate-dict-any-usage ratchet."
        ),
    )
    args = parser.parse_args(argv)

    spec_path = args.spec or _CANONICAL_SPEC_PATH
    consumer = ValidatorRequirementsConsumer.from_spec_path(spec_path)
    gaps = consumer.scan_repo(repo_name=args.repo, repo_root=args.repo_root)

    if args.baseline is None:
        if not gaps:
            print(
                f"validator-requirements: OK ({args.repo} @ {args.repo_root})",
                file=sys.stderr,
            )
            return 0
        print(_format_gaps(gaps), file=sys.stderr)
        return 2

    accepted = _load_baseline(args.baseline)
    observed = {(g.repo, g.validator, g.kind.value) for g in gaps}
    new_gaps = observed - accepted
    stale_entries = accepted - observed

    if not new_gaps and not stale_entries:
        print(
            f"validator-requirements: baseline-clean ({args.repo} — "
            f"{len(observed)} accepted gap(s))",
            file=sys.stderr,
        )
        return 0

    if new_gaps:
        print("New validator-requirement gaps not in baseline:", file=sys.stderr)
        for repo, validator, kind in sorted(new_gaps):
            print(f"  + [{kind}] {repo} :: {validator}", file=sys.stderr)
    if stale_entries:
        print(
            "Baseline entries no longer reproduced (remove from baseline):",
            file=sys.stderr,
        )
        for repo, validator, kind in sorted(stale_entries):
            print(f"  - [{kind}] {repo} :: {validator}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())  # error-ok: standard CLI entry-point idiom
