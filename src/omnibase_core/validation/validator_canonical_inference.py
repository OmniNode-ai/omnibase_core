# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ValidatorCanonicalInference — reject non-canonical model-inference surfaces.

Part of OMN-13219 (enforcement gate: pre-commit + CI must catch non-canonical
code). The delegation ceiling tier shipped as a *shelled* ``codex`` CLI
execution (OMN-13215) — a non-canonical surface — and nothing caught it until a
live matrix run failed with "codex executable not found". Per CLAUDE.md Rule 5
(enforcement, not detection), a detection tool that is not a merge gate gets
ignored; this validator is wired as BOTH a pre-commit hook AND a required CI
status check.

Inference must go through the canonical inference path (the contract-driven
routing authority → bus → inference-effect → Bifrost), never a shelled CLI and
never a hardcoded/env-resolved model or provider.

Detects the following non-canonical patterns in Python source:

1. **model-cli-shellout** — a model-CLI binary name (``codex``, ``claude``,
   ``gemini``, ``opencode``) passed as the program to a subprocess/exec call
   (``subprocess.run``/``Popen``/``call``/``check_output``/``check_call``,
   ``asyncio.create_subprocess_exec``/``_shell``, ``os.system``) OR resolved via
   ``shutil.which(...)``. This is the canonical signal of "shell out to a model
   CLI as an inference/delegation tier."

2. **model-id-env-read** — ``os.environ[...]`` / ``os.environ.get(...)`` whose
   variable NAME ends in ``_MODEL`` / ``_MODEL_ID`` / ``_PROVIDER``. Model and
   provider must resolve from the routing-tiers / model_routing contract, not an
   env var. (Endpoint URLs and ``*_URL`` / ``*_ENDPOINT`` env reads are covered
   by the sibling URL-authority gate, OMN-12803/12818 — this validator does NOT
   re-implement those.)

The two scanners are complementary, not overlapping:
    - ``ValidatorUrlAuthority`` (OMN-12818) owns endpoint URLs + ``*_URL`` /
      ``*_ENDPOINT`` env reads + public-https literals.
    - ``ValidatorCanonicalInference`` (this file, OMN-13219) owns shelled model
      CLIs + ``*_MODEL`` / ``*_PROVIDER`` env reads.
    - The imperative-contract guard ``scan_freestanding_imperative_io``
      (OMN-12515/12540) owns freestanding imperative IO generally.

Ratchet (mirrors the OMN-12818 url-authority gate and the OMN-12791 receipt
gate): existing violations are grandfathered by content fingerprint (sha256 of
{repo, path, normalized-snippet}). Only NEW fingerprints fail the gate. The
baseline may only shrink (burn-down). The codex shell-out tracked by OMN-13215
is baselined explicitly with its removal ticket — a NEW shell-out fails closed.

Baseline per repo lives at:
``src/omnibase_core/validation/baselines/canonical_inference_baseline.json``

Usage Examples:
    Programmatic usage::

        from omnibase_core.validation.validator_canonical_inference import (
            ValidatorCanonicalInference,
        )

        v = ValidatorCanonicalInference()
        result = v.validate(Path("src/"))
        if not result.is_valid:
            for issue in result.issues:
                print(f"{issue.file_path}:{issue.line_number}: {issue.message}")

    CLI — pre-commit (staged files)::

        python -m omnibase_core.validation.validator_canonical_inference file1.py ...

    CLI — full repo scan (CI)::

        python -m omnibase_core.validation.validator_canonical_inference --all \\
            --repo omnibase_core --repo-root .

    CLI — seed / update baseline::

        python -m omnibase_core.validation.validator_canonical_inference \\
            --seed --repo omnibase_core --repo-root .

Suppression:
    Add ``# canonical-inference-ok: <reason>`` on the offending line. Free-text
    PR-body justification does NOT suppress — only the in-line annotation.

Migration debt:
    - codex/claude/gemini CLI shell-out removal: OMN-13215

Schema Version:
    v1.0.0 - Initial version (OMN-13219)
"""

from __future__ import annotations

import ast
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
from omnibase_core.models.validation.model_canonical_inference_violation import (
    ModelCanonicalInferenceViolation,
)
from omnibase_core.validation.validator_base import ValidatorBase

# ---------------------------------------------------------------------------
# Detection configuration
# ---------------------------------------------------------------------------

# Model-CLI binary names that must never be shelled out for inference.
MODEL_CLI_BINARIES: Final[frozenset[str]] = frozenset(
    {"codex", "claude", "gemini", "opencode"}
)

# Subprocess/exec callables whose FIRST string/list arg is the program.
# Stored as the trailing attribute name; the full dotted path is matched too.
_SUBPROCESS_CALLS: Final[frozenset[str]] = frozenset(
    {
        "subprocess.run",
        "subprocess.Popen",
        "subprocess.call",
        "subprocess.check_output",
        "subprocess.check_call",
        "asyncio.create_subprocess_exec",
        "asyncio.create_subprocess_shell",
        "os.system",
        "os.popen",
    }
)

# ``shutil.which("codex")`` is the canonical "is the CLI on PATH" probe that
# precedes a shell-out — treat it as the same violation class.
_WHICH_CALL: Final[str] = "shutil.which"

# Env-var name suffixes that must resolve from the routing contract instead.
_MODEL_ENV_SUFFIXES: Final[tuple[str, ...]] = ("_MODEL", "_MODEL_ID", "_PROVIDER")

# ``os.environ[...]`` / ``os.environ.get(...)`` for a model/provider name.
_ENV_MODEL_READ: Final[re.Pattern[str]] = re.compile(
    rf"""os\.environ(?:\.get\(\s*|\[\s*)["'][A-Z0-9_]*(?:{"|".join(re.escape(suffix) for suffix in _MODEL_ENV_SUFFIXES)})["']""",
)

# Suppression annotation.
_SUPPRESS_ANNOTATION: Final[str] = "# canonical-inference-ok:"

# Rule identifiers (must match the validation contract).
RULE_MODEL_CLI_SHELLOUT: Final[str] = "model-cli-shellout"
RULE_MODEL_ENV_READ: Final[str] = "model-id-env-read"

# Directories excluded from full-tree scans.
_EXCLUDED_PARTS: Final[frozenset[str]] = frozenset(
    {
        ".git",
        ".venv",
        "venv",
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
    Path(__file__).parent / "baselines" / "canonical_inference_baseline.json"
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
# AST helpers
# ---------------------------------------------------------------------------


def _dotted_call_name(func: ast.expr) -> str | None:
    """Return the dotted name of a call target (e.g. ``subprocess.run``)."""
    if isinstance(func, ast.Attribute):
        parent = _dotted_call_name(func.value)
        return f"{parent}.{func.attr}" if parent else func.attr
    if isinstance(func, ast.Name):
        return func.id
    return None


def _string_literals(node: ast.expr) -> list[str]:
    """Collect direct string-literal values from an expr (Constant or list)."""
    out: list[str] = []
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        out.append(node.value)
    elif isinstance(node, (ast.List, ast.Tuple)):
        for elt in node.elts:
            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                out.append(elt.value)
    return out


def _program_token(value: str) -> str:
    """Reduce a program string to its bare binary name (strip path / args)."""
    # Take the first whitespace-delimited token (handles os.system("codex ...")),
    # then the basename (handles "/usr/bin/codex").
    first = value.strip().split()[0] if value.strip() else ""
    return first.rsplit("/", maxsplit=1)[-1]


def _cli_binary_in_call(call: ast.Call) -> str | None:
    """Return the model-CLI binary name a subprocess/which call targets, else None.

    For subprocess/exec calls, inspects the first positional arg (the program or
    argv). For ``shutil.which``, inspects the first positional arg (the name).
    """
    name = _dotted_call_name(call.func)
    if name is None:
        return None

    if name == _WHICH_CALL:
        for literal in (lit for arg in call.args[:1] for lit in _string_literals(arg)):
            token = _program_token(literal)
            if token in MODEL_CLI_BINARIES:
                return token
        return None

    if name in _SUBPROCESS_CALLS or name.rsplit(".", maxsplit=1)[-1] in {
        n.rsplit(".", maxsplit=1)[-1] for n in _SUBPROCESS_CALLS
    }:
        # First positional arg is the program (str) or argv (list whose head is
        # the program).
        if not call.args:
            return None
        first = call.args[0]
        literals = _string_literals(first)
        # For a list/tuple argv, only the HEAD element is the program.
        if isinstance(first, (ast.List, ast.Tuple)):
            literals = literals[:1]
        for literal in literals:
            token = _program_token(literal)
            if token in MODEL_CLI_BINARIES:
                return token
    return None


# ---------------------------------------------------------------------------
# Source scanner
# ---------------------------------------------------------------------------


def _is_test_path(path: str) -> bool:
    lowered = path.lower()
    return "test" in lowered or "conftest" in lowered


def _line_suppressed(raw_line: str) -> bool:
    return _SUPPRESS_ANNOTATION in raw_line


def scan_source(
    repo: str, path: str, source: str
) -> list[ModelCanonicalInferenceViolation]:
    """Scan one source file's text for non-canonical-inference violations.

    Test files are skipped. Lines carrying ``# canonical-inference-ok:`` are
    suppressed. Returns at most one violation per line.

    Args:
        repo: Repo name used in fingerprints (e.g. ``"omnibase_core"``).
        path: Repo-relative path for fingerprints (e.g. ``"src/pkg/file.py"``).
        source: Full source text of the file.

    Returns:
        Sorted (by line) list of violations found in the file.
    """
    if _is_test_path(path):
        return []

    raw_lines = source.splitlines()
    violations: dict[int, ModelCanonicalInferenceViolation] = {}

    def _add(line: int, rule: str) -> None:
        if line in violations:
            return
        raw = raw_lines[line - 1] if 1 <= line <= len(raw_lines) else ""
        if _line_suppressed(raw):
            return
        snippet = raw.strip()[:200]
        violations[line] = ModelCanonicalInferenceViolation(
            repo=repo,
            path=path,
            line=line,
            rule=rule,
            snippet=snippet,
            fingerprint=make_fingerprint(repo, path, snippet),
        )

    # Rule 1: model-CLI shell-out (AST — robust against false positives).
    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError:
        tree = None
    if tree is not None:
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                binary = _cli_binary_in_call(node)
                if binary is not None:
                    _add(node.lineno, RULE_MODEL_CLI_SHELLOUT)

    # Rule 2: model/provider env read (line regex — env reads are single-line).
    for index, raw_line in enumerate(raw_lines, start=1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if _ENV_MODEL_READ.search(raw_line):
            _add(index, RULE_MODEL_ENV_READ)

    return [violations[line] for line in sorted(violations)]


def scan_tree(repo: str, repo_root: Path) -> list[ModelCanonicalInferenceViolation]:
    """Scan all ``*.py`` under ``repo_root`` for non-canonical-inference violations.

    Paths in the returned violations are repo-relative so fingerprints are
    machine-independent. Excludes vendored, build, test, and evidence dirs.

    Args:
        repo: Repo name for fingerprints.
        repo_root: Absolute path to the repository root.

    Returns:
        List of violations.
    """
    violations: list[ModelCanonicalInferenceViolation] = []
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
    """Load the frozen fingerprint set from the baseline JSON. Missing file = empty."""
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
    violations: list[ModelCanonicalInferenceViolation],
    baseline_fingerprints: set[str],
) -> tuple[
    list[ModelCanonicalInferenceViolation], list[ModelCanonicalInferenceViolation]
]:
    """Split violations into (new, grandfathered) by baseline membership.

    Returns:
        Tuple of (new_violations, grandfathered_violations). New violations fail
        the gate; grandfathered ones pass.
    """
    new: list[ModelCanonicalInferenceViolation] = []
    grandfathered: list[ModelCanonicalInferenceViolation] = []
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
        # Standard-Python boundary validation in a pure helper; mirrors
        # ValidatorUrlAuthority.assert_baseline_shrinks_only — no OnexError context
        # is meaningful here and this runs as a CLI/anti-gaming assertion.
        # error-ok: standard-library boundary assertion in a pure CLI helper
        raise ValueError(
            "canonical-inference baseline grew: "
            f"{len(added)} new fingerprint(s) added. The baseline is burn-down "
            "only — fix the violation or annotate with # canonical-inference-ok:, "
            "never add it to the baseline. Offending fingerprints: "
            f"{sorted(added)[:5]}"
        )


def serialize_baseline(
    violations: list[ModelCanonicalInferenceViolation],
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


class ValidatorCanonicalInference(ValidatorBase):
    """Reject NEW non-canonical model-inference surfaces.

    Wraps the canonical-inference ratchet as a standard ValidatorBase subclass so
    it participates in the ecosystem-wide validation pipeline (pre-commit hooks,
    CI required checks, cross-repo wiring).

    The validator ONLY reports violations that are NEW (not in the per-repo
    baseline). Existing (grandfathered) violations are silently skipped until they
    are fixed and the baseline is shrunk. The codex shell-out tracked by OMN-13215
    is the seeded baseline.
    """

    validator_id: ClassVar[str] = "canonical_inference"

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
        if path.suffix != ".py":
            return ()

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
                        f"non-canonical inference [{v.rule}]: {v.snippet!r} — route "
                        "inference through the contract-driven routing authority "
                        "(bus / inference-effect / Bifrost); resolve model + provider "
                        "from the routing contract. Annotate "
                        "# canonical-inference-ok: <reason> only with a real waiver."
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
            _err(f"CANONICAL-INFERENCE BASELINE REJECTED: {exc}")
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
        f"CANONICAL-INFERENCE BASELINE updated for {repo}: {len(repo_after)} "
        f"violation(s) ({action}). Total across repos: {len(merged)}."
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
        prog="check-canonical-inference",
        description="canonical-inference ratchet gate (OMN-13219).",
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
            _out("CANONICAL-INFERENCE GATE: no files to scan.")
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
            f"CANONICAL-INFERENCE GATE FAILED: {len(new)} NEW violation(s) — inference "
            "must go through the contract-driven routing authority (bus / "
            "inference-effect / Bifrost); model + provider resolve from the routing "
            "contract, never a shelled model CLI or env var.\n"
        )
        for v in new:
            _err(f"  [{v.rule}] {v.repo}/{v.path}:{v.line}")
            _err(f"    {v.snippet}")
            _err(
                "    -> route through the canonical inference path, or annotate "
                "# canonical-inference-ok: <reason>"
            )
        return 1

    _out(
        f"CANONICAL-INFERENCE GATE PASSED: 0 new violations "
        f"({len(grandfathered)} grandfathered)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
