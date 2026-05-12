# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""validator_skill_backing_node -- block skill backing-node regressions.

Ticket: OMN-10052/OMN-10171. Closes OMN-9884 class of failure. SEAM-2 canonical home.

ADR: ``omnibase_core/docs/decisions/adr-2026-04-28-skill-liveness-validator-home.md``

On 2026-04-27, /onex:merge_sweep pointed at node_merge_sweep (gutted by
functional-core/imperative-shell decomposition) for hours. Cron ticked every
5 minutes against a non-existent entrypoint. Silent failure.

This validator blocks that class of regression at pre-commit (omniclaude) and
CI (omnimarket):

1. Walk every ``plugins/onex/skills/*/SKILL.md`` in the omniclaude repo root.
2. Extract the backing-node reference using the canonical body form::

       **Backing node**: `omnimarket/src/omnimarket/nodes/<node_name>/`

   and the alternate short form (no path prefix)::

       - **Backing node**: `node_<name>`

   The extractor accepts all three field-value separators seen in the corpus:
   ``**Backing node**:``, ``Backing node:``, and ``backing_node:`` (YAML
   frontmatter). The first match per file wins.

3. For each declared backing node, resolve the path relative to the omnimarket
   repo root and assert:

   a. Directory exists.
   b. ``contract.yaml`` exists at the directory root.
   c. ``handlers/`` directory exists and contains at least one ``handler_*.py``
      file with non-trivial content (more than 10 non-blank, non-comment lines
      -- guards against ``pass`` / ``NotImplementedError`` stubs).

4. Fail with a precise message naming the offending skill + specific violation.

5. Allowlist: ``plugins/onex/skills/_lib/skill_backing_node_allowlist.yaml``
   inside the omniclaude repo root. Every entry MUST carry a non-empty
   ``reason`` field. The loader raises ``ValueError`` on a missing or blank
   reason so silent drop-ins are caught at pre-commit time, not at runtime.

No warn-only mode. Per ``feedback_no_informational_gates.md``, the validator
BLOCKS unconditionally. Skills whose SKILL.md does not declare a backing node
are not checked (they may be pure-instruction skills like ``build_loop``).

Invocation surfaces:
- ``omniclaude`` pre-commit: thin shim at
  ``plugins/onex/skills/_lib/validate_skill_backing_node.py`` delegates here.
- ``omnimarket`` CI: invokes this module directly.
- Standalone / CI self-scan::

    python -m omnibase_core.validation.validator_skill_backing_node [OMNICLAUDE_ROOT]

  OMNICLAUDE_ROOT defaults to ``$OMNI_HOME/omniclaude`` when ``$OMNI_HOME``
  is set, else raises ``RuntimeError``.

Exit codes:
    0 -- all declared backing nodes are live (or omnimarket not resolvable locally)
    1 -- at least one violation found (or allowlist entry missing reason)
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import yaml

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_ALLOWLIST_PATH_REL = Path("plugins/onex/skills/_lib/skill_backing_node_allowlist.yaml")

_OMNIMARKET_NODES_REL = Path("src") / "omnimarket" / "nodes"

# Minimum non-blank, non-comment lines to consider a handler non-trivial.
_MIN_SUBSTANTIVE_LINES = 10

# Regex patterns for extracting the backing-node name from SKILL.md.
# Listed in priority order; first match per file wins.
_BACKING_NODE_PATTERNS: list[re.Pattern[str]] = [
    # Canonical body form: **Backing node**: `omnimarket/src/omnimarket/nodes/node_foo/`
    re.compile(
        r"\*\*Backing node\*\*\s*:\s*`(?:[^`]*/)?(?P<name>node_[a-z_0-9]+)/?`",
        re.IGNORECASE,
    ),
    # Short body form: - **Backing node**: `node_foo`
    re.compile(
        r"\*\*Backing node\*\*\s*:\s*`(?P<name>node_[a-z_0-9]+)`",
        re.IGNORECASE,
    ),
    # Inline heading form (compliance_sweep):
    # **Skill ID**: ... · **Backing node**: `omnimarket/...node_foo/` · ...
    re.compile(
        r"Backing\s+node\*\*\s*:\s*`(?:[^`]*/)?(?P<name>node_[a-z_0-9]+)/?`",
        re.IGNORECASE,
    ),
    # YAML frontmatter form: backing_node: "node_foo"
    re.compile(
        r"^backing_node\s*:\s*[\"']?(?P<name>node_[a-z_0-9]+)[\"']?",
        re.MULTILINE,
    ),
]


# ---------------------------------------------------------------------------
# Allowlist loader
# ---------------------------------------------------------------------------


def load_allowlist(omniclaude_root: Path) -> dict[str, str]:
    """Return mapping skill_name -> reason from the allowlist YAML.

    Raises ``ValueError`` if any entry has a blank or missing ``reason``.
    Returns an empty dict when the allowlist file does not exist.
    """
    path = omniclaude_root / _ALLOWLIST_PATH_REL
    if not path.is_file():
        return {}
    raw = (
        yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    )  # yaml-ok: allowlist is a flat config file, not a typed domain model
    entries = raw.get("allowlist") if isinstance(raw, dict) else None
    if not isinstance(entries, list):
        return {}
    out: dict[str, str] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError(  # error-ok: allowlist shape validation at config load boundary
                f"skill_backing_node allowlist entries must be mappings; got {entry!r}"
            )
        skill = entry.get("skill")
        reason = entry.get("reason")
        if not isinstance(skill, str) or not skill.strip():
            raise ValueError(  # error-ok: allowlist shape validation at config load boundary
                "skill_backing_node allowlist entry missing non-empty 'skill' field"
            )
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError(  # error-ok: allowlist shape validation at config load boundary
                f"skill_backing_node allowlist entry {skill!r}: every entry must "
                "declare a non-empty 'reason' explaining why the skill is exempt "
                "from backing-node liveness enforcement"
            )
        out[skill.strip()] = reason.strip()
    return out


# ---------------------------------------------------------------------------
# SKILL.md parser
# ---------------------------------------------------------------------------


def extract_backing_node(skill_md_path: Path) -> str | None:
    """Return the node directory name declared in the SKILL.md, or None."""
    try:
        text = skill_md_path.read_text(encoding="utf-8")
    except OSError:
        return None
    for pattern in _BACKING_NODE_PATTERNS:
        m = pattern.search(text)
        if m:
            return m.group("name")
    return None


# ---------------------------------------------------------------------------
# Node liveness checks
# ---------------------------------------------------------------------------


def _count_substantive_lines(path: Path) -> int:
    """Return the number of non-blank, non-comment lines in *path*."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return 0
    count = 0
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            count += 1
    return count


class SkillLivenessViolation:
    """A single liveness violation for a skill's backing node."""

    def __init__(self, skill: str, node_name: str, detail: str) -> None:
        self.skill = skill
        self.node_name = node_name
        self.detail = detail

    def __str__(self) -> str:
        return (
            f"VIOLATION  skill={self.skill!r}  node={self.node_name!r}\n  {self.detail}"
        )


def _resolve_omnimarket_nodes_root(omniclaude_root: Path) -> list[Path]:
    """Return candidate paths for the omnimarket nodes directory.

    Resolution order (first that is_dir() wins):
    1. ``$OMNIMARKET_ROOT`` env var -- explicit override for local dev + CI.
    2. ``$OMNI_HOME/omnimarket`` -- standard OMNI_HOME layout.
    3. ``_omnimarket`` relative to *omniclaude_root* -- CI checkout layout.
    4. Sibling repo: ``<omniclaude_root>/../omnimarket`` -- worktree sibling.
    5. Mono-repo style: ``<omniclaude_root>/omnimarket/...`` (future).
    6. Vendor dir: ``<omniclaude_root>/vendor/omnimarket/...`` (future).
    """
    bases: list[Path] = []

    omnimarket_root_env = os.environ.get("OMNIMARKET_ROOT")
    if omnimarket_root_env:
        bases.append(Path(omnimarket_root_env) / _OMNIMARKET_NODES_REL)

    omni_home = os.environ.get("OMNI_HOME")
    if omni_home:
        bases.append(Path(omni_home) / "omnimarket" / _OMNIMARKET_NODES_REL)

    bases.append(omniclaude_root / "_omnimarket" / _OMNIMARKET_NODES_REL)
    bases.append(omniclaude_root.parent / "omnimarket" / _OMNIMARKET_NODES_REL)
    bases.append(omniclaude_root / "omnimarket" / "src" / "omnimarket" / "nodes")
    bases.append(omniclaude_root / "vendor" / "omnimarket" / _OMNIMARKET_NODES_REL)

    return bases


def check_node_liveness(
    skill_name: str,
    node_name: str,
    omniclaude_root: Path,
) -> SkillLivenessViolation | None:
    """Assert that *node_name* exists and is live.

    Returns a ``SkillLivenessViolation`` describing the first problem found, or
    ``None`` when the node passes all checks.
    """
    candidates = [
        base / node_name for base in _resolve_omnimarket_nodes_root(omniclaude_root)
    ]

    node_dir: Path | None = None
    for candidate in candidates:
        if candidate.is_dir():
            node_dir = candidate
            break

    if node_dir is None:
        unique = list(dict.fromkeys(str(c) for c in candidates))
        searched = "\n    ".join(unique)
        return SkillLivenessViolation(
            skill_name,
            node_name,
            f"node directory not found.  Searched:\n    {searched}\n"
            "  Tip: set $OMNIMARKET_ROOT to the omnimarket repo root, or "
            "ensure the CI workflow checks out omnimarket into _omnimarket/",
        )

    contract = node_dir / "contract.yaml"
    if not contract.is_file():
        return SkillLivenessViolation(
            skill_name,
            node_name,
            f"contract.yaml missing at {contract}",
        )

    handlers_dir = node_dir / "handlers"
    if not handlers_dir.is_dir():
        return SkillLivenessViolation(
            skill_name,
            node_name,
            f"handlers/ directory missing at {handlers_dir}",
        )

    handler_files = sorted(handlers_dir.glob("handler_*.py"))
    if not handler_files:
        return SkillLivenessViolation(
            skill_name,
            node_name,
            f"handlers/ directory at {handlers_dir} contains no handler_*.py files",
        )

    live_handler = next(
        (
            hf
            for hf in handler_files
            if _count_substantive_lines(hf) >= _MIN_SUBSTANTIVE_LINES
        ),
        None,
    )
    if live_handler is None:
        stub_list = ", ".join(hf.name for hf in handler_files)
        return SkillLivenessViolation(
            skill_name,
            node_name,
            f"all handler files appear to be stubs (fewer than "
            f"{_MIN_SUBSTANTIVE_LINES} substantive lines each): {stub_list}",
        )

    return None


# ---------------------------------------------------------------------------
# Main scan
# ---------------------------------------------------------------------------


def _omnimarket_available(omniclaude_root: Path) -> bool:
    """Return True when at least one omnimarket nodes base directory exists."""
    return any(
        base.is_dir() for base in _resolve_omnimarket_nodes_root(omniclaude_root)
    )


def scan(omniclaude_root: Path) -> list[str]:
    """Scan *omniclaude_root* for backing-node violations.

    Returns a list of human-readable error strings. An empty list means clean.
    Raises ``ValueError`` on a malformed allowlist entry.

    When omnimarket is not resolvable locally, prints a warning and returns
    an empty list. CI enforces the gate unconditionally via _omnimarket/.
    """
    allowlist = load_allowlist(omniclaude_root)
    skills_root = omniclaude_root / "plugins" / "onex" / "skills"
    if not skills_root.is_dir():
        return [f"skills directory not found at {skills_root}"]

    if not _omnimarket_available(omniclaude_root):
        print(
            "validate-skill-backing-node: SKIPPED locally -- omnimarket not found. "
            "Set $OMNIMARKET_ROOT or $OMNI_HOME to enable local enforcement. "
            "CI checks out omnimarket and enforces this gate on every PR.",
            file=sys.stderr,
        )
        return []

    errors: list[str] = []

    for skill_md in sorted(skills_root.glob("*/SKILL.md")):
        skill_name = skill_md.parent.name

        node_name = extract_backing_node(skill_md)
        if node_name is None:
            continue

        if skill_name in allowlist:
            continue

        violation = check_node_liveness(skill_name, node_name, omniclaude_root)
        if violation is not None:
            errors.append(str(violation))

    return errors


def _count_skills_checked(omniclaude_root: Path) -> int:
    """Return number of skills that have a backing-node declaration."""
    skills_root = omniclaude_root / "plugins" / "onex" / "skills"
    if not skills_root.is_dir():
        return 0
    count = 0
    try:
        allowlist = load_allowlist(omniclaude_root)
    except ValueError:
        allowlist = {}
    for skill_md in skills_root.glob("*/SKILL.md"):
        skill_name = skill_md.parent.name
        if extract_backing_node(skill_md) is not None and skill_name not in allowlist:
            count += 1
    return count


def _resolve_omniclaude_root() -> Path:
    """Resolve the omniclaude repo root from env or raise RuntimeError."""
    omni_home = os.environ.get("OMNI_HOME")
    if omni_home:
        candidate = Path(omni_home) / "omniclaude"
        if candidate.is_dir():
            return candidate
    raise RuntimeError(  # error-ok: CLI entrypoint environment misconfiguration — stdlib is appropriate
        "Cannot resolve omniclaude repo root. "
        "Pass the path as a CLI argument or set $OMNI_HOME."
    )


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns 0 on success, 1 on violations."""
    args = argv if argv is not None else sys.argv[1:]

    if args:
        omniclaude_root = Path(args[0]).resolve()
    else:
        try:
            omniclaude_root = _resolve_omniclaude_root()
        except RuntimeError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1

    try:
        errors = scan(omniclaude_root)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if errors:
        print(
            "validate-skill-backing-node: FAILED -- backing-node liveness violations:\n",
            file=sys.stderr,
        )
        for err in errors:
            print(err, file=sys.stderr)
        print(
            "\nFIX: update the backing node so it has a live handlers/ directory, "
            "or add the skill to "
            "plugins/onex/skills/_lib/skill_backing_node_allowlist.yaml "
            "with a non-empty 'reason' field.",
            file=sys.stderr,
        )
        return 1

    if not _omnimarket_available(omniclaude_root):
        return 0

    print(
        f"validate-skill-backing-node: OK -- {_count_skills_checked(omniclaude_root)} "
        "skills with backing-node declarations are live"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
