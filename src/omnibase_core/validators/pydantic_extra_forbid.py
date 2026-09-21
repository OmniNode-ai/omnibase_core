# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Ratchet gate asserting explicit ``extra="forbid"`` on every Pydantic model (OMN-14515).

Operator ruling: ``extra`` is ``"forbid"`` for everything. ``extra="ignore"`` and
``extra="allow"`` are default-deny.

**This gate asserts the positive.** Pydantic's own default, when a model declares no
``model_config`` at all, is ``extra="ignore"`` — unknown fields are silently dropped.
So a model with *no config whatsoever* is already broken; it just never said so. A gate
that greps for the literal string ``extra="ignore"`` catches only the honest minority
(platform census: 858 implicit-default violations vs. 514 explicit ignore/allow).
Therefore: **absence of an explicit, inherited-or-declared ``extra="forbid"`` is a
violation.**

Four confirmed live silent-data-loss bugs came from exactly this — a consumer
hand-rolled a slim copy of a producer's event model with a permissive ``extra``, so
fields vanished on every message (OMN-14490, OMN-14506, OMN-14513, OMN-14514).
``extra="ignore"`` is what converts a *loud* schema mismatch into a *silent* one.

Resolution
----------
Two engines, runtime-authoritative:

1. **Runtime** (preferred): import the module, read the real ``cls.model_config``.
   Pydantic has already merged config down the MRO, so inheritance is exact — a model
   inheriting ``forbid`` from a compliant base IS compliant, with no hand-rolled MRO
   walk to get wrong.
2. **Static AST** (fallback, for files that cannot be imported): walk the class body,
   the class *keyword arguments*, and then the base classes recursively through the
   import graph.

The static engine handles the four extractor bugs a prior census lane hit — each of
which produces FALSE violations:

* ``model_config`` as an ``ast.AnnAssign`` (annotated), not just ``ast.Assign``.
* ``model_config = {"extra": "forbid"}`` as a plain **dict literal**, not only
  ``ConfigDict(...)`` (70 files platform-wide).
* ``class Foo(Base, extra="forbid")`` — ``extra`` as a **class keyword argument**, not
  in the body at all (14 files, incl. the whole ``ModelContextBundleL0``-``L4`` chain).
* Path-format (relative vs. absolute) mismatch when resolving modules to files.

``RootModel`` subclasses are exempt: Pydantic *rejects* ``extra`` on a ``RootModel``
(``PydanticUserError``), so demanding it would be an impossible-to-satisfy gate.

Ratchet, not allowlist
----------------------
* Any violation NOT in the frozen baseline fails — new models are blocked on day one.
* ``--enforce-modified <ref>`` also fails any *baselined* violation whose class body was
  touched by the diff: you may not edit a broken model and leave it broken.
* ``--check-stale`` fails when a baselined FQN is now compliant/absent — the baseline
  may only shrink, never coast.
* The only sanctioned suppression is an **expiring waiver** keyed to an open ticket AND
  PR (``extra_forbid_waivers.yaml``). An expired waiver is a hard failure, so a waiver
  cannot rot into an allowlist entry.

The existing violations are NOT burned down by hand: RSD regenerates the corpus with
``extra="forbid"`` emitted by construction. This gate exists so the *next* hand-written
model cannot be born broken.

Usage::

    # pre-commit (staged files) — full-tree ratchet + modified-model enforcement
    python -m omnibase_core.validators.pydantic_extra_forbid \
        --enforce-modified :staged src/omnibase_core

    # CI — full scan, stale-entry enforcement, modified-model enforcement vs. dev
    python -m omnibase_core.validators.pydantic_extra_forbid \
        --check-stale --enforce-modified origin/dev src/omnibase_core

    # (re)generate the frozen baseline
    python -m omnibase_core.validators.pydantic_extra_forbid \
        --write-baseline src/omnibase_core

DoD reference: OMN-14515 (parent OMN-14208).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Iterator, Sequence
from datetime import UTC, date, datetime
from pathlib import Path

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.validation.model_extra_forbid_baseline import (
    ModelExtraForbidBaseline,
)
from omnibase_core.models.validation.model_extra_forbid_finding import (
    ENGINE_RUNTIME,
    ENGINE_STATIC,
    ModelExtraForbidFinding,
)
from omnibase_core.models.validation.model_violation_waivers_document import (
    ModelViolationWaiversDocument,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_content_as_model

DEFAULT_SCAN_ROOT = Path("src/omnibase_core")
DEFAULT_BASELINE_PATH = Path(__file__).with_name("extra_forbid_baseline.yaml")
DEFAULT_WAIVERS_PATH = Path(__file__).with_name("extra_forbid_waivers.yaml")

STAGED_REF = ":staged"
from omnibase_core.validation.pydantic_module_index import (
    parse_module as _parse_module,
)
from omnibase_core.validation.pydantic_runtime_resolver import _RuntimeResolver
from omnibase_core.validation.pydantic_static_resolver import _StaticResolver


# ---------------------------------------------------------------------------
# Scan
# ---------------------------------------------------------------------------
def scan_paths(
    paths: Sequence[Path], *, use_runtime: bool = True
) -> list[ModelExtraForbidFinding]:
    """Return one finding per Pydantic model found under *paths* (compliant included)."""
    files = list(_iter_python_files(paths))
    static = _StaticResolver(paths)
    runtime = _RuntimeResolver() if use_runtime else None

    results: list[ModelExtraForbidFinding] = []
    for path in files:
        index = static.index_for_path(path)
        if index is None:
            continue
        runtime_module = runtime.load(path) if runtime is not None else None

        for class_name, node in index.classes.items():
            verdict: tuple[str, str | None, bool] | None = None
            engine = ENGINE_STATIC

            if runtime is not None and runtime_module is not None:
                verdict = runtime.verdict(runtime_module, class_name)
                if verdict is not None:
                    engine = ENGINE_RUNTIME

            if verdict is None:
                # Runtime could not speak (module unimportable, or the class is not
                # bound at module level) -> static fallback.
                if not static.is_pydantic_model(index.module, node):
                    continue
                if static.is_exempt(index.module, node):
                    continue
                status, extra = static.resolve_extra(index.module, node)
                verdict = (status, extra, False)
            elif verdict[2]:
                continue  # exempt (RootModel) or pydantic's own BaseModel

            status, extra, _ = verdict
            results.append(
                ModelExtraForbidFinding(
                    path=path,
                    line=node.lineno,
                    column=node.col_offset,
                    class_name=class_name,
                    module=index.module,
                    status=status,
                    effective_extra=extra,
                    engine=engine,
                )
            )
    return results


def _iter_python_files(paths: Sequence[Path]) -> Iterator[Path]:
    scan_paths_ = tuple(paths) or (DEFAULT_SCAN_ROOT,)
    seen: set[Path] = set()
    for path in scan_paths_:
        if path.is_file() and path.suffix == ".py":
            candidates: Iterator[Path] = iter((path,))
        elif path.is_dir():
            candidates = (
                candidate
                for candidate in sorted(path.rglob("*.py"))
                if "__pycache__" not in candidate.parts
            )
        else:
            continue
        for candidate in candidates:
            resolved = candidate.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            yield candidate


# ---------------------------------------------------------------------------
# Baseline (frozen ratchet) + waivers (expiring, ticket+PR-keyed)
# ---------------------------------------------------------------------------
def load_baseline(path: Path) -> set[str]:
    """Load the frozen ``module:ClassName`` violation baseline.

    A missing/unreadable baseline yields the empty set — fail-closed: every violation
    is then treated as NEW.
    """
    try:
        data = load_yaml_content_as_model(
            path.read_text(encoding="utf-8"), ModelExtraForbidBaseline
        )
    except (ModelOnexError, UnicodeDecodeError, OSError):
        return set()
    return set(data.violations)


def load_waivers(path: Path, today: date) -> tuple[set[str], list[str]]:
    """Return ``(active_waived_fqns, errors)``.

    A waiver MUST carry ``fqn``, ``ticket`` (OMN-NNNN), ``pr``, and an ``expires_at``
    date. Anything missing, malformed, or expired is an ERROR (hard failure) — never a
    silent pass. That is what keeps a waiver from decaying into an allowlist entry.
    """
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return set(), []
    try:
        data = load_yaml_content_as_model(raw, ModelViolationWaiversDocument)
    except ModelOnexError as exc:
        return set(), [f"waivers file is not valid YAML: {exc}"]
    entries = data.waivers

    active: set[str] = set()
    errors: list[str] = []
    for raw_entry in entries:
        fqn = str(raw_entry.get("fqn", "")).strip()
        ticket = str(raw_entry.get("ticket", "")).strip()
        pr = str(raw_entry.get("pr", "")).strip()
        expires_raw = raw_entry.get("expires_at")

        if not fqn:
            errors.append(f"waiver entry missing 'fqn': {raw_entry!r}")
            continue
        if not ticket.startswith("OMN-") or not ticket[4:].isdigit():
            errors.append(f"waiver {fqn}: 'ticket' must be an OMN-NNNN reference")
            continue
        if not pr:
            errors.append(f"waiver {fqn}: 'pr' (the in-flight PR) is required")
            continue

        expires = _coerce_date(expires_raw)
        if expires is None:
            errors.append(
                f"waiver {fqn}: 'expires_at' must be an ISO date (YYYY-MM-DD); "
                f"got {expires_raw!r}"
            )
            continue
        if expires < today:
            errors.append(
                f"waiver {fqn}: EXPIRED on {expires.isoformat()} (ticket {ticket}, {pr}) "
                f'— fix the model (extra="forbid") or renew the waiver with a new '
                f"expiry; an expired waiver is a hard failure by design"
            )
            continue
        active.add(fqn)
    return active, errors


def today_utc() -> date:
    """UTC "today" for waiver expiry — machine-timezone-independent by construction."""
    return datetime.now(UTC).date()


def _coerce_date(value: object) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value.strip())
        except ValueError:
            return None
    return None


def render_baseline(
    violations: Sequence[ModelExtraForbidFinding], scan_roots: Sequence[Path]
) -> str:
    fqns = sorted({finding.fqn for finding in violations})
    roots = ", ".join(str(root) for root in scan_roots)
    lines = [
        '# Frozen baseline for the extra="forbid" ratchet (OMN-14515).',
        "#",
        "# This is NOT an allowlist. It is a shrink-only ratchet of models that predate",
        "# the gate. New/modified models are blocked outright; --check-stale fails when",
        "# an entry here becomes compliant, forcing the count down. Do not hand-add.",
        "#",
        f"# scan roots: {roots}",
        f"# count: {len(fqns)}",
        "#",
        "# Regenerate: python -m omnibase_core.validators.pydantic_extra_forbid \\",
        f"#     --write-baseline {roots}",
        "",
        "violations:",
    ]
    lines.extend(f'  - "{fqn}"' for fqn in fqns)
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Modified-model enforcement (git diff -> changed line ranges)
# ---------------------------------------------------------------------------
def changed_line_ranges(ref: str, cwd: Path) -> dict[Path, list[tuple[int, int]]]:
    """Map absolute file path -> changed line ranges for *ref*.

    ``ref`` is either ``":staged"`` (pre-commit) or a git ref such as ``origin/dev``
    (CI, diffed as ``<ref>...HEAD``). Raises ``ModelOnexError`` on git failure — the
    caller fails closed rather than silently skipping the check.
    """
    if ref == STAGED_REF:
        args = ["git", "diff", "--cached", "--unified=0", "--no-color"]
    else:
        args = ["git", "diff", "--unified=0", "--no-color", f"{ref}...HEAD"]

    try:
        proc = subprocess.run(
            args, cwd=cwd, capture_output=True, text=True, check=False
        )
    except OSError as exc:
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.OPERATION_FAILED,
            message=f"could not run git: {exc}",
        ) from exc
    if proc.returncode != 0:
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.OPERATION_FAILED,
            message=(
                f"`{' '.join(args)}` failed (exit {proc.returncode}): "
                f"{proc.stderr.strip() or 'no stderr'}"
            ),
        )

    try:
        top = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.OPERATION_FAILED,
            message=f"could not resolve the git worktree root: {exc}",
        ) from exc

    root = Path(top)
    ranges: dict[Path, list[tuple[int, int]]] = {}
    current: Path | None = None
    for line in proc.stdout.splitlines():
        if line.startswith("+++ "):
            target = line[4:].strip()
            if target == "/dev/null":
                current = None
            else:
                current = (
                    (root / target[2:]).resolve() if target.startswith("b/") else None
                )
        elif line.startswith("@@") and current is not None:
            span = _parse_hunk(line)
            if span is not None:
                ranges.setdefault(current, []).append(span)
    return ranges


def _parse_hunk(line: str) -> tuple[int, int] | None:
    # @@ -12,0 +13,4 @@ optional trailing context
    try:
        plus = line.split("+", 1)[1].split("@@", 1)[0].strip()
    except IndexError:
        return None
    start_str, _, count_str = plus.partition(",")
    try:
        start = int(start_str)
        count = int(count_str) if count_str else 1
    except ValueError:
        return None
    if count == 0:  # pure deletion; anchor on the surrounding line
        return start, start
    return start, start + count - 1


def _class_span(path: Path, finding: ModelExtraForbidFinding) -> tuple[int, int]:
    index = _parse_module(path, finding.module)
    node = index.classes.get(finding.class_name) if index is not None else None
    if node is None:
        return finding.line, finding.line
    return node.lineno, node.end_lineno or node.lineno


def _touched(
    finding: ModelExtraForbidFinding, ranges: dict[Path, list[tuple[int, int]]]
) -> bool:
    spans = ranges.get(finding.path.resolve())
    if not spans:
        return False
    start, end = _class_span(finding.path, finding)
    return any(not (hi < start or lo > end) for lo, hi in spans)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            'Assert every Pydantic model explicitly declares extra="forbid" '
            "(resolved through inheritance). Absence is a violation — Pydantic's "
            'default is extra="ignore", i.e. silent field-dropping (OMN-14515).'
        )
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[DEFAULT_SCAN_ROOT],
        help="Python file or directory paths to scan (default: src/omnibase_core).",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=DEFAULT_BASELINE_PATH,
        help="Path to the frozen violation baseline YAML.",
    )
    parser.add_argument(
        "--waivers",
        type=Path,
        default=DEFAULT_WAIVERS_PATH,
        help="Path to the expiring-waiver YAML (ticket + PR + expires_at).",
    )
    parser.add_argument(
        "--write-baseline",
        action="store_true",
        help="Regenerate the baseline from the current scan and exit 0.",
    )
    parser.add_argument(
        "--check-stale",
        action="store_true",
        help=(
            "Fail if a baselined FQN is now compliant or gone — the baseline may only "
            "shrink, never coast."
        ),
    )
    parser.add_argument(
        "--enforce-modified",
        metavar="REF",
        default=None,
        help=(
            "Also fail any BASELINED violation whose class body was touched by the "
            f"diff. REF is a git ref (diffed as REF...HEAD) or '{STAGED_REF}' for the "
            "staged diff. You may not edit a broken model and leave it broken."
        ),
    )
    parser.add_argument(
        "--no-runtime",
        action="store_true",
        help=(
            "Disable runtime introspection (real cls.model_config) and use the static "
            "AST engine only. Runtime is authoritative; this is an escape hatch."
        ),
    )
    parser.add_argument(
        "--json",
        dest="json_out",
        type=Path,
        default=None,
        help="Write the full per-class census (compliant + violations) as JSON.",
    )
    return parser.parse_args(list(argv))


def _write_json(path: Path, findings: Sequence[ModelExtraForbidFinding]) -> None:
    payload = [
        {
            "file": str(f.path),
            "module": f.module,
            "class": f.class_name,
            "line": f.line,
            "status": f.status,
            "effective_extra": f.effective_extra,
            "engine": f.engine,
            "compliant": not f.is_violation,
        }
        for f in sorted(findings, key=lambda f: (str(f.path), f.line))
    ]
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)

    findings = scan_paths(args.paths, use_runtime=not args.no_runtime)
    violations = [f for f in findings if f.is_violation]

    if args.json_out is not None:
        _write_json(args.json_out, findings)

    if args.write_baseline:
        args.baseline.write_text(
            render_baseline(violations, args.paths), encoding="utf-8"
        )
        runtime_count = sum(1 for f in findings if f.engine == ENGINE_RUNTIME)
        sys.stdout.write(
            f"wrote {args.baseline}: {len(violations)} violation(s) of "
            f"{len(findings)} model(s) "
            f"({runtime_count} resolved via runtime introspection, "
            f"{len(findings) - runtime_count} via static AST)\n"
        )
        return 0

    baseline = load_baseline(args.baseline)
    waived, waiver_errors = load_waivers(args.waivers, today_utc())

    present = {f.fqn for f in violations}
    new_violations = [
        f for f in violations if f.fqn not in baseline and f.fqn not in waived
    ]

    modified_violations: list[ModelExtraForbidFinding] = []
    if args.enforce_modified:
        try:
            ranges = changed_line_ranges(args.enforce_modified, Path.cwd())
        except ModelOnexError as exc:
            sys.stderr.write(
                f"pydantic-extra-forbid: --enforce-modified could not read the diff, "
                f"failing closed: {exc}\n"
            )
            return 1
        modified_violations = [
            f
            for f in violations
            if f.fqn in baseline and f.fqn not in waived and _touched(f, ranges)
        ]

    stale = sorted(baseline - present) if args.check_stale else []

    exit_code = 0

    if new_violations:
        exit_code = 1
        sys.stderr.write(
            "pydantic-extra-forbid: NEW Pydantic model(s) without an explicit "
            'extra="forbid":\n'
        )
        for finding in sorted(new_violations, key=lambda f: f.fqn):
            sys.stderr.write(f"  {finding.format()}\n")
        sys.stderr.write(
            '\n  Every model must declare extra="forbid" — inheriting it from a base is\n'
            '  fine. Pydantic\'s default is extra="ignore", which silently DROPS unknown\n'
            "  fields; four live data-loss bugs came from exactly that (OMN-14490,\n"
            "  OMN-14506, OMN-14513, OMN-14514). Fix:\n\n"
            '      model_config = ConfigDict(extra="forbid")\n\n'
            "  The baseline is not a place to add new entries. If this model is part of\n"
            "  sanctioned, time-boxed in-flight work, add an EXPIRING waiver keyed to the\n"
            f"  open ticket + PR in {args.waivers}. See OMN-14515.\n\n"
        )

    if modified_violations:
        exit_code = 1
        sys.stderr.write(
            "pydantic-extra-forbid: you MODIFIED baselined model(s) that still lack an "
            'explicit extra="forbid" — fix them now, do not leave them broken:\n'
        )
        for finding in sorted(modified_violations, key=lambda f: f.fqn):
            sys.stderr.write(f"  {finding.format()}\n")
        sys.stderr.write(
            "\n  Touching a model's body is your chance to fix it. Add\n"
            '  model_config = ConfigDict(extra="forbid") and remove the FQN from\n'
            f"  {args.baseline} so the ratchet counts down.\n\n"
        )

    if waiver_errors:
        exit_code = 1
        sys.stderr.write("pydantic-extra-forbid: waiver problem(s):\n")
        for error in waiver_errors:
            sys.stderr.write(f"  {error}\n")
        sys.stderr.write("\n")

    if stale:
        exit_code = 1
        sys.stderr.write(
            "pydantic-extra-forbid: STALE baseline entr(y/ies) — the model is now "
            "compliant or gone; delete the line so the ratchet counts down:\n"
        )
        for fqn in stale:
            sys.stderr.write(f"  {fqn}\n")
        sys.stderr.write("\n")

    if exit_code == 0:
        runtime_count = sum(1 for f in findings if f.engine == ENGINE_RUNTIME)
        sys.stdout.write(
            f"pydantic-extra-forbid: OK — {len(findings) - len(violations)}/"
            f'{len(findings)} model(s) declare extra="forbid"; '
            f"{len(violations)} baselined violation(s) remain "
            f"({runtime_count} resolved via runtime introspection).\n"
        )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())  # error-ok: validator CLI process exit
