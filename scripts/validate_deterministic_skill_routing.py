#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""AST-based CI lint gate: deterministic-skill routing enforcement (OMN-8765).

Enforces the W3 Hard Gate from OMN-8737: every Tier 1 deterministic skill
must route through ``onex run-node`` / ``onex node`` (or the equivalent Kafka
command dispatch) and surface ``SkillRoutingError`` on routing failure. Skills
must not contain inline LLM SDK usage or subprocess orchestration wrappers
that would let an agent produce prose instead of dispatching.

The predecessor in ``omniclaude`` (OMN-8749) enforces the same contract with
regex heuristics over the full markdown. This gate is stricter: it parses
each fenced ```python``` block with ``ast`` and each fenced shell block
(``bash`` / ``sh`` / ``shell`` / ``zsh``) as tokens, and applies structural
checks rather than line-count thresholds:

  1. Zero LLM SDK imports in any Python block (``anthropic``, ``openai``,
     ``google.generativeai``).
  2. At least one node-dispatch declaration (``onex run-node`` / ``onex
     run`` / ``onex node`` in a bash/sh/shell block or inline-code, OR a
     Kafka publish to an ``onex.cmd.*`` topic). CLI usage banners and
     comments are skipped.
  3. No subprocess orchestration wrappers around the dispatch
     (``subprocess.run``/``subprocess.Popen``/``os.system``) in Python blocks,
     and no shell ``python -c`` / ``bash -c`` wrapping the dispatch line.
  4. No ``client.messages.create`` / ``client.completions.create`` (Anthropic /
     OpenAI message APIs) anywhere in the Python blocks.
  5. No hidden conditional prose fallback path after a routing failure — e.g.,
     a shell conditional that responds/writes/describes when the dispatch
     exits non-zero. Detected structurally by walking the token stream after
     the dispatch site.

Per amendment A4 on OMN-8765, dispatch *presence* is asserted via structural
token-matching rather than a line-count threshold; the "exactly one" phrasing
in the original amendment is interpreted as "at least one, unambiguous"
because Kafka-publish dispatches are declared in payload schemas rather than
as imperative shell commands.

Additionally, the markdown body must still reference ``SkillRoutingError``
with the ``do not produce prose`` directive (inherited from OMN-8749) so that
the markdown contract matches the AST contract.

Exit codes:
    0  All Tier 1 deterministic skills pass
    1  One or more violations found (blocking), or invalid invocation

Linear: OMN-8765 (S18). Parent: OMN-8737.
"""

from __future__ import annotations

import argparse
import ast
import logging
import re
import shlex
import sys
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Skill classification (mirrors OMN-8749)
# ---------------------------------------------------------------------------

TIER1_DETERMINISTIC_SKILLS: frozenset[str] = frozenset(
    {
        "autopilot",
        "aislop_sweep",
        "build_loop",
        "ci_watch",
        "compliance_sweep",
        "contract_sweep",
        "dashboard_sweep",
        "data_flow_sweep",
        "golden_chain_sweep",
        "merge_sweep",
        "pipeline_fill",
        "platform_readiness",
        "redeploy",
        "release",
        "runtime_sweep",
        "session",
        "start_environment",
        "verify_plugin",
    }
)

# ---------------------------------------------------------------------------
# Banned LLM SDK imports
# ---------------------------------------------------------------------------

BANNED_LLM_MODULES: frozenset[str] = frozenset(
    {
        "anthropic",
        "openai",
        "google.generativeai",
    }
)

BANNED_LLM_ATTR_CALLS: frozenset[tuple[str, str]] = frozenset(
    {
        ("messages", "create"),
        ("completions", "create"),
        ("chat", "completions"),
    }
)

SUBPROCESS_BANNED_NAMES: frozenset[str] = frozenset(
    {"run", "Popen", "call", "check_call", "check_output"}
)

OS_BANNED_NAMES: frozenset[str] = frozenset({"system", "popen"})

# ---------------------------------------------------------------------------
# Violation codes
# ---------------------------------------------------------------------------

CHECK_MISSING_SKILL_MD = "MISSING_SKILL_MD"
CHECK_LLM_IMPORT = "LLM_SDK_IMPORT"
CHECK_LLM_API_CALL = "LLM_API_CALL"
CHECK_SUBPROCESS_ORCH = "SUBPROCESS_ORCHESTRATION"
CHECK_DISPATCH_COUNT = "DISPATCH_COUNT"
CHECK_SHELL_WRAPPER = "SHELL_WRAPPER_AROUND_DISPATCH"
CHECK_PROSE_FALLBACK = "PROSE_FALLBACK_BRANCH"
CHECK_MISSING_ROUTING_ERROR = "MISSING_SKILL_ROUTING_ERROR"
CHECK_PARSE_ERROR = "CODE_BLOCK_PARSE_ERROR"


# ---------------------------------------------------------------------------
# Code block extraction
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CodeBlock:
    """A fenced code block extracted from a SKILL.md file."""

    language: str
    start_line: int  # 1-indexed line number of the opening fence
    source: str


_FENCE_RE = re.compile(r"^([`~]{3,})\s*([A-Za-z0-9_+-]*)\s*$")


def extract_code_blocks(markdown: str) -> list[CodeBlock]:
    """Extract all fenced code blocks from a markdown document.

    Handles both backtick (```) and tilde (~~~) fences. The opening and closing
    fence must use the same character and length.
    """
    blocks: list[CodeBlock] = []
    lines = markdown.splitlines()
    i = 0
    while i < len(lines):
        match = _FENCE_RE.match(lines[i])
        if match is None:
            i += 1
            continue
        fence = match.group(1)
        language = match.group(2).lower()
        start_line = i + 1  # 1-indexed
        body: list[str] = []
        j = i + 1
        while j < len(lines):
            closing = _FENCE_RE.match(lines[j])
            if closing is not None and closing.group(1) == fence:
                break
            body.append(lines[j])
            j += 1
        blocks.append(
            CodeBlock(
                language=language,
                start_line=start_line,
                source="\n".join(body),
            )
        )
        # Skip past the closing fence (or EOF)
        i = j + 1
    return blocks


# ---------------------------------------------------------------------------
# Violations
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RoutingViolation:
    skill_name: str
    skill_path: Path
    check: str
    line_number: int  # 0 when the violation is skill-level rather than block-level
    message: str

    def format_line(self) -> str:
        loc = f"{self.skill_path}"
        if self.line_number > 0:
            loc = f"{loc}:{self.line_number}"
        return f"{loc}: [{self.check}] {self.message}"


@dataclass
class ScanResult:
    skills_scanned: int = 0
    skills_with_violations: int = 0
    total_violations: int = 0
    violations: list[RoutingViolation] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Python AST checks
# ---------------------------------------------------------------------------


def _banned_module_root(module: str) -> str | None:
    """Return the banned prefix if ``module`` matches a banned LLM SDK."""
    for banned in BANNED_LLM_MODULES:
        if module == banned or module.startswith(banned + "."):
            return banned
    return None


class PythonBlockAnalyzer(ast.NodeVisitor):
    """AST visitor that records deterministic-skill violations in a Python block."""

    def __init__(
        self,
        skill_name: str,
        skill_path: Path,
        block: CodeBlock,
    ) -> None:
        self.skill_name = skill_name
        self.skill_path = skill_path
        self.block = block
        self.violations: list[RoutingViolation] = []
        # Track aliases so ``import subprocess as sp`` and ``from subprocess
        # import run`` still trip the subprocess-orchestration check. Always
        # include the module names themselves to preserve the default binding.
        self._subprocess_aliases: set[str] = {"subprocess"}
        self._os_aliases: set[str] = {"os"}
        # Names imported directly from subprocess/os (``from subprocess import run``)
        # map local-name -> canonical (module, attr) so bare ``run(...)`` calls
        # are recognised as subprocess orchestration.
        self._direct_orch_calls: dict[str, tuple[str, str]] = {}

    def _abs_line(self, node_lineno: int) -> int:
        # +1 because the fence itself sits on block.start_line, body starts next line.
        return self.block.start_line + node_lineno

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name == "subprocess":
                self._subprocess_aliases.add(alias.asname or alias.name)
            elif alias.name == "os":
                self._os_aliases.add(alias.asname or alias.name)
            banned = _banned_module_root(alias.name)
            if banned is not None:
                self.violations.append(
                    RoutingViolation(
                        skill_name=self.skill_name,
                        skill_path=self.skill_path,
                        check=CHECK_LLM_IMPORT,
                        line_number=self._abs_line(node.lineno),
                        message=(
                            f"LLM SDK import '{alias.name}' is not allowed in a "
                            "deterministic skill shim."
                        ),
                    )
                )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module == "subprocess":
            for alias in node.names:
                if alias.name in SUBPROCESS_BANNED_NAMES:
                    self._direct_orch_calls[alias.asname or alias.name] = (
                        "subprocess",
                        alias.name,
                    )
        elif node.module == "os":
            for alias in node.names:
                if alias.name in OS_BANNED_NAMES:
                    self._direct_orch_calls[alias.asname or alias.name] = (
                        "os",
                        alias.name,
                    )
        if node.module is not None:
            banned = _banned_module_root(node.module)
            # Also catch ``from google import generativeai`` where the module
            # root is ``google`` but the name completes a banned SDK path.
            banned_alias: str | None = None
            if banned is None:
                banned_alias = next(
                    (
                        alias.name
                        for alias in node.names
                        if _banned_module_root(f"{node.module}.{alias.name}")
                        is not None
                    ),
                    None,
                )
            if banned is not None or banned_alias is not None:
                import_repr = (
                    f"from {node.module} import {banned_alias}"
                    if banned_alias is not None
                    else f"from {node.module} import ..."
                )
                self.violations.append(
                    RoutingViolation(
                        skill_name=self.skill_name,
                        skill_path=self.skill_path,
                        check=CHECK_LLM_IMPORT,
                        line_number=self._abs_line(node.lineno),
                        message=(
                            f"LLM SDK import '{import_repr}' is not "
                            "allowed in a deterministic skill shim."
                        ),
                    )
                )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        # Detect subprocess orchestration and LLM API invocations.
        func = node.func
        if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
            owner = func.value.id
            attr = func.attr
            in_subprocess = (
                owner in self._subprocess_aliases and attr in SUBPROCESS_BANNED_NAMES
            )
            in_os = owner in self._os_aliases and attr in OS_BANNED_NAMES
            if in_subprocess or in_os:
                canonical_module = "subprocess" if in_subprocess else "os"
                self.violations.append(
                    RoutingViolation(
                        skill_name=self.skill_name,
                        skill_path=self.skill_path,
                        check=CHECK_SUBPROCESS_ORCH,
                        line_number=self._abs_line(node.lineno),
                        message=(
                            f"Subprocess orchestration call '{canonical_module}.{attr}(...)' "
                            "is not allowed around the dispatch."
                        ),
                    )
                )
        elif isinstance(func, ast.Name) and func.id in self._direct_orch_calls:
            canonical_module, canonical_attr = self._direct_orch_calls[func.id]
            self.violations.append(
                RoutingViolation(
                    skill_name=self.skill_name,
                    skill_path=self.skill_path,
                    check=CHECK_SUBPROCESS_ORCH,
                    line_number=self._abs_line(node.lineno),
                    message=(
                        f"Subprocess orchestration call '{canonical_module}.{canonical_attr}(...)' "
                        "is not allowed around the dispatch."
                    ),
                )
            )
        # Detect chained attribute calls like client.messages.create(...).
        if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Attribute):
            inner = func.value
            pair = (inner.attr, func.attr)
            if pair in BANNED_LLM_ATTR_CALLS:
                self.violations.append(
                    RoutingViolation(
                        skill_name=self.skill_name,
                        skill_path=self.skill_path,
                        check=CHECK_LLM_API_CALL,
                        line_number=self._abs_line(node.lineno),
                        message=(
                            f"Banned LLM API call '...{inner.attr}.{func.attr}(...)' "
                            "found in deterministic skill shim."
                        ),
                    )
                )
        self.generic_visit(node)


def check_python_block(
    skill_name: str,
    skill_path: Path,
    block: CodeBlock,
) -> list[RoutingViolation]:
    try:
        tree = ast.parse(block.source)
    except SyntaxError as exc:
        # Many skills embed pseudocode; log and skip without emitting a
        # blocking violation so ``main()`` does not fail on narrative blocks.
        logger.info(
            "Skipping unparseable python block in %s (line %s): %s",
            skill_path,
            exc.lineno,
            exc.msg,
        )
        return []
    analyzer = PythonBlockAnalyzer(skill_name, skill_path, block)
    analyzer.visit(tree)
    return analyzer.violations


# ---------------------------------------------------------------------------
# Shell block checks
# ---------------------------------------------------------------------------

SHELL_LANGUAGES: frozenset[str] = frozenset({"bash", "sh", "shell", "zsh"})

_ONEX_CMD_TOPIC_RE = re.compile(r"onex\.cmd\.[A-Za-z0-9_\-]+(?:\.[A-Za-z0-9_\-]+)+")
_PROSE_FALLBACK_VERBS: frozenset[str] = frozenset(
    {"echo", "printf", "cat", "write", "describe", "respond"}
)


@dataclass
class ShellLine:
    abs_line: int
    raw: str
    tokens: tuple[str, ...]


def _tokenize_shell(block: CodeBlock) -> list[ShellLine]:
    """Tokenize shell lines with best-effort shlex parsing.

    Logical lines continued with a trailing ``\\`` are joined before
    tokenization so multi-line ``onex run-node ... \\`` invocations are
    counted as a single dispatch. Lines that fail shlex (unbalanced quotes,
    heredoc markers, etc.) are kept as single raw tokens so downstream
    matchers can still run regex checks.
    """
    result: list[ShellLine] = []
    buffer: list[str] = []
    buffer_start: int | None = None
    for rel_line, raw in enumerate(block.source.splitlines(), start=1):
        if raw.rstrip().endswith("\\"):
            if buffer_start is None:
                buffer_start = rel_line
            buffer.append(raw.rstrip()[:-1])
            continue
        if buffer:
            buffer.append(raw)
            logical = " ".join(segment.strip() for segment in buffer).strip()
            start_rel = buffer_start if buffer_start is not None else rel_line
            buffer = []
            buffer_start = None
        else:
            logical = raw.strip()
            start_rel = rel_line

        if not logical or logical.startswith("#"):
            continue
        try:
            tokens = tuple(shlex.split(logical, comments=True, posix=True))
        except ValueError:
            tokens = (logical,)
        result.append(
            ShellLine(
                abs_line=block.start_line + start_rel,
                raw=logical,
                tokens=tokens,
            )
        )
    return result


def _is_cli_banner_line(raw: str) -> bool:
    """Skip usage banners / documentation examples that mention ``onex run``.

    Banner examples we want to allow — they are not dispatch calls:
      - ``Usage: onex run-node <node>``
      - ``Run via: onex run-node session_orchestrator``
      - ``# Example: onex node merge_sweep``
    The heuristic: if the line begins with a non-command prose token (``usage``,
    ``example``, ``run via``, ``see``, etc.) *before* the onex invocation, it is
    documentation, not executable dispatch. A command line dispatching ``onex
    run-node`` starts with ``onex`` (or with an env-prefix like ``ENV=...``).
    """
    lowered = raw.lower().lstrip()
    for banner in ("usage:", "example:", "example:", "run via:", "see ", "see:"):
        if lowered.startswith(banner):
            return True
    return False


def _line_is_dispatch(tokens: tuple[str, ...], raw: str) -> bool:
    """Return True if the tokenized shell line is a node-dispatch invocation.

    Three accepted forms:
      - ``onex run-node <node>`` / ``onex run <node>`` / ``onex node <node>``
      - ``rpk topic produce onex.cmd.<service>.<...>`` (Kafka publish wrapper)
      - any other top-level command whose args include an ``onex.cmd.*`` topic
        (generalised publish, covering ``kcat``/``kafka-console-producer``/…)
    """
    if not tokens:
        return False
    if _is_cli_banner_line(raw):
        return False

    # Strip env-var assignments (e.g., ``FOO=bar onex run-node x``).
    idx = 0
    while idx < len(tokens) and "=" in tokens[idx] and not tokens[idx].startswith("-"):
        head = tokens[idx].split("=", 1)[0]
        if head and head.replace("_", "").isalnum() and head[0].isalpha():
            idx += 1
            continue
        break
    head_tokens = tokens[idx:]

    if not head_tokens:
        return False

    # Accept both ``onex run-node X`` and ``uv run onex run-node X``.
    onex_tokens = head_tokens
    if len(head_tokens) >= 2 and head_tokens[0] == "uv" and head_tokens[1] == "run":
        onex_tokens = head_tokens[2:]
    if onex_tokens and onex_tokens[0] == "onex" and len(onex_tokens) >= 3:
        subcmd = onex_tokens[1]
        if subcmd in {"run", "run-node", "node"}:
            return True

    # Kafka publish with onex.cmd.* topic anywhere in the command.
    for tok in head_tokens:
        if _ONEX_CMD_TOPIC_RE.search(tok):
            return True

    return False


def _is_wrapped_dispatch(raw: str) -> bool:
    """Detect subprocess wrappers around ``onex run-node`` dispatches.

    Examples that should trip this:
      - ``python -c "import subprocess; subprocess.run(['onex', 'run-node', ...])"``
      - ``bash -c 'onex run-node ...'``
    We detect the wrapper pattern when one of the "-c" wrappers contains the
    onex command string literally.
    """
    if "onex run" not in raw and "onex node" not in raw:
        return False
    wrapper_prefixes = (
        "python -c",
        "python3 -c",
        "bash -c",
        "sh -c",
        "zsh -c",
    )
    lowered = raw.lower()
    return any(prefix in lowered for prefix in wrapper_prefixes)


def _is_prose_fallback(line: ShellLine) -> bool:
    """Detect a prose-writing fallback line inside an ``if ... fi`` block.

    Trips on:
      - ``echo "...fallback prose..."``
      - ``printf "..."``
      - ``cat <<EOF ... EOF``
    We require a prose verb at the head of the command (after env assignments),
    and the raw line must contain a word hinting at fallback / degrade / prose.
    """
    head = line.tokens[0] if line.tokens else ""
    if head not in _PROSE_FALLBACK_VERBS:
        return False
    hint_re = re.compile(
        r"(?:fallback|degrade|unavailable|if\s+.*?(?:fails?|unavailable)|"
        r"claude|prose|advisory)",
        re.IGNORECASE,
    )
    return hint_re.search(line.raw) is not None


def check_shell_block(
    skill_name: str,
    skill_path: Path,
    block: CodeBlock,
) -> tuple[int, list[RoutingViolation]]:
    """Return (dispatch_count, violations) for a shell block.

    ``dispatch_count`` is summed across all shell blocks by the skill-level
    aggregator before the ``exactly one dispatch`` rule is enforced.
    """
    violations: list[RoutingViolation] = []
    dispatch_count = 0
    lines = _tokenize_shell(block)

    # Track whether we are inside a failure branch (``if ... fi`` block after a
    # dispatch line) so we can flag prose fallback writes.
    in_failure_branch = False
    branch_depth = 0
    saw_dispatch_before_branch = False

    for line in lines:
        raw = line.raw

        # Flag shell wrappers around the dispatch.
        if _is_wrapped_dispatch(raw):
            violations.append(
                RoutingViolation(
                    skill_name=skill_name,
                    skill_path=skill_path,
                    check=CHECK_SHELL_WRAPPER,
                    line_number=line.abs_line,
                    message=(
                        "Dispatch must be invoked directly; subprocess wrappers "
                        "(python -c, bash -c, ...) around `onex run-node` are "
                        "forbidden."
                    ),
                )
            )

        if _line_is_dispatch(line.tokens, raw):
            dispatch_count += 1
            saw_dispatch_before_branch = True
            continue

        # Track failure-branch depth.
        if line.tokens and line.tokens[0] == "if":
            branch_depth += 1
            if saw_dispatch_before_branch and _branch_tests_failure(raw):
                in_failure_branch = True
            continue
        if line.tokens and line.tokens[0] == "fi":
            if branch_depth > 0:
                branch_depth -= 1
            if branch_depth == 0:
                in_failure_branch = False
            continue

        if in_failure_branch and _is_prose_fallback(line):
            violations.append(
                RoutingViolation(
                    skill_name=skill_name,
                    skill_path=skill_path,
                    check=CHECK_PROSE_FALLBACK,
                    line_number=line.abs_line,
                    message=(
                        "Conditional prose fallback after routing failure is "
                        "forbidden; surface SkillRoutingError instead."
                    ),
                )
            )

    return dispatch_count, violations


def _branch_tests_failure(raw: str) -> bool:
    """Heuristic: does an ``if`` line test for a non-zero exit (routing failure)?"""
    failure_patterns = (
        "$? -ne 0",
        "$? != 0",
        '"$?" -ne 0',
        '"$?" != 0',
        "! onex ",
        "|| ",
    )
    return any(pattern in raw for pattern in failure_patterns)


# ---------------------------------------------------------------------------
# Document-scope dispatch scanner
# ---------------------------------------------------------------------------

# Inline-code dispatch: `onex run-node X` or `onex node X` or
# `uv run onex node X` — captured from a markdown backtick span. The target
# must be a real node identifier (alnum / underscore / dot / hyphen), not a
# placeholder like ``<node_name>`` which would let the boilerplate routing
# sentence satisfy the contract without naming any node.
_INLINE_DISPATCH_RE = re.compile(
    r"`(?:uv\s+run\s+)?onex\s+(?:run-node|node|run)\s+[A-Za-z0-9_][A-Za-z0-9_.\-]*`"
)

# Publish declaration: "Publish to `onex.cmd.foo.bar.v1`" or
# "Dispatch: Kafka publish to `onex.cmd.foo.bar.v1`". We match the verb
# (publish / dispatch / emit / send) followed by an onex.cmd.* topic within
# the same line, tolerating backticks and angle brackets around the topic.
_PUBLISH_DECLARATION_RE = re.compile(
    r"(?:publish(?:es|ed)?|dispatch(?:es|ed)?|emit(?:s|ted)?|sends?)\b"
    r"[^\n`]{0,80}"
    r"`?(onex\.cmd\.[A-Za-z0-9_\-]+(?:\.[A-Za-z0-9_\-]+)+)`?",
    re.IGNORECASE,
)


def _count_document_dispatches(content: str) -> int:
    """Count dispatch declarations expressed outside of shell code blocks.

    Returns the count of inline-code dispatches (``\\`onex run-node X\\```)
    plus prose publish declarations (``Publish to \\`onex.cmd.*\\```).
    Both forms satisfy the routing contract when paired with the
    SkillRoutingError directive.
    """
    inline = len(_INLINE_DISPATCH_RE.findall(content))
    prose = len(_PUBLISH_DECLARATION_RE.findall(content))
    return inline + prose


# ---------------------------------------------------------------------------
# Skill-level scan
# ---------------------------------------------------------------------------

_ROUTING_ERROR_RE = re.compile(r"SkillRoutingError")
_NO_PROSE_RE = re.compile(r"do not produce prose", re.IGNORECASE)


def scan_skill(skill_path: Path) -> list[RoutingViolation]:
    skill_name = skill_path.parent.name
    content = skill_path.read_text(encoding="utf-8")
    violations: list[RoutingViolation] = []

    blocks = extract_code_blocks(content)

    # Python-block checks
    for block in blocks:
        if block.language == "python":
            violations.extend(check_python_block(skill_name, skill_path, block))

    # Shell-block checks (flag prose fallbacks + subprocess wrappers). The
    # dispatch-presence check runs at whole-document scope below because valid
    # dispatch declarations also appear in inline code and prose bullet lists
    # for Kafka-publish skills.
    total_shell_dispatches = 0
    for block in blocks:
        if block.language in SHELL_LANGUAGES:
            count, block_violations = check_shell_block(skill_name, skill_path, block)
            total_shell_dispatches += count
            violations.extend(block_violations)

    # Whole-document dispatch evidence: a code-fenced command, an inline-code
    # dispatch reference, or a prose "Publish to onex.cmd.*" declaration.
    document_dispatches = total_shell_dispatches + _count_document_dispatches(content)
    if document_dispatches == 0:
        violations.append(
            RoutingViolation(
                skill_name=skill_name,
                skill_path=skill_path,
                check=CHECK_DISPATCH_COUNT,
                line_number=0,
                message=(
                    "Deterministic skill must declare at least one node "
                    "dispatch (`onex run-node` / `onex node` in a shell block "
                    "or inline code, OR a Kafka publish to an `onex.cmd.*` "
                    "topic). None found."
                ),
            )
        )

    # Markdown-level SkillRoutingError contract (mirrors OMN-8749)
    if _ROUTING_ERROR_RE.search(content) is None:
        violations.append(
            RoutingViolation(
                skill_name=skill_name,
                skill_path=skill_path,
                check=CHECK_MISSING_ROUTING_ERROR,
                line_number=0,
                message=(
                    "SKILL.md must reference `SkillRoutingError` and instruct "
                    "agents to surface it directly (`do not produce prose`)."
                ),
            )
        )
    elif _NO_PROSE_RE.search(content) is None:
        violations.append(
            RoutingViolation(
                skill_name=skill_name,
                skill_path=skill_path,
                check=CHECK_MISSING_ROUTING_ERROR,
                line_number=0,
                message=(
                    "SKILL.md references `SkillRoutingError` but is missing the "
                    "`do not produce prose` directive."
                ),
            )
        )

    return violations


def scan_skills_root(skills_root: Path) -> ScanResult:
    result = ScanResult()
    for skill_name in sorted(TIER1_DETERMINISTIC_SKILLS):
        skill_file = skills_root / skill_name / "SKILL.md"
        result.skills_scanned += 1
        if not skill_file.exists():
            violation = RoutingViolation(
                skill_name=skill_name,
                skill_path=skill_file,
                check=CHECK_MISSING_SKILL_MD,
                line_number=0,
                message=(
                    f"SKILL.md not found for Tier 1 deterministic skill '{skill_name}'."
                ),
            )
            result.violations.append(violation)
            result.skills_with_violations += 1
            result.total_violations += 1
            continue
        skill_violations = scan_skill(skill_file)
        if skill_violations:
            result.skills_with_violations += 1
            result.total_violations += len(skill_violations)
            result.violations.extend(skill_violations)
    return result


def scan_single_skill(skills_root: Path, skill_name: str) -> ScanResult:
    result = ScanResult(skills_scanned=1)
    skill_file = skills_root / skill_name / "SKILL.md"
    if not skill_file.exists():
        violation = RoutingViolation(
            skill_name=skill_name,
            skill_path=skill_file,
            check=CHECK_MISSING_SKILL_MD,
            line_number=0,
            message=f"SKILL.md not found for skill '{skill_name}'.",
        )
        result.violations.append(violation)
        result.skills_with_violations = 1
        result.total_violations = 1
        return result
    violations = scan_skill(skill_file)
    if violations:
        result.skills_with_violations = 1
        result.total_violations = len(violations)
        result.violations.extend(violations)
    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _print_result(result: ScanResult, *, report_mode: bool) -> None:
    if not result.violations:
        print(
            f"validate_deterministic_skill_routing: OK — "
            f"{result.skills_scanned} Tier 1 skill(s) scanned, 0 violations."
        )
        return

    label = "Report" if report_mode else "FAILED"
    print(
        f"\nvalidate_deterministic_skill_routing: {label} — "
        f"{result.total_violations} violation(s) in "
        f"{result.skills_with_violations} skill(s)\n"
    )
    for violation in result.violations:
        print(f"  {violation.format_line()}")

    if not report_mode:
        print(
            "\nEach Tier 1 deterministic skill must:\n"
            "  1. Import zero LLM SDKs (anthropic, openai, google.generativeai)\n"
            "  2. Declare at least one node dispatch (`onex run-node` / `onex node`\n"
            "     in a shell block or inline code, OR a Kafka publish to an\n"
            "     `onex.cmd.*` topic)\n"
            "  3. Not wrap dispatch in subprocess.run / bash -c / python -c\n"
            "  4. Not invoke LLM completion APIs (client.messages.create, ...)\n"
            "  5. Not contain conditional prose fallback branches\n"
            "  6. Reference `SkillRoutingError` with `do not produce prose`\n"
        )


def _default_skills_root() -> Path:
    """Resolve the default skills root by walking up to find an omniclaude sibling.

    Search order (first existing wins):
      1. ``$DETERMINISTIC_SKILL_ROOT`` env var
      2. ``plugins/onex/skills`` relative to cwd
      3. ``<repo_root>/../omniclaude/plugins/onex/skills``
      4. ``$OMNI_HOME/omniclaude/plugins/onex/skills``
    """
    import os

    env = os.environ.get("DETERMINISTIC_SKILL_ROOT")
    if env:
        return Path(env)
    candidates: list[Path] = [Path.cwd() / "plugins" / "onex" / "skills"]
    script_path = Path(__file__).resolve()
    # scripts/ -> repo root -> parent
    candidates.append(
        script_path.parent.parent.parent / "omniclaude" / "plugins" / "onex" / "skills"
    )
    omni_home = os.environ.get("OMNI_HOME")
    if omni_home:
        candidates.append(
            Path(omni_home) / "omniclaude" / "plugins" / "onex" / "skills"
        )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "AST-based CI lint gate enforcing SkillRoutingError routing "
            "across all Tier 1 deterministic skills (OMN-8765)."
        ),
    )
    parser.add_argument(
        "--skills-root",
        type=Path,
        default=None,
        help=(
            "Path to the deterministic skills directory "
            "(default: auto-discovered from omniclaude sibling or "
            "$DETERMINISTIC_SKILL_ROOT)."
        ),
    )
    parser.add_argument(
        "--skill",
        metavar="SKILL_NAME",
        help="Scan only a single named skill (useful for local iteration).",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Print violations but exit 0 (non-blocking mode for rollout).",
    )
    args = parser.parse_args(argv)

    skills_root: Path = args.skills_root or _default_skills_root()
    if not skills_root.exists():
        print(
            f"ERROR: deterministic skills root not found: {skills_root}\n"
            "       Pass --skills-root <path> or set $DETERMINISTIC_SKILL_ROOT.",
            file=sys.stderr,
        )
        return 1

    if args.skill is not None:
        result = scan_single_skill(skills_root, args.skill)
    else:
        result = scan_skills_root(skills_root)

    _print_result(result, report_mode=args.report)

    if args.report:
        return 0
    return 1 if result.total_violations > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
