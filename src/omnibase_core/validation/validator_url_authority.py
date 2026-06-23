# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ValidatorUrlAuthority — reject new URL/endpoint literals outside contracts.

Part of OMN-12803 (PR-2, the enforcement gate). Every URL and ``*_URL`` /
``*_ENDPOINT`` env read must resolve from a contract (routing authority /
integration catalog), not a literal string or a bare env read.

Detects four classes of violations in Python source files:

1. **public-https-literal** — a quoted ``https://`` URL targeting a public
   host with a dotted TLD.  Excludes localhost/loopback, example placeholders,
   VCS display permalinks, and JSON-schema refs (audit cosmetic-exclusion
   class 1K).

2. **env-url-read** — ``os.environ[...]`` subscript or ``os.environ.get(...)``
   call whose variable NAME ends in ``_URL`` or ``_ENDPOINT``.  API-key /
   token / secret variable names do NOT end in those suffixes and remain legal.

3. **url-const-assignment** — module-level constant assignment whose name
   ends in ``URL`` or ``ENDPOINT``, sourced from ``os.environ`` or a bare
   ``https://`` literal.

4. **localhost-literal** (OMN-13480) — a hardcoded ``http(s)://`` loopback
   connection-target literal (``localhost``, ``127.x.x.x``, ``0.0.0.0``,
   ``[::1]``) that is NOT a ``*_URL`` / ``*_ENDPOINT`` constant.  The
   public-https rule deliberately skips localhost (no dotted TLD), so a bare
   loopback literal passed directly to an HTTP client call was otherwise
   invisible.  A connection target should resolve from the routing authority,
   not a hardcoded loopback literal.

Ratchet (OMN-12818, mirrors OMN-12791 receipt-honesty gate): existing
violations are grandfathered by content fingerprint (sha256 of {repo, path,
normalized-snippet}).  Only NEW fingerprints fail the gate.  The baseline may
only shrink — the ``--update-baseline`` / ``--seed`` modes enforce the
burn-down invariant.

Baseline per repo lives at:
``src/omnibase_core/validation/baselines/url_authority_baseline.json``

Usage Examples:
    Programmatic usage::

        from omnibase_core.validation import ValidatorUrlAuthority

        v = ValidatorUrlAuthority()
        result = v.validate(Path("src/"))
        if not result.is_valid:
            for issue in result.issues:
                print(f"{issue.file_path}:{issue.line_number}: {issue.message}")

    CLI — pre-commit (staged files)::

        python -m omnibase_core.validation.validator_url_authority file1.py ...

    CLI — full repo scan (CI)::

        python -m omnibase_core.validation.validator_url_authority --all \\
            --repo omnibase_core --repo-root .

    CLI — seed / update baseline::

        python -m omnibase_core.validation.validator_url_authority \\
            --seed --repo omnibase_core --repo-root .

Suppression:
    Add ``# url-authority-ok: <reason>`` on the offending line.
    Config-PATH env reads annotated with ``# contract-config-ok:`` are also exempt.

Migration debt tickets:
    - omnibase_core: OMN-12806
    - omnibase_infra: OMN-12807
    - other repos: OMN-12808

Schema Version:
    v1.0.0 - Initial version (OMN-12818)
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import ClassVar, Final

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.validation.model_url_authority_violation import (
    ModelUrlAuthorityViolation,
)
from omnibase_core.validation.validator_base import ValidatorBase

# ---------------------------------------------------------------------------
# Detection patterns
# ---------------------------------------------------------------------------

# 1. Public HTTPS endpoint literal.  Connection-target scope only: excludes
#    localhost/loopback, example/placeholder hosts, VCS display permalinks,
#    JSON-schema refs, and raw-content refs (audit cosmetic-exclusion class 1K).
_PUBLIC_HTTPS_LITERAL: Final[re.Pattern[str]] = re.compile(
    r"""["']https://[a-z0-9-]+(?:\.[a-z0-9-]+)*\.[a-z]{2,}(?:[/"':]|$)""",
    re.IGNORECASE,
)

# Hosts/paths that are NOT connection targets (excluded from the public-https rule).
_NON_ENDPOINT_MARKERS: Final[tuple[str, ...]] = (
    "example.com",
    "example.org",
    ".invalid",
    "://github.com/",  # display permalinks; api.github.com IS matched
    "://gitlab.com/",
    "raw.githubusercontent.com",
    "$schema",
    "schemastore.org",
    "json-schema.org",
    "w3.org",
    "spdx.org",
)

# 2. ``*_URL`` / ``*_ENDPOINT`` env read.
_ENV_URL_READ: Final[re.Pattern[str]] = re.compile(
    r"""os\.environ(?:\.get\(\s*|\[\s*)["'][A-Z0-9_]*(?:_URL|_ENDPOINT)["']""",
)

# 3. ``*_URL`` / ``*_ENDPOINT`` module-constant assignment.
_CONST_URL_FROM_ENV: Final[re.Pattern[str]] = re.compile(
    r"""^[A-Z0-9_]*(?:URL|ENDPOINT)[A-Z0-9_]*\s*=\s*os\.environ""",
)
_CONST_URL_FROM_LITERAL: Final[re.Pattern[str]] = re.compile(
    r"""^[A-Z0-9_]*(?:URL|ENDPOINT)[A-Z0-9_]*\s*=\s*["']https?://""",
)

# 4. Hardcoded localhost / loopback connection-target literal (OMN-13480).
#    The public-https rule deliberately skips localhost (no dotted TLD), and
#    a bare loopback literal that is NOT assigned to a ``*_URL`` / ``*_ENDPOINT``
#    constant is otherwise invisible — e.g. ``httpx.get("http://localhost:9000")``.
#    A connection target should resolve from the routing authority, not a
#    hardcoded loopback literal. Matches http(s):// to:
#      * ``localhost`` (optionally with a ``:port``)
#      * IPv4 loopback ``127.x.x.x`` and the wildcard bind address ``0.0.0.0``
#      * IPv6 loopback ``[::1]``
_LOCALHOST_LITERAL: Final[re.Pattern[str]] = re.compile(
    r"""["']https?://(?:localhost|127\.\d{1,3}\.\d{1,3}\.\d{1,3}|0\.0\.0\.0|\[::1\])(?:[:/"']|$)""",
    re.IGNORECASE,
)

# Suppression annotations.
_SUPPRESS_ANNOTATION: Final[str] = "# url-authority-ok:"
_CONFIG_PATH_ANNOTATION: Final[str] = "# contract-config-ok:"

# Authority files: the URL literals inside them ARE canonical — skip.
_AUTHORITY_PATH_SUFFIXES: Final[tuple[str, ...]] = (
    "configs/bifrost_delegation.yaml",
    "contracts/integrations/catalog.yaml",
)

# Rule identifiers (must match the validation contract).
RULE_PUBLIC_HTTPS: Final[str] = "public-https-literal"
RULE_ENV_URL_READ: Final[str] = "env-url-read"
RULE_CONST_ASSIGNMENT: Final[str] = "url-const-assignment"
RULE_LOCALHOST_LITERAL: Final[str] = "localhost-literal"

# Directories excluded from full-tree scans.
_EXCLUDED_PARTS: Final[frozenset[str]] = frozenset(
    {
        ".git",
        ".venv",
        "node_modules",
        "__pycache__",
        "dist",
        "build",
        "dod_receipts",
        "evidence",
        ".onex_state",
    }
)

# Default baseline path (relative to this file's parent → baselines/ subdir).
_DEFAULT_BASELINE: Final[Path] = (
    Path(__file__).parent / "baselines" / "url_authority_baseline.json"
)


# ---------------------------------------------------------------------------
# Fingerprinting helpers
# ---------------------------------------------------------------------------


def _normalize(snippet: str) -> str:
    """Normalize the offending snippet for a stable, line-number-independent hash."""
    return re.sub(r"\s+", " ", snippet.strip())


def make_fingerprint(repo: str, path: str, snippet: str) -> str:
    """sha256({repo}\\0{path}\\0{normalized-snippet}) — survives unrelated edits."""
    payload = f"{repo}\0{path}\0{_normalize(snippet)}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Per-line matching helpers
# ---------------------------------------------------------------------------


def _is_authority_path(path: str) -> bool:
    """True when the file IS a URL authority (its literals are canonical)."""
    norm = path.replace("\\", "/")
    return any(norm.endswith(suffix) for suffix in _AUTHORITY_PATH_SUFFIXES)


def _is_test_path(path: str) -> bool:
    lowered = path.lower()
    return "test" in lowered or "conftest" in lowered


def _is_connection_target(raw_line: str) -> bool:
    """True when an https literal is a real connection endpoint, not a placeholder."""
    lowered = raw_line.lower()
    if any(marker in lowered for marker in _NON_ENDPOINT_MARKERS):
        return False
    # Heuristic: the line is (part of) a JSON-object literal, not an assignment.
    stripped = raw_line.strip()
    if stripped.startswith(("{", '{"')) or '":{"' in stripped:
        return False
    return True


def _match_rule(raw_line: str, stripped: str) -> str | None:
    """Return the first matching rule id for a line, or None."""
    if _ENV_URL_READ.search(raw_line):
        return RULE_ENV_URL_READ
    if _CONST_URL_FROM_ENV.match(stripped) or _CONST_URL_FROM_LITERAL.match(stripped):
        return RULE_CONST_ASSIGNMENT
    if _PUBLIC_HTTPS_LITERAL.search(raw_line) and _is_connection_target(raw_line):
        return RULE_PUBLIC_HTTPS
    # Bare loopback connection-target literal not captured by the rules above
    # (the public-https rule skips localhost; this is not a *_URL constant).
    if _LOCALHOST_LITERAL.search(raw_line):
        return RULE_LOCALHOST_LITERAL
    return None


# ---------------------------------------------------------------------------
# Source scanner
# ---------------------------------------------------------------------------


def scan_source(repo: str, path: str, source: str) -> list[ModelUrlAuthorityViolation]:
    """Scan one source file's text for url-authority violations.

    Test files and authority files are skipped.  Lines carrying
    ``# url-authority-ok:`` or (for env reads) ``# contract-config-ok:`` are
    suppressed.  Returns at most one violation per line.

    Args:
        repo: Repo name used in fingerprints (e.g. ``"omnibase_core"``).
        path: Repo-relative path for fingerprints (e.g. ``"src/pkg/file.py"``).
        source: Full source text of the file.

    Returns:
        List of violations found in the file.
    """
    if _is_test_path(path) or _is_authority_path(path):
        return []

    violations: list[ModelUrlAuthorityViolation] = []
    for index, raw_line in enumerate(source.splitlines(), start=1):
        stripped = raw_line.strip()
        # Skip blank, comment-only, and docstring lines (triple-quoted blocks
        # holding URLs are documentation, not connection targets).
        if not stripped or stripped.startswith(("#", '"""', "'''")):
            continue
        if _SUPPRESS_ANNOTATION in raw_line:
            continue

        rule = _match_rule(raw_line, stripped)
        if rule is None:
            continue
        # Config-PATH env reads annotated with contract-config-ok are exempt.
        if rule == RULE_ENV_URL_READ and _CONFIG_PATH_ANNOTATION in raw_line:
            continue

        snippet = stripped[:200]
        violations.append(
            ModelUrlAuthorityViolation(
                repo=repo,
                path=path,
                line=index,
                rule=rule,
                snippet=snippet,
                fingerprint=make_fingerprint(repo, path, snippet),
            )
        )
    return violations


def scan_tree(repo: str, repo_root: Path) -> list[ModelUrlAuthorityViolation]:
    """Scan all ``*.py`` under ``repo_root`` for url-authority violations.

    Paths in the returned violations are repo-relative so fingerprints are
    machine-independent.  Excludes vendored, build, test, and evidence dirs.

    Args:
        repo: Repo name for fingerprints.
        repo_root: Absolute path to the repository root.

    Returns:
        Sorted list of violations.
    """
    violations: list[ModelUrlAuthorityViolation] = []
    for py in sorted(repo_root.rglob("*.py")):
        if set(py.parts) & _EXCLUDED_PARTS:
            continue
        if _is_test_path(py.name):
            continue
        try:
            source = py.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        try:
            rel = str(py.relative_to(repo_root))
        except ValueError:
            rel = str(py)
        violations.extend(scan_source(repo, rel, source))
    return violations


# ---------------------------------------------------------------------------
# Ratchet baseline helpers
# ---------------------------------------------------------------------------


def load_baseline(baseline_path: Path) -> set[str]:
    """Load the frozen fingerprint set from the baseline JSON.  Missing file = empty."""
    if not baseline_path.exists():
        return set()
    data = json.loads(baseline_path.read_text(encoding="utf-8"))
    entries = data.get("violations", []) if isinstance(data, dict) else []
    return {
        str(e["fingerprint"])
        for e in entries
        if isinstance(e, dict) and "fingerprint" in e
    }


def partition_against_baseline(
    violations: list[ModelUrlAuthorityViolation],
    baseline_fingerprints: set[str],
) -> tuple[list[ModelUrlAuthorityViolation], list[ModelUrlAuthorityViolation]]:
    """Split violations into (new, grandfathered) by baseline membership.

    Returns:
        Tuple of (new_violations, grandfathered_violations).  New violations
        fail the gate; grandfathered ones pass.
    """
    new: list[ModelUrlAuthorityViolation] = []
    grandfathered: list[ModelUrlAuthorityViolation] = []
    for v in violations:
        if v.fingerprint in baseline_fingerprints:
            grandfathered.append(v)
        else:
            new.append(v)
    return new, grandfathered


def assert_baseline_shrinks_only(before: set[str], after: set[str]) -> None:
    """Anti-gaming: the baseline may shrink (burn-down) but never grow.

    Raises:
        ValueError: If ``after`` introduces fingerprints not present in ``before``.
    """
    added = after - before
    if added:
        raise ValueError(  # error-ok: function-boundary validation guard (anti-gaming baseline check, CLI-surfaced)
            "url-authority baseline grew: "
            f"{len(added)} new fingerprint(s) added. The baseline is burn-down only "
            "— fix the violation or annotate with # url-authority-ok:, never add it "
            "to the baseline. Offending fingerprints: "
            f"{sorted(added)[:5]}"
        )


def serialize_baseline(
    violations: list[ModelUrlAuthorityViolation],
) -> dict[str, object]:
    """Build the on-disk baseline document — sorted, deterministic, fingerprint-keyed."""
    entries: list[dict[str, str]] = sorted(
        (
            {
                "repo": v.repo,
                "path": v.path,
                "rule": v.rule,
                "fingerprint": v.fingerprint,
            }
            for v in violations
        ),
        key=lambda e: (e["repo"], e["path"], e["fingerprint"]),
    )
    seen: set[str] = set()
    unique: list[dict[str, str]] = []
    for e in entries:
        fp = e["fingerprint"]
        if fp in seen:
            continue
        seen.add(fp)
        unique.append(e)
    return {"schema_version": "1.0.0", "count": len(unique), "violations": unique}


# ---------------------------------------------------------------------------
# ValidatorBase subclass
# ---------------------------------------------------------------------------


class ValidatorUrlAuthority(ValidatorBase):
    """Reject NEW URL/endpoint literals outside contracts.

    Wraps the url-authority ratchet as a standard ValidatorBase subclass so it
    participates in the ecosystem-wide validation pipeline (pre-commit hooks,
    CI required checks, cross-repo wiring).

    The validator ONLY reports violations that are NEW (not in the per-repo
    baseline).  Existing (grandfathered) violations are silently skipped until
    they are fixed and the baseline is shrunk.

    See migration debt tickets OMN-12806 (omnibase_core), OMN-12807
    (omnibase_infra), OMN-12808 (other repos).
    """

    validator_id: ClassVar[str] = "url_authority"

    def __init__(
        self,
        contract: ModelValidatorSubcontract | None = None,
        repo: str = "omnibase_core",
        baseline_path: Path | None = None,
        repo_root: Path | None = None,
    ) -> None:
        super().__init__(contract=contract)
        self._repo = repo
        self._baseline_path = baseline_path or _DEFAULT_BASELINE
        self._baseline: set[str] | None = None
        # repo_root anchors fingerprints to a stable repo-relative path.
        # When None, the absolute path is used (consistent per machine run).
        self._repo_root = repo_root

    def _get_baseline(self) -> set[str]:
        if self._baseline is None:
            self._baseline = load_baseline(self._baseline_path)
        return self._baseline

    def _validate_file(
        self,
        path: Path,
        contract: ModelValidatorSubcontract,
    ) -> tuple[ModelValidationIssue, ...]:
        if path.suffix not in {".py"}:
            return ()

        # Determine repo-relative path for stable fingerprints.
        if self._repo_root is not None:
            try:
                rel = str(path.relative_to(self._repo_root))
            except ValueError:
                rel = path.name
        else:
            rel = path.name

        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ()

        raw_violations = scan_source(self._repo, rel, source)
        baseline = self._get_baseline()
        new, _ = partition_against_baseline(raw_violations, baseline)

        issues: list[ModelValidationIssue] = []
        for v in new:
            enabled, severity = self._get_rule_config(v.rule, contract)
            if not enabled:
                continue
            issues.append(
                ModelValidationIssue(
                    severity=severity,
                    message=(
                        f"url-authority violation [{v.rule}]: {v.snippet!r} — "
                        "migrate to the routing authority/integration catalog, or "
                        "annotate # url-authority-ok: <reason>"
                    ),
                    code=v.rule,
                    file_path=path,
                    line_number=v.line,
                    rule_name=v.rule,
                )
            )
        return tuple(issues)


# ---------------------------------------------------------------------------
# CLI — pre-commit hook + CI gate
# ---------------------------------------------------------------------------


def _err(msg: str) -> None:
    sys.stderr.write(msg + "\n")


def _out(msg: str) -> None:
    sys.stdout.write(msg + "\n")


def _update_baseline(
    repo: str, repo_root: Path, baseline_path: Path, *, seed: bool
) -> int:
    """Regenerate this repo's baseline subset (burn-down only)."""
    prior_entries: list[dict[str, str]] = []
    if baseline_path.exists():
        data = json.loads(baseline_path.read_text(encoding="utf-8"))
        all_entries = data.get("violations", []) if isinstance(data, dict) else []
        prior_entries = [
            e for e in all_entries if isinstance(e, dict) and "fingerprint" in e
        ]
    repo_before = {e["fingerprint"] for e in prior_entries if e.get("repo") == repo}
    other_entries = [e for e in prior_entries if e.get("repo") != repo]

    fresh_violations = scan_tree(repo, repo_root)
    fresh: list[dict[str, str]] = [
        {
            "repo": v.repo,
            "path": v.path,
            "rule": v.rule,
            "fingerprint": v.fingerprint,
        }
        for v in fresh_violations
    ]
    repo_after = {e["fingerprint"] for e in fresh}

    if not seed:
        try:
            assert_baseline_shrinks_only(repo_before, repo_after)
        except ValueError as exc:
            _err(f"URL-AUTHORITY BASELINE REJECTED: {exc}")
            return 1

    merged = sorted(
        [*other_entries, *fresh],
        key=lambda e: (e["repo"], e["path"], e["fingerprint"]),
    )
    baseline_path.parent.mkdir(parents=True, exist_ok=True)
    baseline_path.write_text(
        json.dumps(
            {"schema_version": "1.0.0", "count": len(merged), "violations": merged},
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    action = "seeded" if seed else f"burned down {len(repo_before) - len(repo_after)}"
    _out(
        f"URL-AUTHORITY BASELINE updated for {repo}: {len(repo_after)} violation(s) "
        f"({action}). Total across repos: {len(merged)}."
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entry point.

    Staged-files mode (pre-commit): pass file paths as positional args.
    Full-repo mode (CI): pass ``--all --repo <name> --repo-root <path>``.
    Baseline update: pass ``--seed`` or ``--update-baseline``.

    Exit codes:
        0 — no new violations (or grandfathered-only)
        1 — new violation(s) found or baseline grew
    """
    import argparse

    parser = argparse.ArgumentParser(
        prog="check-url-authority",
        description="url-authority ratchet gate (OMN-12818).",
    )
    parser.add_argument(
        "paths", nargs="*", help="Explicit files to scan (staged set, pre-commit mode)."
    )
    parser.add_argument(
        "--repo", default="omnibase_core", help="Repo name for fingerprints."
    )
    parser.add_argument(
        "--repo-root", default=".", help="Repo root for repo-relative paths."
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Full-repo scan (CI mode) instead of explicit staged files.",
    )
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="Regenerate this repo's baseline subset (burn-down only).",
    )
    parser.add_argument(
        "--seed",
        action="store_true",
        help="One-time initialization of this repo's baseline subset (no shrink check).",
    )
    parser.add_argument(
        "--baseline",
        default=str(_DEFAULT_BASELINE),
        help="Path to the baseline JSON.",
    )
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root)
    baseline_path = Path(args.baseline)

    if args.update_baseline or args.seed:
        return _update_baseline(args.repo, repo_root, baseline_path, seed=args.seed)

    if args.all:
        violations = scan_tree(args.repo, repo_root)
    else:
        if not args.paths:
            _out("URL-AUTHORITY GATE: no files to scan.")
            return 0
        violations = []
        for raw in args.paths:
            p = Path(raw)
            if not p.is_file() or p.suffix != ".py":
                continue
            try:
                source = p.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            try:
                rel = str(p.resolve().relative_to(repo_root.resolve()))
            except ValueError:
                rel = str(p)
            violations.extend(scan_source(args.repo, rel, source))

    baseline = load_baseline(baseline_path)
    new, grandfathered = partition_against_baseline(violations, baseline)

    if new:
        _err(
            f"URL-AUTHORITY GATE FAILED: {len(new)} NEW violation(s) — every URL must "
            "resolve from a contract (routing authority / integration catalog), not a "
            "literal or a *_URL/*_ENDPOINT env read.\n"
        )
        for v in new:
            _err(f"  [{v.rule}] {v.repo}/{v.path}:{v.line}")
            _err(f"    {v.snippet}")
            _err(
                "    -> migrate to the resolver, or annotate "
                "# url-authority-ok: <reason>"
            )
        return 1

    _out(
        f"URL-AUTHORITY GATE PASSED: 0 new violations "
        f"({len(grandfathered)} grandfathered)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
