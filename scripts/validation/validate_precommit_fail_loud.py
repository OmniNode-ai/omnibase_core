#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
CI/pre-commit check: fail-loud meta-gate over .pre-commit-config.yaml
(OMN-14671, WS7 fan-out #7 of the OMN-14655 canary; logic ported byte-for-byte
from the omniclaude#1904 canary / omnimarket#1783 / omnibase_infra#2318 so every
surface enforces the identical rule).

DRIFT-2 (false-green hook) recurrence guard. The canary repo had gate wrappers
that silently degraded to a zero exit when a sibling script could not be
resolved -- a skipped gate that was byte-indistinguishable from a passing one.
This gate makes the fix a mechanism, not a one-off: it hard-fails (a) any gate
wrapper script that pairs a missing-dependency / WARN / SKIP signal with a
following zero exit (the recurring false-green shape), and (b) any hook
`stages:` value that `default_install_hook_types` does not cover, so a
pre-push/commit-msg hook can never silently go uninstalled again.

Scope: only scripts actually referenced by a `.pre-commit-config.yaml`
`entry:` for a `language: system` / `language: script` hook (plus the raw
`entry:` string itself, for inline `bash -c '...'` hooks). This deliberately
excludes unrelated automation under scripts/ (cron-*.sh, watchdog-*.sh, ...)
that are not pre-commit hooks at all.

Note: this prose deliberately avoids writing the detected token pair (a literal
zero-exit adjacent to a missing-path phrase) so the meta-gate does not flag its
own docstring when a hook `entry:` resolves this file directly.

Suppress a reviewed false positive with `# fail-loud-ok: <reason>` on the
flagged line.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = REPO_ROOT / ".pre-commit-config.yaml"

SUPPRESS_MARKER = "fail-loud-ok"

# Lines matching this shape are the false-green "missing prerequisite"
# signal. Deliberately narrow to "not found" (the literal phrase both real
# bugs fixed under OMN-14655 used) rather than a bare WARN/SKIP keyword --
# a broader match false-positives on legitimate WARN/SKIP branches that
# degrade gracefully for reasons unrelated to a missing sibling/dependency
# (e.g. "explicit approval receipt present -- allowed").
_DEGRADE_RE = re.compile(r"not\s+found", re.IGNORECASE)
_EXIT_ZERO_RE = re.compile(r"\bexit\s+0\b")
_WINDOW = 6  # lines of look-back from an `exit 0` for a degrade signal

# Env-var-name shapes commonly used for undocumented gate bypasses. The
# sanctioned bypass (`# skip-token-allowed: <receipt-id>`) is a *comment*
# marker checked by reject-deploy-gate-skip-token.sh, not an env-var
# conditional, and is not matched by this pattern. Identifiers ending in
# PATTERN/REGEX (e.g. $SKIP_PATTERN, a regex literal, not a toggle) are
# excluded -- they are pattern-holder variables, not bypass flags.
_SKIP_ENV_VAR_RE = re.compile(
    r"\$\{?\b\w*(SKIP|BYPASS)\w*(?<!PATTERN)(?<!REGEX)\b", re.IGNORECASE
)


def _is_suppressed(line: str) -> bool:
    return SUPPRESS_MARKER in line


def _scan_text(source: str, label: str) -> list[str]:
    """Return violation messages for one block of shell/entry text."""
    violations: list[str] = []
    lines = source.splitlines()

    for idx, line in enumerate(lines):
        if not _EXIT_ZERO_RE.search(line):
            continue
        if _is_suppressed(line):
            continue

        window_start = max(0, idx - _WINDOW)
        window = lines[window_start : idx + 1]
        if any(_DEGRADE_RE.search(w) and not _is_suppressed(w) for w in window):
            violations.append(
                f"{label}:{idx + 1}: `exit 0` near a not-found/WARN/SKIP "
                f"signal -- a gate that cannot run must fail loud (exit 1), "
                f"not silently pass. Suppress a reviewed false positive with "
                f"`# {SUPPRESS_MARKER}: <reason>`.\n    {line.strip()}"
            )
            continue

        # Env-var-gated bypass check (class c): only meaningful when an
        # env-var-shaped SKIP/BYPASS token appears in the same window as the
        # `exit 0`, guarding it via a conditional.
        if any(
            _SKIP_ENV_VAR_RE.search(w) and not _is_suppressed(w) for w in window
        ) and any("if" in w or "&&" in w for w in window):
            violations.append(
                f"{label}:{idx + 1}: `exit 0` conditioned on a SKIP/BYPASS-shaped "
                f"env var -- undocumented env-var bypasses defeat the gate. Route "
                f"through the sanctioned `# skip-token-allowed: <receipt-id>` "
                f"escape hatch (CLAUDE.md Rule #10) or suppress a reviewed false "
                f"positive with `# {SUPPRESS_MARKER}: <reason>`.\n    {line.strip()}"
            )

    return violations


def _resolve_script(entry: str) -> Path | None:
    """Best-effort extraction of a scripts/ or .pre-commit-hooks/ file the
    entry invokes, so its content can also be scanned."""
    for token in entry.replace("\n", " ").split():
        if token.endswith((".sh", ".py")) and token.startswith(
            ("scripts/", ".pre-commit-hooks/")
        ):
            candidate = REPO_ROOT / token
            if candidate.is_file():
                return candidate
    return None


def _iter_local_hooks(config: dict[str, Any]) -> list[dict[str, Any]]:
    hooks: list[dict[str, Any]] = []
    for repo in config.get("repos", []):
        if repo.get("repo") != "local":
            continue
        hooks.extend(repo.get("hooks", []))
    return hooks


def check_fail_loud(config: dict[str, Any]) -> list[str]:
    violations: list[str] = []
    seen_scripts: set[Path] = set()

    for hook in _iter_local_hooks(config):
        language = hook.get("language")
        if language not in ("system", "script"):
            continue
        entry = hook.get("entry", "")
        hook_id = hook.get("id", "<unknown>")

        violations.extend(_scan_text(entry, f"entry[{hook_id}]"))

        script_path = _resolve_script(entry)
        if script_path is not None and script_path not in seen_scripts:
            seen_scripts.add(script_path)
            text = script_path.read_text(encoding="utf-8")
            violations.extend(_scan_text(text, str(script_path.relative_to(REPO_ROOT))))

    return violations


def check_stage_coverage(config: dict[str, Any]) -> list[str]:
    """Every `stages:` value used by any hook must be installed by
    `default_install_hook_types`, else `pre-commit install` never wires it
    up and the hook silently never runs locally (DRIFT-2)."""
    violations: list[str] = []
    installed = set(config.get("default_install_hook_types") or [])
    # `manual` is intentionally never auto-installed (opt-in only stage).
    allowed_uninstalled = {"manual"}

    used_stages: set[str] = set()
    for repo in config.get("repos", []):
        for hook in repo.get("hooks", []):
            used_stages.update(hook.get("stages") or [])

    uncovered = used_stages - installed - allowed_uninstalled
    if uncovered:
        violations.append(
            "default_install_hook_types="
            f"{sorted(installed)} does not cover stage(s) {sorted(uncovered)} "
            "used by one or more hooks -- `pre-commit install` will never "
            "wire up those hook types, so the hook silently never runs "
            "locally. Either add the stage to default_install_hook_types or "
            "remove the hook's use of that stage."
        )
    return violations


def main() -> int:
    if not CONFIG_PATH.is_file():
        print(f"ERROR: {CONFIG_PATH} not found", file=sys.stderr)
        return 1

    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        print(f"ERROR: {CONFIG_PATH} did not parse to a mapping", file=sys.stderr)
        return 1

    violations = check_fail_loud(config) + check_stage_coverage(config)

    if violations:
        print(f"FAIL: {len(violations)} fail-loud meta-gate violation(s):\n")
        for v in violations:
            print(f"  {v}\n")
        return 1

    print(
        "OK: no false-green (exit-0-on-missing / env-var-bypass) or "
        "stages-coverage violations found."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
