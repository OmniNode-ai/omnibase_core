# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Skill-dispatch receipt-mode validator (OMN-13098).

Enforces the skill-output-suppression governing simplification — **a dispatch
skill IS one CLI call**. Dispatch-only shim skills must shrink to frontmatter +
the single receipt-mode command + result presentation; all glue lives in the
``onex skill`` / ``onex delegate`` CLI entrypoint.

Four checks, applied to every skill under ``plugins/onex/skills/``:

(a) **skill_kind** — every skill declares ``skill_kind: dispatch | methodology``
    in its frontmatter. Classification is explicit, never heuristic. A missing
    or invalid value FAILS.
(b) **bare dispatch invocation** — a ``dispatch`` skill's markdown may not
    contain a bare ``onex (run|node|run-node)`` invocation; the only accepted
    dispatch form is the single ``onex skill`` / ``onex delegate`` receipt-mode
    command.
(c) **no executable logic** — a ``dispatch`` skill directory must contain only
    markdown: no ``*.py``, no ``_lib/`` directory, no shell scripts.
(d) **prompt-instruction consistency** — a ``dispatch`` skill may not instruct
    Claude to ``cat workflow_result.json`` or "surface the JSON verbatim";
    receipt mode already prints exactly one typed result, and such an
    instruction conflicts with the hook backstop that suppresses raw output.

Ratchet
-------
``--allowlist <path>`` points at the YAML ratchet file
(``omniclaude/.onex_ratchets/skill_receipt_mode_allowlist.yaml``) listing skills
that were not yet migrated when the gate was introduced. A listed skill's
findings are tolerated. The gate FAILS if:

* the allowlist GROWS — a skill produces findings but is not listed AND was not
  present at gate introduction (i.e. any non-allowlisted skill with findings);
* a migrated skill REGRESSES — covered by the same rule (a clean skill that is
  listed is a *stale* entry and also FAILS, forcing the allowlist to shrink);
* a listed skill no longer exists (stale entry);
* a new skill ships a dispatch command without receipt mode (non-allowlisted +
  findings).

When the allowlist file is absent the gate is unconditional (every skill must
pass) — this is the end state once all migrations land and the file is deleted.

Usage::

    # Pre-commit / CI (scan a skills root against the ratchet)
    python -m omnibase_core.validators.skill_dispatch_receipt_mode \\
        --skills-root plugins/onex/skills \\
        --allowlist .onex_ratchets/skill_receipt_mode_allowlist.yaml

    # Regenerate the allowlist from the current violation set (migration aid)
    python -m omnibase_core.validators.skill_dispatch_receipt_mode \\
        --skills-root plugins/onex/skills --generate-allowlist
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import yaml  # ONEX_EXCLUDE: manual_yaml - validator reads the ratchet allowlist + skill frontmatter

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_skill_receipt_rule import EnumSkillReceiptRule
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.validation.model_skill_dispatch_receipt_finding import (
    ModelSkillDispatchReceiptFinding,
)

__all__ = [
    "Allowlist",
    "EnumSkillReceiptRule",
    "ModelSkillDispatchReceiptFinding",
    "load_allowlist",
    "main",
    "validate_skill_dir",
    "validate_skills_root",
]

# A skill directory whose name starts with "_" is shared infrastructure
# (_lib, _shared, _bin, _golden_path_validate), not a user-facing skill.
_SHARED_PREFIX = "_"

# Bare dispatch invocation: `onex run`, `onex node`, `onex run-node` (optionally
# `uv run onex ...`). `onex skill` / `onex delegate` are the accepted forms and
# deliberately excluded by requiring one of the three legacy verbs as a whole
# word immediately after `onex`.
_BARE_DISPATCH_RE = re.compile(r"\bonex\s+(?:run-node|run|node)\b")

# Prompt-instruction inconsistencies (check d).
_RAW_JSON_RES: tuple[re.Pattern[str], ...] = (
    re.compile(r"cat\s+[^\n`]*workflow_result\.json", re.IGNORECASE),
    re.compile(r"surface\s+the\s+json\s+verbatim", re.IGNORECASE),
    re.compile(r"print\s+the\s+(?:full\s+)?json\s+verbatim", re.IGNORECASE),
)

# Negation guard for check (d): a line that PROHIBITS raw-JSON surfacing
# ("no cat of workflow_result.json", "never surface the json verbatim",
# "do NOT cat ...") is the desired guidance, not a violation. Skip the match
# when a negation token precedes it on the same line.
_NEGATION_RE = re.compile(
    r"\b(?:no|not|never|don'?t|do\s+not|avoid|without|instead\s+of|n[ -]o)\b",
    re.IGNORECASE,
)

_VALID_SKILL_KINDS = frozenset({"dispatch", "methodology"})

# Executable-logic file detection (check c).
_EXECUTABLE_SUFFIXES = frozenset({".py", ".sh", ".bash", ".zsh"})
_EXECUTABLE_DIR_NAMES = frozenset({"_lib"})

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


@dataclass(frozen=True, slots=True)
class Allowlist:
    """Parsed ratchet allowlist: the set of not-yet-migrated skill names."""

    skills: frozenset[str]


def load_allowlist(path: Path) -> Allowlist | None:
    """Load the ratchet allowlist. ``None`` when the file is absent (gate is
    unconditional once the file has been deleted)."""
    if not path.exists():
        return None
    # ONEX_EXCLUDE: manual_yaml - validator reads the free-form ratchet allowlist
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    skills = raw.get("skills") or []
    if not isinstance(skills, list):
        raise ModelOnexError(
            message=(
                f"{path}: 'skills' must be a list of skill names, "
                f"got {type(skills).__name__}"
            ),
            error_code=EnumCoreErrorCode.INVALID_INPUT,
        )
    return Allowlist(skills=frozenset(str(s).strip() for s in skills if str(s).strip()))


def _parse_frontmatter(text: str) -> dict[str, object] | None:
    match = _FRONTMATTER_RE.match(text)
    if match is None:
        return None
    try:
        # ONEX_EXCLUDE: manual_yaml - validator reads free-form skill frontmatter
        parsed = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        # Malformed frontmatter cannot declare a valid skill_kind; treat it as
        # absent so check (a) fails rather than the validator crashing.
        return None
    return parsed if isinstance(parsed, dict) else None


def _markdown_files(skill_dir: Path) -> list[Path]:
    return sorted(p for p in skill_dir.rglob("*.md") if p.is_file())


def _executable_files(skill_dir: Path) -> list[Path]:
    hits: list[Path] = []
    for p in sorted(skill_dir.rglob("*")):
        if "__pycache__" in p.parts:
            continue
        if (p.is_dir() and p.name in _EXECUTABLE_DIR_NAMES) or (
            p.is_file() and p.suffix in _EXECUTABLE_SUFFIXES
        ):
            hits.append(p)
    return hits


def _skill_kind(skill_dir: Path) -> tuple[str | None, bool]:
    """Return (skill_kind value or None, frontmatter_present)."""
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        # Use the first markdown file as the frontmatter carrier if no SKILL.md.
        mds = _markdown_files(skill_dir)
        if not mds:
            return None, False
        skill_md = mds[0]
    fm = _parse_frontmatter(skill_md.read_text(encoding="utf-8"))
    if fm is None:
        return None, False
    value = fm.get("skill_kind")
    return (str(value) if value is not None else None), True


def validate_skill_dir(skill_dir: Path) -> list[ModelSkillDispatchReceiptFinding]:
    """Run all four checks against a single skill directory."""
    name = skill_dir.name
    findings: list[ModelSkillDispatchReceiptFinding] = []

    kind, fm_present = _skill_kind(skill_dir)

    # (a) explicit skill_kind
    if not fm_present or kind is None:
        findings.append(
            ModelSkillDispatchReceiptFinding(
                skill_name=name,
                path=skill_dir / "SKILL.md",
                rule=EnumSkillReceiptRule.MISSING_SKILL_KIND,
                message="frontmatter must declare 'skill_kind: dispatch | methodology'",
            )
        )
        # Without an explicit classification we cannot apply dispatch-only
        # checks; the missing-kind finding is sufficient to fail the gate.
        return findings

    if kind not in _VALID_SKILL_KINDS:
        findings.append(
            ModelSkillDispatchReceiptFinding(
                skill_name=name,
                path=skill_dir / "SKILL.md",
                rule=EnumSkillReceiptRule.INVALID_SKILL_KIND,
                message=(
                    f"skill_kind '{kind}' is invalid; must be one of "
                    f"{sorted(_VALID_SKILL_KINDS)}"
                ),
            )
        )
        return findings

    if kind == "methodology":
        # Methodology skills are exempt from dispatch-only checks (their prose
        # and any helper scripts are the deliverable).
        return findings

    # kind == "dispatch": apply checks (b), (c), (d).
    for md in _markdown_files(skill_dir):
        text = md.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), start=1):
            if _BARE_DISPATCH_RE.search(line):
                findings.append(
                    ModelSkillDispatchReceiptFinding(
                        skill_name=name,
                        path=md,
                        rule=EnumSkillReceiptRule.BARE_DISPATCH_INVOCATION,
                        message=(
                            "bare 'onex run|node|run-node' invocation; dispatch "
                            "skills must use the single 'onex skill'/'onex delegate' "
                            "receipt-mode command"
                        ),
                        line=lineno,
                    )
                )
        for lineno, line in enumerate(text.splitlines(), start=1):
            if not any(p.search(line) for p in _RAW_JSON_RES):
                continue
            # A line that prohibits raw-JSON surfacing is correct guidance.
            if _NEGATION_RE.search(line):
                continue
            findings.append(
                ModelSkillDispatchReceiptFinding(
                    skill_name=name,
                    path=md,
                    rule=EnumSkillReceiptRule.PROMPT_PRINTS_RAW_JSON,
                    message=(
                        "dispatch skill instructs raw-JSON surfacing "
                        "(cat workflow_result.json / surface JSON verbatim); "
                        "receipt mode prints exactly one typed result"
                    ),
                    line=lineno,
                )
            )

    # (c) no executable logic in a dispatch skill directory
    for exe in _executable_files(skill_dir):
        findings.append(
            ModelSkillDispatchReceiptFinding(
                skill_name=name,
                path=exe,
                rule=EnumSkillReceiptRule.EXECUTABLE_LOGIC_IN_SKILL_DIR,
                message=(
                    "dispatch skill directory must contain markdown only; "
                    "move logic behind the backing omnimarket node"
                ),
            )
        )

    return findings


def _iter_skill_dirs(skills_root: Path) -> Iterable[Path]:
    for child in sorted(skills_root.iterdir()):
        if not child.is_dir():
            continue
        if child.name.startswith(_SHARED_PREFIX):
            continue
        if child.name == "__pycache__":
            continue
        yield child


def validate_skills_root(
    skills_root: Path, *, allowlist: Allowlist
) -> list[ModelSkillDispatchReceiptFinding]:
    """Validate every skill under ``skills_root``, suppressing findings for
    allowlisted skills. Returns the unsuppressed findings."""
    findings: list[ModelSkillDispatchReceiptFinding] = []
    for skill_dir in _iter_skill_dirs(skills_root):
        if skill_dir.name in allowlist.skills:
            continue
        findings.extend(validate_skill_dir(skill_dir))
    return findings


def _skills_with_findings(skills_root: Path) -> set[str]:
    out: set[str] = set()
    for skill_dir in _iter_skill_dirs(skills_root):
        if validate_skill_dir(skill_dir):
            out.add(skill_dir.name)
    return out


def _generate_allowlist(skills_root: Path) -> str:
    names = sorted(_skills_with_findings(skills_root))
    lines = [
        "# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.",
        "# SPDX-License-Identifier: MIT",
        "#",
        "# OMN-13098 skill receipt-mode ratchet allowlist.",
        "# Skills listed here predate the receipt-mode gate and are not yet",
        "# migrated to the single 'onex skill'/'onex delegate' dispatch form.",
        "# CI fails if this list GROWS, if a listed skill is migrated (stale",
        "# entry), or if a listed skill no longer exists. Shrink to empty as",
        "# migrations land, then delete this file to make the gate unconditional.",
        "skills:",
    ]
    lines += [f"  - {n}" for n in names]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="skill-dispatch-receipt-mode",
        description=(
            "Enforce that dispatch-only shim skills are a single receipt-mode "
            "'onex skill'/'onex delegate' CLI call with no inline glue."
        ),
    )
    parser.add_argument(
        "--skills-root",
        required=True,
        help="Path to the plugins/onex/skills directory.",
    )
    parser.add_argument(
        "--allowlist",
        default=None,
        help=(
            "Path to the ratchet allowlist YAML (absent => unconditional gate). "
            "Required unless --generate-allowlist is given."
        ),
    )
    parser.add_argument(
        "--generate-allowlist",
        action="store_true",
        help="Print a ratchet allowlist of the current violation set and exit 0.",
    )
    args = parser.parse_args(argv)

    skills_root = Path(args.skills_root)
    if not skills_root.is_dir():
        sys.stderr.write(
            f"skill-dispatch-receipt-mode: {skills_root} is not a directory\n"
        )
        return 2

    if args.generate_allowlist:
        sys.stdout.write(_generate_allowlist(skills_root))
        return 0

    if args.allowlist is None:
        sys.stderr.write(
            "skill-dispatch-receipt-mode: --allowlist is required "
            "(or pass --generate-allowlist)\n"
        )
        return 2

    allowlist_path = Path(args.allowlist)
    allowlist = load_allowlist(allowlist_path)
    if allowlist is None:
        allowlist = Allowlist(skills=frozenset())

    exit_code = 0

    # Ratchet integrity: a listed skill must (1) still exist and (2) still have
    # findings. A migrated/clean listed skill is a stale entry — fail so the
    # allowlist is forced to shrink.
    present = {d.name for d in _iter_skill_dirs(skills_root)}
    violating = _skills_with_findings(skills_root)
    for listed in sorted(allowlist.skills):
        if listed not in present:
            sys.stderr.write(
                f"skill-dispatch-receipt-mode: stale allowlist entry '{listed}' "
                "(skill no longer exists). Remove it from the allowlist.\n"
            )
            exit_code = 1
        elif listed not in violating:
            sys.stderr.write(
                f"skill-dispatch-receipt-mode: stale allowlist entry '{listed}' "
                "(skill is migrated/clean). Remove it from the allowlist — it must shrink.\n"
            )
            exit_code = 1

    findings = validate_skills_root(skills_root, allowlist=allowlist)
    if findings:
        sys.stderr.write(
            "skill-dispatch-receipt-mode: FAIL — non-allowlisted dispatch-skill "
            "violations (the allowlist must not grow):\n"
        )
        for f in findings:
            sys.stderr.write(f"  {f.format()}\n")
        sys.stderr.write(
            "  Migrate to the single 'onex skill <name>'/'onex delegate' receipt-mode "
            "form, delete inline glue, and declare 'skill_kind: dispatch'.\n"
        )
        exit_code = 1

    if exit_code == 0:
        sys.stdout.write(
            "skill-dispatch-receipt-mode: OK — all dispatch skills are receipt-mode "
            "(or allowlisted), and the ratchet has no stale entries.\n"
        )
    return exit_code


if __name__ == "__main__":
    # error-ok: CLI entrypoint propagates the process exit code (pre-commit/CI gate)
    raise SystemExit(main())
