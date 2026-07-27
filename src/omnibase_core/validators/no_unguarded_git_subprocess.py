# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Block unguarded ``git`` subprocess invocations in test files (OMN-14891).

THE DEFECT
----------
A test fixture that shells out to git inside a ``tmp_path`` directory::

    subprocess.run(["git", "init"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@t.t"], cwd=repo, check=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "x"], cwd=repo, check=True)

is safe *in isolation*. It is NOT safe when pytest runs as a subprocess of the
repo's own pre-push hook: git exports ``GIT_DIR`` / ``GIT_WORK_TREE`` /
``GIT_INDEX_FILE`` / ``GIT_COMMON_DIR`` into every hook's environment, and those
variables **override both ``-C`` and ``cwd``**. The child git command therefore
silently targets the REAL invoking worktree.

Observed damage (twice, log-proven): the shared canonical clone's ``.git/config``
was rewritten (``core.bare = true`` from a fixture ``git init``, plus a bogus
``[user]`` block), 6707 lines of phantom staged deletions were written into the
real index, and an amend then committed that index as a 6668-file deletion.
``$OMNI_HOME/<repo>/.git/config`` is shared by every worktree of that repo, so
one session's test run corrupts every concurrent session.

WHY THIS GATE EXISTS
--------------------
OMN-14744 fixed exactly one file in omnibase_infra. The class then recurred in a
different repo across five different files. Per-file patching does not hold, so
the remedy is systemic: a session-level ``os.environ`` scrub in the top-level
``tests/conftest.py`` (the primary remedy) **plus** this gate, which keeps a new
unguarded call from being introduced (CLAUDE.md Rule #5 — a detection surface
that is not wired as a gate gets ignored).

THE RULE
--------
Inside test files, a ``subprocess`` call whose argv begins with the literal
``"git"`` must pass an explicit ``env=``, and that ``env=`` expression must be
provably free of the inherited git location variables. Three acceptance tiers:

1. **canonical helper** — the env expression references a helper whose name is in
   :data:`CANONICAL_SCRUB_NAMES` (e.g. ``scrub_git_location_env``).
2. **full replacement** — the env expression is a dict/``dict(...)`` literal that
   never reads ``os.environ``. A replacement environment cannot inherit
   ``GIT_DIR``, so it is safe by construction.
3. **verified local scrub** — the env expression references a helper function that
   removes every variable in :data:`GIT_LOCATION_ENV_VARS`, or the call is
   lexically enclosed by a function that performs that removal inline (the shape
   the existing per-file fixes use: build ``env``, pop the vars, pass ``env=env``).

Anything else fails CLOSED, including a bare ``env=os.environ.copy()``.

Additionally, ``git config --global`` / ``--system`` is rejected outright in test
files: an ``os.environ`` scrub fixes *location*, but it does not stop a fixture
from deliberately writing the real user's ``~/.gitconfig``.

Usage::

    python -m omnibase_core.validators.no_unguarded_git_subprocess tests/

When pre-commit supplies staged filenames, each is scanned. When no paths are
supplied, ``tests/`` is scanned.
"""

from __future__ import annotations

import argparse
import ast
import os
import sys
from collections.abc import Iterator, Mapping, MutableMapping, Sequence
from pathlib import Path

from omnibase_core.models.validation.model_git_subprocess_finding import (
    ModelGitSubprocessFinding,
)

DEFAULT_SCAN_ROOT = Path("tests")

# The git environment variables that OVERRIDE `-C` and `cwd`. These are the
# variables that produced the OMN-14891 / OMN-14892 corruption; a scrub that
# misses any one of them is not a scrub. `GIT_CEILING_DIRECTORIES` is scrubbed by
# the conftest fixture too, but it can only make discovery fail (never redirect
# it at the real repo), so it is not required of a module-local helper here.
GIT_LOCATION_ENV_VARS: tuple[str, ...] = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_COMMON_DIR",
    "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
)

# Additionally scrubbed by the session fixture; see tests/conftest.py.
GIT_DISCOVERY_ENV_VARS: tuple[str, ...] = ("GIT_CEILING_DIRECTORIES",)

# Names that, when referenced inside an `env=` expression, mark the environment
# as canonically scrubbed.
CANONICAL_SCRUB_NAMES: frozenset[str] = frozenset(
    ("scrub_git_location_env", "scrubbed_git_env")
)

# subprocess entrypoints that execute an argv.
SUBPROCESS_CALLABLES: frozenset[str] = frozenset(
    ("run", "call", "check_call", "check_output", "Popen")
)

_ENVIRON_NAMES: frozenset[str] = frozenset(("environ", "os.environ"))

# `tests/fixtures/` holds inert data corpora consumed BY tests (including files
# that are deliberately syntactically invalid, e.g.
# tests/fixtures/validation/exports/syntax_error.py). Nothing there is executed
# as test code, so it is excluded from the scan rather than reported.
EXCLUDED_DIR_NAMES: frozenset[str] = frozenset(("fixtures", "__pycache__"))


# ---------------------------------------------------------------------------
# the remedy (kept in the same module as the guard so the two cannot drift)
# ---------------------------------------------------------------------------


def scrub_git_location_env(
    environ: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Return a copy of ``environ`` with inherited git overrides removed.

    Defaults to :data:`os.environ`. Removes every location override
    (:data:`GIT_LOCATION_ENV_VARS`), the discovery limiter
    (:data:`GIT_DISCOVERY_ENV_VARS`), and any ``GIT_CONFIG*`` override a hook or
    wrapper injected. Everything else (``PATH``, ``HOME``, ``GIT_AUTHOR_*``,
    ``GIT_COMMITTER_*``) is preserved, so commits still resolve an identity.
    """
    scrubbed = dict(os.environ if environ is None else environ)
    strip_git_location_env(scrubbed)
    return scrubbed


def strip_git_location_env(environ: MutableMapping[str, str]) -> tuple[str, ...]:
    """Remove inherited git overrides from ``environ`` IN PLACE.

    Returns the names actually removed, so a caller (the session fixture in
    ``tests/conftest.py``) can report what it neutralised.
    """
    removed: list[str] = []
    for key in tuple(environ):
        if key.startswith("GIT_CONFIG"):
            del environ[key]
            removed.append(key)
    for key in (*GIT_LOCATION_ENV_VARS, *GIT_DISCOVERY_ENV_VARS):
        if environ.pop(key, None) is not None:
            removed.append(key)
    return tuple(removed)


def validate_paths(paths: Sequence[Path]) -> list[ModelGitSubprocessFinding]:
    """Validate Python files under the provided paths."""
    findings: list[ModelGitSubprocessFinding] = []
    for path in _iter_python_files(paths):
        findings.extend(validate_file(path))
    return findings


def validate_file(path: Path) -> list[ModelGitSubprocessFinding]:
    """Validate one Python file for unguarded git subprocess calls."""
    try:
        source = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        return [
            ModelGitSubprocessFinding(
                path=path,
                line=1,
                column=0,
                call="<parse-error>",
                reason=f"could not decode as UTF-8: {exc}",
            )
        ]
    return validate_source(path, source)


def validate_source(path: Path, source: str) -> list[ModelGitSubprocessFinding]:
    """Validate in-memory ``source`` attributed to ``path``."""
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        return [
            ModelGitSubprocessFinding(
                path=path,
                line=exc.lineno or 1,
                column=exc.offset or 0,
                call="<syntax-error>",
                reason=exc.msg or "syntax error",
            )
        ]

    scrubbing_helpers = _scrubbing_helper_names(tree)
    enclosed_by_scrub = _calls_enclosed_by_scrub(tree)
    findings: list[ModelGitSubprocessFinding] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        call_name = _subprocess_call_name(node)
        if call_name is None:
            continue
        argv = _argv_elements(node)
        if argv is None or not _argv_is_git(argv):
            continue

        reason = _guard_reason(
            node,
            argv,
            scrubbing_helpers,
            enclosed_by_scrub=id(node) in enclosed_by_scrub,
        )
        if reason is None:
            continue
        findings.append(
            ModelGitSubprocessFinding(
                path=path,
                line=node.lineno,
                column=node.col_offset,
                call=call_name,
                reason=reason,
            )
        )
    return findings


# ---------------------------------------------------------------------------
# call classification
# ---------------------------------------------------------------------------


def _subprocess_call_name(node: ast.Call) -> str | None:
    """Return the dotted name if ``node`` invokes a subprocess entrypoint."""
    name = _qualified_expr_name(node.func)
    if name is None:
        return None
    tail = name.rsplit(".", maxsplit=1)[-1]
    if tail not in SUBPROCESS_CALLABLES:
        return None
    # `subprocess.run(...)` / `sp.run(...)` / bare `run(...)` all qualify; a
    # `self.run(...)` / `client.check_output(...)` method call does not execute
    # an argv, but it also cannot have a literal `["git", ...]` first arg in
    # practice, so argv classification below filters those out anyway.
    return name


def _argv_elements(node: ast.Call) -> list[ast.expr] | None:
    """Return the literal argv sequence elements, if the first arg is one."""
    if not node.args:
        return None
    first = node.args[0]
    if isinstance(first, (ast.List, ast.Tuple)):
        return list(first.elts)
    return None


def _argv_is_git(argv: Sequence[ast.expr]) -> bool:
    """True when the argv's program (element 0) is the literal string ``git``."""
    if not argv:
        return False
    head = argv[0]
    return isinstance(head, ast.Constant) and head.value == "git"


# ---------------------------------------------------------------------------
# guard evaluation
# ---------------------------------------------------------------------------


def _guard_reason(
    node: ast.Call,
    argv: Sequence[ast.expr],
    scrubbing_helpers: frozenset[str],
    *,
    enclosed_by_scrub: bool,
) -> str | None:
    """Return a failure reason, or None when the call is adequately guarded."""
    global_config = _global_config_reason(argv)
    if global_config is not None:
        return global_config

    env_kwarg = next(
        (kw.value for kw in node.keywords if kw.arg == "env"),
        None,
    )
    if env_kwarg is None:
        return (
            "no env= keyword, so GIT_DIR/GIT_WORK_TREE/GIT_INDEX_FILE inherited "
            "from a git hook override cwd and -C and retarget the real worktree"
        )
    if enclosed_by_scrub or _env_is_scrubbed(env_kwarg, scrubbing_helpers):
        return None
    return (
        "env= is derived from the ambient environment without removing "
        f"{', '.join(GIT_LOCATION_ENV_VARS)}"
    )


def _global_config_reason(argv: Sequence[ast.expr]) -> str | None:
    """Reject `git config --global/--system`, which escapes any env scrub."""
    literals = [
        element.value
        for element in argv
        if isinstance(element, ast.Constant) and isinstance(element.value, str)
    ]
    if "config" not in literals:
        return None
    for scope in ("--global", "--system"):
        if scope in literals:
            return (
                f"`git config {scope}` writes the real user's git configuration; "
                "an env scrub cannot contain it"
            )
    return None


def _env_is_scrubbed(env: ast.expr, scrubbing_helpers: frozenset[str]) -> bool:
    """True when the ``env=`` expression provably drops the git location vars."""
    referenced = _referenced_names(env)

    # Tier 1: the canonical shared scrub helper.
    if referenced & CANONICAL_SCRUB_NAMES:
        return True
    # Tier 3: a verified module-local scrub helper.
    if referenced & scrubbing_helpers:
        return True
    # Tier 2: a full replacement environment that never reads os.environ.
    return _is_replacement_env(env) and not (referenced & _ENVIRON_NAMES)


def _is_replacement_env(env: ast.expr) -> bool:
    """True for dict literals / ``dict(...)`` / ``{**a, **b}`` constructions."""
    if isinstance(env, ast.Dict):
        return True
    if isinstance(env, ast.Call):
        return _qualified_expr_name(env.func) == "dict"
    return False


def _scrubbing_helper_names(tree: ast.Module) -> frozenset[str]:
    """Names of functions that remove every git location var."""
    return frozenset(fn.name for fn in _scrubbing_functions(tree))


def _calls_enclosed_by_scrub(tree: ast.Module) -> frozenset[int]:
    """``id()`` of every Call lexically inside a function that scrubs inline.

    This is the shape the pre-existing per-file fixes use: a ``_git(...)`` helper
    copies ``os.environ``, pops the location vars, and passes ``env=env`` to the
    subprocess call in the same function body. The ``env=`` expression is then a
    bare local name that carries no static evidence on its own.
    """
    enclosed: set[int] = set()
    for fn in _scrubbing_functions(tree):
        for node in ast.walk(fn):
            if isinstance(node, ast.Call):
                enclosed.add(id(node))
    return frozenset(enclosed)


def _scrubbing_functions(
    tree: ast.Module,
) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and _drops_all(node)
    ]


def _drops_all(func: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """True when ``func`` removes every variable in GIT_LOCATION_ENV_VARS."""
    dropped: set[str] = set()
    for node in ast.walk(func):
        # `env.pop("GIT_DIR", None)` / `env.pop("GIT_DIR")`
        if isinstance(node, ast.Call):
            name = _qualified_expr_name(node.func)
            if name is not None and name.rsplit(".", maxsplit=1)[-1] == "pop":
                dropped.update(_string_constants(node.args))
            continue
        # `del env["GIT_DIR"]`
        if isinstance(node, ast.Delete):
            for target in node.targets:
                if isinstance(target, ast.Subscript):
                    dropped.update(_string_constants([target.slice]))
        # `for key in ("GIT_DIR", ...): env.pop(key, None)` — the loop iterable
        # supplies the names; the pop above contributes the `key` variable, so
        # harvest the literals from the iterable directly.
        if isinstance(node, ast.For):
            dropped.update(_iterable_string_constants(node.iter))
    return set(GIT_LOCATION_ENV_VARS).issubset(dropped)


def _string_constants(nodes: Sequence[ast.expr]) -> set[str]:
    return {
        node.value
        for node in nodes
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }


def _iterable_string_constants(node: ast.expr) -> set[str]:
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return _string_constants(list(node.elts))
    if isinstance(node, ast.Call):
        # `tuple(("GIT_DIR", ...))` / `frozenset([...])`
        collected: set[str] = set()
        for arg in node.args:
            collected |= _iterable_string_constants(arg)
        return collected
    return set()


# ---------------------------------------------------------------------------
# shared helpers
# ---------------------------------------------------------------------------


def _referenced_names(node: ast.expr) -> frozenset[str]:
    """All simple and dotted names appearing anywhere inside ``node``."""
    names: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Name):
            names.add(child.id)
        elif isinstance(child, ast.Attribute):
            qualified = _qualified_expr_name(child)
            if qualified is not None:
                names.add(qualified)
                names.add(qualified.rsplit(".", maxsplit=1)[-1])
    return frozenset(names)


def _qualified_expr_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _qualified_expr_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    if isinstance(node, ast.Subscript):
        return _qualified_expr_name(node.value)
    if isinstance(node, ast.Call):
        return _qualified_expr_name(node.func)
    return None


def _iter_python_files(paths: Sequence[Path]) -> Iterator[Path]:
    scan_paths = tuple(paths) or (DEFAULT_SCAN_ROOT,)
    for path in scan_paths:
        if path.is_file() and path.suffix == ".py":
            if not _is_excluded(path):
                yield path
        elif path.is_dir():
            yield from sorted(
                candidate
                for candidate in path.rglob("*.py")
                if not _is_excluded(candidate)
            )


def _is_excluded(path: Path) -> bool:
    return bool(EXCLUDED_DIR_NAMES.intersection(path.parts))


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Block git subprocess invocations in tests that inherit GIT_DIR, "
            "GIT_WORK_TREE, GIT_INDEX_FILE, or GIT_COMMON_DIR from a git hook."
        )
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[DEFAULT_SCAN_ROOT],
        help="Python file or directory paths to scan.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    findings = validate_paths(args.paths)
    if not findings:
        return 0

    sys.stderr.write("Unguarded git subprocess guard failed (OMN-14891):\n")
    for finding in findings:
        sys.stderr.write(f"  {finding.format()}\n")
    sys.stderr.write(
        "\nGit exports GIT_DIR / GIT_WORK_TREE / GIT_INDEX_FILE / GIT_COMMON_DIR into "
        "every hook environment, and those OVERRIDE both `cwd=` and `git -C`. A test "
        "fixture that shells out to git under a pre-push hook therefore mutates the "
        "REAL invoking worktree, not tmp_path.\n"
        "Fix: pass env=scrub_git_location_env(os.environ) (see tests/conftest.py), or "
        "pass a full replacement env dict that never reads os.environ.\n"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())  # error-ok: CLI entry point requires SystemExit
