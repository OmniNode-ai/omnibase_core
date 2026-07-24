# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Regression guard for the pre-push hook's bounded per-test timeout (OMN-14967).

Root cause: ``tests/pytest.ini`` declares its own ``addopts`` with no
``-n``/``--timeout``, and pytest's config-file discovery picks the nearest ini
to the invocation args (``tests/pytest.ini`` wins outright over
``pyproject.toml``'s ``[tool.pytest.ini_options]`` -- the two do not merge)
whenever the pre-push hook invokes ``uv run pytest tests/ ...``. That silently
drops the ``-n4``/``--timeout=60`` safety net that ``pyproject.toml`` declares,
so a long-running or GC-heavy test can hang the local suite for hours with no
bound.

CI is immune because ``.github/workflows/ci.yml`` passes ``-n`` and
``--timeout`` explicitly on the pytest command line, which wins regardless of
which ini file is discovered. This test statically asserts the pre-push hook
does the same -- both ``uv run pytest`` invocation lines in
``scripts/hooks/prepush_smart_tests.sh`` must carry an explicit ``-n`` worker
count and ``--timeout=`` value, so the hook can never again silently rely on
whichever ini file pytest happens to resolve.
"""

from __future__ import annotations

import re
from pathlib import Path

_HOOK_SCRIPT = (
    Path(__file__).resolve().parents[2] / "scripts" / "hooks" / "prepush_smart_tests.sh"
)


def _pytest_invocation_lines(script_text: str) -> list[str]:
    """Return only the lines that actually EXECUTE pytest -- i.e. start with
    ``uv run pytest`` -- excluding ``log "... uv run pytest ..."`` lines that
    merely mention the invocation for human-readable output."""
    return [
        line
        for line in script_text.splitlines()
        if line.strip().startswith("uv run pytest")
    ]


def _resolve_shell_var(script_text: str, var_name: str) -> str:
    """Extract the RHS of a ``VAR_NAME="..."`` assignment in the script, so
    invocation lines that reference the variable (``${VAR_NAME}``) can be
    resolved to their effective flags for assertion purposes."""
    match = re.search(rf'^{re.escape(var_name)}="([^"]*)"', script_text, re.MULTILINE)
    assert match, f'expected a `{var_name}="..."` assignment in the hook script'
    return match.group(1)


def _resolve_invocation(line: str, resolved_vars: dict[str, str]) -> str:
    resolved = line
    for name, value in resolved_vars.items():
        resolved = resolved.replace(f"${{{name}}}", value)
    return resolved


def test_hook_script_exists() -> None:
    assert _HOOK_SCRIPT.is_file(), f"expected pre-push hook at {_HOOK_SCRIPT}"


def test_every_pytest_invocation_has_bounded_timeout_and_parallelism() -> None:
    script_text = _HOOK_SCRIPT.read_text(encoding="utf-8")
    invocation_lines = _pytest_invocation_lines(script_text)

    # Sanity: the hook must actually invoke pytest at least twice (the
    # full-suite escalation branch and the impacted-subset branch) -- if this
    # count regresses to zero the assertions below would vacuously pass.
    assert len(invocation_lines) >= 2, (
        "expected at least 2 non-comment 'uv run pytest' invocation lines in "
        f"{_HOOK_SCRIPT} (full-suite branch + impacted-subset branch), "
        f"found {len(invocation_lines)}: {invocation_lines!r}"
    )

    resolved_vars = {
        "PREPUSH_TIMEOUT_FLAGS": _resolve_shell_var(
            script_text, "PREPUSH_TIMEOUT_FLAGS"
        )
    }

    for line in invocation_lines:
        resolved = _resolve_invocation(line, resolved_vars)
        assert re.search(r"-n\s?\d", resolved) or '-n "' in resolved, (
            f"pytest invocation missing an explicit -n worker count, which "
            f"leaves it exposed to tests/pytest.ini's addopts (no -n) "
            f"shadowing pyproject.toml's safety net: {line!r} (resolved: {resolved!r})"
        )
        assert "--timeout=" in resolved, (
            f"pytest invocation missing an explicit --timeout=, which leaves "
            f"it exposed to tests/pytest.ini's addopts (no --timeout) "
            f"shadowing pyproject.toml's safety net: {line!r} (resolved: {resolved!r})"
        )


def test_bounded_timeout_flags_defined_once_and_reused() -> None:
    """The hook should define the timeout flags once and reuse them, not
    hand-duplicate the flag string per invocation (drift risk)."""
    script_text = _HOOK_SCRIPT.read_text(encoding="utf-8")
    assert "PREPUSH_TIMEOUT_FLAGS" in script_text, (
        "expected a single PREPUSH_TIMEOUT_FLAGS variable defining the bounded "
        "-n/--timeout flags, reused by both pytest invocation branches"
    )
    assert script_text.count("${PREPUSH_TIMEOUT_FLAGS}") >= 2, (
        "expected PREPUSH_TIMEOUT_FLAGS to be referenced in both the "
        "full-suite and impacted-subset pytest invocations"
    )
