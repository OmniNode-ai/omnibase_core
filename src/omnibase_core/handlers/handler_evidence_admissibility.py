# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The single admissibility predicate for DoD evidence (OMN-15309).

Operator ruling 2026-07-29 (recorded in ``docs/tracking/ROLLING_WORK_LEDGER.md``,
"OPERATOR RULINGS x8", item 3): adopt the **OMN-14505 deploy-gate falsifiability
predicate** as THE admissibility rule for evidence everywhere, CI-enforced. This
module is that adoption. It is deliberately the *only* place in this repo where
"is this evidence admissible?" is decided.

Three properties, all required. Evidence is admissible only if it is:

1. **EXECUTED** — a command actually runs. Not a declaration, not an attestation,
   not a keyword appearing as quoted text. Decided by shell *command position*
   (``shlex``), never by substring match: ``echo 'docker exec x'`` lexes to
   ``['echo', 'docker exec x']``, so ``docker`` is an argument and never counts.
2. **FALSIFIABLE** — it can go RED. A probe whose exit status is fixed by the
   text the author typed (``echo``, ``true``, ``:``, ``printf``) proves nothing.
3. **OUTSIDE ITS OWN DIFF** — it observes something the evidence author does not
   write in the same change. Reading back the receipt/contract tree authored by
   the same OCC companion PR, or grepping only files the PR itself modifies, is
   circular: the check passes because the author wrote the text it greps.

Provenance — the cited single source
------------------------------------
The algorithm (shell lexing, command-position resolution, wrapper unwrapping,
``$(...)``/``bash -c`` recursion, the self-referential DENY list) is adopted from
``omniclaude/.github/actions/deploy-gate/validate_pr_deploy_required.py``
(``classify_check_value``), shipped under OMN-14505. That file remains the cited
source of the predicate; this module is its adoption in onex_change_control, and
``tests/test_evidence_admissibility.py`` plus the ``predicate-parity`` step in
``.github/workflows/ci.yml`` prove the two agree by **execution** against a
shared case corpus, so they cannot silently drift into a second definition.

Why the probe vocabulary is a parameter, not a constant
-------------------------------------------------------
The two consumers differ in exactly one respect, and it is a real difference, not
a second definition:

* ``deploy-gate`` **never executes** the check_value — it only reads the contract
  text — so "EXECUTED" can only be inferred from the *name* of the command. It
  therefore admits only :data:`LIVE_PROBE_COMMANDS`, whose exit status can only
  come from a deployed system.
* ``contract_compliance_check.py`` **does execute** the check_value in CI, so a
  hermetic command that runs against the product checkout (``uv run pytest``,
  ``python -c 'import ...'``, ``grep`` over a file the PR does not touch) is
  genuinely executed and genuinely falsifiable. It admits
  :data:`EXECUTED_HERMETIC_COMMANDS` in addition.

Both consumers apply the identical DENY half and the identical command-position
analysis. Only the ALLOW vocabulary is parameterised.

Fails CLOSED: empty, non-string, unparseable (unbalanced quotes), or
not-provably-executed input is INADMISSIBLE.
"""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass
from pathlib import Path
from re import Pattern
from typing import TYPE_CHECKING

from omnibase_core.enums.ticket.enum_admissibility_rule import EnumAdmissibilityRule

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable

__all__ = [
    "EXECUTED_CHECK_TYPES",
    "EXECUTED_HERMETIC_COMMANDS",
    "EXISTENCE_CHECK_TYPES",
    "LIVE_PROBE_COMMANDS",
    "SELF_REFERENTIAL_PATTERNS",
    "TEXT_READING_COMMANDS",
    "AdmissibilityVerdict",
    "EnumAdmissibilityRule",
    "admissible_evidence_guidance",
    "classify_evidence",
    "classify_evidence_item",
    "commands_in",
    "is_self_referential",
]


@dataclass(frozen=True)
class AdmissibilityVerdict:
    """Why one evidence check_value was admitted or refused."""

    admissible: bool
    rule: EnumAdmissibilityRule
    reason: str


# ---------------------------------------------------------------------------
# ALLOW vocabularies
# ---------------------------------------------------------------------------

#: Commands that probe a LIVE runtime surface. Their exit status depends on the
#: state of a deployed system, not on the content of any file in the PR.
#: Verbatim parity with ``validate_pr_deploy_required.LIVE_PROBE_COMMANDS``.
LIVE_PROBE_COMMANDS: frozenset[str] = frozenset(
    {
        # containers / orchestrators
        "docker",
        "docker-compose",
        "podman",
        "nerdctl",
        "kubectl",
        # message broker
        "rpk",
        "kcat",
        "kafkacat",
        # datastores
        "psql",
        "mysql",
        "redis-cli",
        "valkey-cli",
        "mongosh",
        # HTTP surfaces
        "curl",
        "wget",
        "httpie",
        # remote hosts
        "ssh",
        # ONEX node dispatch against the live runtime
        "onex",
        # GitHub REST content reads at a pinned ref. Compound token, NOT bare
        # `gh`: `gh pr view/list/status` only report PR/issue metadata and are
        # trivially true via almost every ticket's own generated self-bind
        # check, so accepting bare `gh` would reclassify hundreds of
        # non-substantive checks as falsifiable.
        "gh-api",
    }
)

#: Commands that genuinely EXECUTE against the product checkout inside CI. These
#: are admissible only for consumers that actually run the check_value (the
#: contract-compliance runner), never for a text-only gate like deploy-gate.
#:
#: `test`/`[`/`ls`/`stat` are deliberately ABSENT: a bare existence probe on a
#: path the PR itself adds cannot go RED once the PR is applied — it is the
#: `test -f src/path/touched_by_this_pr.py` shape this ticket removes from the
#: runner's own guidance.
EXECUTED_HERMETIC_COMMANDS: frozenset[str] = frozenset(
    {
        "uv",
        "uvx",
        "pytest",
        "python",
        "python3",
        "mypy",
        "ruff",
        "pre-commit",
        "grep",
        "rg",
        "jq",
        "yq",
        "git",
        "make",
        "npm",
        "npx",
        "node",
        "tsc",
        "diff",
        "cmp",
        "sha256sum",
        "shasum",
    }
)

#: Commands whose exit status is decided entirely by the text the author typed.
#: Present so a `false`/`echo` leading segment is reported as NOT_FALSIFIABLE
#: (a precise diagnosis) instead of the vaguer NOT_EXECUTED.
NON_FALSIFIABLE_COMMANDS: frozenset[str] = frozenset(
    {"echo", "printf", "true", "false", ":", "test", "[", "ls", "stat", "cat"}
)

#: Commands that READ TEXT rather than EXECUTE BEHAVIOUR.
#:
#: This distinction is what keeps the OUTSIDE-ITS-OWN-DIFF rule from refusing
#: the single most legitimate evidence shape there is. Reading only text you
#: just wrote is circular — the grep passes because you typed the string.
#: *Executing* code you just wrote is not circular — the test runs the
#: behaviour and goes RED when the behaviour is wrong, which is the entire
#: point of adding a test alongside a fix.
#:
#: So the own-diff rule applies ONLY when every probe in the check is a text
#: reader. ``uv run pytest tests/test_new_thing.py`` where that test is added by
#: the same PR stays ADMISSIBLE; ``grep -q 'symbol' src/new_thing.py`` where
#: that source is added by the same PR does not.
TEXT_READING_COMMANDS: frozenset[str] = frozenset(
    {
        "grep",
        "rg",
        "cat",
        "head",
        "tail",
        "diff",
        "cmp",
        "jq",
        "yq",
        "sha256sum",
        "shasum",
        "test",
        "ls",
        "stat",
        "wc",
    }
)

#: ``check_type`` values whose ``check_value`` is a bare path/glob asserting that
#: something EXISTS, not a command. An existence assertion cannot go RED once the
#: PR that adds the path is applied, which is the ``test -f`` shape OMN-14505
#: names as one of its five vacuous classes. Refused as NOT_FALSIFIABLE with a
#: diagnosis that fits the check_type, rather than a confusing "no command in
#: command position" message about a value that was never a command.
EXISTENCE_CHECK_TYPES: frozenset[str] = frozenset({"file_exists", "test_exists"})

#: ``check_type`` values the runner EXECUTES as behaviour, whose ``check_value``
#: is not shell text. ``test_passes`` runs the named test; ``endpoint`` probes a
#: live URL. Both are executed and falsifiable by construction.
EXECUTED_CHECK_TYPES: frozenset[str] = frozenset({"test_passes", "endpoint"})


# ---------------------------------------------------------------------------
# DENY half — outside-its-own-diff
# ---------------------------------------------------------------------------

#: Artifact trees the evidence author writes in the SAME OCC companion PR. A
#: check_value that reads these back is circular: its verdict is decided by text
#: the author typed. Verbatim parity with
#: ``validate_pr_deploy_required.SELF_REFERENTIAL_PATTERNS``.
SELF_REFERENTIAL_PATTERNS: tuple[Pattern[str], ...] = (
    # the DoD receipt tree — drift/dod_receipts/OMN-X/<item>/command.yaml
    re.compile(r"dod_receipts", re.IGNORECASE),
    # $CONTRACT_REPO_DIR / ${CONTRACT_REPO_DIR} — the OCC checkout root
    re.compile(r"\$\{?CONTRACT_REPO_DIR\b", re.IGNORECASE),
    # the ticket's own contract file
    re.compile(r"contracts/OMN-\d+\.ya?ml", re.IGNORECASE),
)


def is_self_referential(value: str) -> Pattern[str] | None:
    """Return the matching DENY pattern, or ``None`` when the value is clean."""
    for pattern in SELF_REFERENTIAL_PATTERNS:
        if pattern.search(value):
            return pattern
    return None


# ---------------------------------------------------------------------------
# Command-position analysis (adopted verbatim from OMN-14505)
# ---------------------------------------------------------------------------

_CMD_SUBST_RE = re.compile(r"\$\(([^()]*(?:\([^()]*\)[^()]*)*)\)")
_BACKTICK_RE = re.compile(r"`([^`]*)`")
_ASSIGNMENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")

#: Transparent wrappers: they execute their argument, so the real command is the
#: next token. ``env -u PYTHONPATH docker exec ...`` must still resolve to
#: ``docker``.
WRAPPER_COMMANDS: frozenset[str] = frozenset(
    {
        "env",
        "sudo",
        "time",
        "timeout",
        "nohup",
        "stdbuf",
        "nice",
        "command",
        "exec",
        "xargs",
        "then",
        "do",
    }
)

#: Shells whose ``-c <string>`` argument is itself a script to parse.
SHELL_COMMANDS: frozenset[str] = frozenset({"bash", "sh", "zsh", "dash"})

#: Shell operators that terminate one command and begin the next. Split on these
#: only AFTER lexing — a ``;`` inside a quoted ``python -c`` string is data.
_OPERATOR_TOKENS: frozenset[str] = frozenset(
    {"&&", "||", "|", ";", "&", "(", ")", "\n"}
)

#: Wrapper flags that consume the following token as their value.
_WRAPPER_FLAGS_WITH_ARG: frozenset[str] = frozenset(
    {"-u", "--unset", "-C", "--chdir", "-S", "--split-string"}
)

#: ``timeout 30`` / ``timeout 1m`` — a bare duration argument to a wrapper.
_DURATION_RE = re.compile(r"^\d+(\.\d+)?[smhd]?$")

#: Recursion bound for $(...) / backtick / `bash -c` descent. Depth-bounded so
#: pathological nesting cannot spin.
_MAX_SUBSTITUTION_DEPTH = 4


def _lex(script: str) -> list[str]:
    """Lex a shell script into tokens, keeping operators as their own tokens.

    ``punctuation_chars=True`` groups ``&&``/``||`` as single tokens AND lexes
    *after* quote handling, so a ``;`` inside ``python -c "a; b"`` stays inside
    the quoted token instead of being mistaken for a command separator.

    Quote-stripping is what makes the whole rule work: ``echo 'docker exec x'``
    lexes to ``['echo', 'docker exec x']``, so the probe name inside the quotes
    is a single *argument* token and can never reach command position.

    An unparseable script (unbalanced quotes) fails CLOSED — no tokens.
    """
    lexer = shlex.shlex(script, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    try:
        return list(lexer)
    except ValueError:
        return []


def _command_of(tokens: list[str]) -> tuple[str | None, list[str]]:
    """Return ``(command, remaining_args)`` for one pipeline segment.

    Skips leading ``!`` negation, ``VAR=value`` assignments, and transparent
    wrappers. ``command -v``/``-V`` is a PATH lookup, not execution, so it
    short-circuits to "no command" rather than unwrapping to the named binary.
    """
    idx = 0
    in_wrapper = False
    while idx < len(tokens):
        word = tokens[idx]
        if word == "!" or _ASSIGNMENT_RE.match(word):
            idx += 1
            continue
        if Path(word).name.lower() in WRAPPER_COMMANDS:
            if (
                Path(word).name.lower() == "command"
                and idx + 1 < len(tokens)
                and tokens[idx + 1] in ("-v", "-V")
            ):
                return None, []
            in_wrapper = True
            idx += 1
            continue
        if in_wrapper:
            if word in _WRAPPER_FLAGS_WITH_ARG:
                idx += 2
                continue
            if word.startswith("-") or _DURATION_RE.match(word):
                idx += 1
                continue
        break
    if idx >= len(tokens):
        return None, []
    return Path(tokens[idx]).name.lower(), tokens[idx + 1 :]


def _pipeline_segments(tokens: list[str]) -> list[list[str]]:
    """Split a LEXED token stream into pipeline segments on operator tokens.

    Splitting the LEXED stream (never the raw text) is what keeps a ``;`` inside
    a quoted ``python -c`` string from being read as a command separator.
    """
    segment: list[str] = []
    segments: list[list[str]] = []
    for token in tokens:
        if token in _OPERATOR_TOKENS:
            segments.append(segment)
            segment = []
        else:
            segment.append(token)
    segments.append(segment)
    return segments


def commands_in(script: str, depth: int = 0) -> set[str]:
    """Return the commands appearing in COMMAND POSITION in a shell script.

    Recurses into ``$(...)``/backtick substitutions and ``bash -c '<script>'``,
    because a probe genuinely executes in all three positions. Depth-bounded so
    pathological nesting cannot spin.
    """
    if depth > _MAX_SUBSTITUTION_DEPTH or not script.strip():
        return set()

    found: set[str] = set()

    for match in _CMD_SUBST_RE.finditer(script):
        found |= commands_in(match.group(1), depth + 1)
    for match in _BACKTICK_RE.finditer(script):
        found |= commands_in(match.group(1), depth + 1)

    # Replace substitutions with a space so their inner text is not re-read as a
    # top-level argument, and surrounding quotes stay balanced.
    stripped = _BACKTICK_RE.sub(" ", _CMD_SUBST_RE.sub(" ", script))

    for tokens in _pipeline_segments(_lex(stripped)):
        command, rest = _command_of(tokens)
        if command is None:
            continue

        if command in SHELL_COMMANDS:
            if "-c" in rest:
                c_at = rest.index("-c")
                if c_at + 1 < len(rest):
                    found |= commands_in(rest[c_at + 1], depth + 1)
            continue

        found.add(command)

        # `gh api ...` specifically — NOT bare `gh`.
        if command == "gh" and rest and rest[0] == "api":
            found.add("gh-api")

    return found


# ---------------------------------------------------------------------------
# OUTSIDE-ITS-OWN-DIFF: `gh api` endpoint discrimination
# ---------------------------------------------------------------------------
#
# OMN-15309, found by EXECUTION while building this module's corpus: the
# OMN-14505 predicate admits `gh api` on the strength of the `api` subcommand
# alone, so `gh api repos/OWNER/REPO/pulls/<n> --jq .merged` is accepted as a
# falsifiable probe. It is not. It proves a pull request exists and merged —
# a fact ABOUT the change itself, not about anything the change claims to have
# made true. OMN-14505's own acceptance list names "PR-existence probes" as a
# class that must go RED; the implementation only catches the `gh pr view`
# spelling of it. The `gh api .../pulls/<n>` spelling was, until this ticket,
# ALSO the shape contract_compliance_check.py recommended in its own BLOCK
# message ("gh api repos/OWNER/REPO/pulls/<src_pr> --jq .merged").
#
# Admitted `gh api` endpoints read CONTENT or RUN state at a ref. Refused ones
# read PR/issue metadata. `/pulls/<n>/files` is admitted: it returns the actual
# diff, not merely the fact that a PR exists.
_GH_METADATA_ENDPOINT_RE = re.compile(
    r"/(?:pulls|issues)/\d+(?:/(?:merge|reviews|comments))?/?(?:\?|$)",
    re.IGNORECASE,
)


def _first_operand_after(tokens: list[str], start: int) -> str | None:
    """First non-flag operand at or after ``start``, stopping at an operator."""
    for candidate in tokens[start:]:
        if candidate in _OPERATOR_TOKENS:
            return None
        if candidate.startswith("-"):
            continue
        return candidate
    return None


def _gh_api_endpoints_in_tokens(tokens: list[str]) -> set[str]:
    """Endpoint operands of ``gh api <endpoint>`` pairs in one token stream."""
    endpoints: set[str] = set()
    for idx, token in enumerate(tokens):
        if Path(token).name.lower() != "gh":
            continue
        if tokens[idx + 1 : idx + 2] != ["api"]:
            continue
        operand = _first_operand_after(tokens, idx + 2)
        if operand is not None:
            endpoints.add(operand)
    return endpoints


def gh_api_endpoints(script: str, depth: int = 0) -> set[str]:
    """Return the endpoint operand of every ``gh api <endpoint>`` invocation."""
    if depth > _MAX_SUBSTITUTION_DEPTH or not script.strip():
        return set()

    endpoints: set[str] = set()
    for match in _CMD_SUBST_RE.finditer(script):
        endpoints |= gh_api_endpoints(match.group(1), depth + 1)
    for match in _BACKTICK_RE.finditer(script):
        endpoints |= gh_api_endpoints(match.group(1), depth + 1)

    stripped = _BACKTICK_RE.sub(" ", _CMD_SUBST_RE.sub(" ", script))
    tokens = _lex(stripped)
    endpoints |= _gh_api_endpoints_in_tokens(tokens)
    # `bash -c '<script>'` — recurse so a wrapped `gh api` is still seen.
    for idx, token in enumerate(tokens):
        is_shell_c = (
            Path(token).name.lower() in SHELL_COMMANDS
            and tokens[idx + 1 : idx + 2] == ["-c"]
            and idx + 2 < len(tokens)
        )
        if is_shell_c:
            endpoints |= gh_api_endpoints(tokens[idx + 2], depth + 1)
    return endpoints


def _gh_api_is_metadata_only(script: str) -> set[str] | None:
    """Offending endpoints when EVERY ``gh api`` call reads PR/issue metadata."""
    endpoints = gh_api_endpoints(script)
    if not endpoints:
        return None
    metadata = {e for e in endpoints if _GH_METADATA_ENDPOINT_RE.search(e)}
    if metadata and metadata == endpoints:
        return metadata
    return None


# ---------------------------------------------------------------------------
# OUTSIDE-ITS-OWN-DIFF: path operands vs. the PR's own changed files
# ---------------------------------------------------------------------------

#: A token that looks like a repo-relative path operand (has a slash or a file
#: extension) rather than a flag, a URL, or free prose.
_PATH_OPERAND_RE = re.compile(r"^[A-Za-z0-9_./\-\$\{\}]+$")


def _path_operands(script: str) -> set[str]:
    """Repo-relative path-looking operands appearing anywhere in ``script``."""
    operands: set[str] = set()
    for token in _lex(script):
        if token in _OPERATOR_TOKENS or token.startswith("-"):
            continue
        if "://" in token:
            continue
        if not _PATH_OPERAND_RE.match(token):
            continue
        if "/" not in token and "." not in token:
            continue
        operand = token[:-1] if token.endswith("/") else token
        operands.add(operand.lstrip("./"))
    return operands


def _normalise_changed(changed_paths: Iterable[str]) -> set[str]:
    return {p.strip().lstrip("./") for p in changed_paths if p and p.strip()}


def _only_reads_own_diff(script: str, changed: set[str]) -> set[str] | None:
    """Return the offending operands when EVERY path operand is in ``changed``.

    ``None`` means the check reaches at least one path outside the diff (or
    names no path at all, in which case this rule has nothing to say and the
    EXECUTED/FALSIFIABLE half decides).
    """
    operands = _path_operands(script)
    # Only consider operands that name a real repo path in the changed set;
    # a bare `pytest` target like `tests/test_x.py::case` still normalises.
    candidates = {op.split("::", 1)[0] for op in operands}
    candidates = {op for op in candidates if "/" in op or "." in op}
    if not candidates:
        return None
    inside = {op for op in candidates if op in changed}
    if inside and inside == candidates:
        return inside
    return None


# ---------------------------------------------------------------------------
# The predicate
# ---------------------------------------------------------------------------


def classify_evidence(
    check_value: object,
    *,
    admissible_probes: Collection[str] = LIVE_PROBE_COMMANDS,
    changed_paths: Collection[str] | None = None,
) -> AdmissibilityVerdict:
    """Decide whether ``check_value`` is admissible evidence.

    Args:
        check_value: the raw ``check_value`` string from a ``dod_evidence``
            check. Anything that is not a non-empty string is INADMISSIBLE.
        admissible_probes: the ALLOW vocabulary for this consumer. Text-only
            gates pass :data:`LIVE_PROBE_COMMANDS`; a consumer that actually
            executes the value passes
            ``LIVE_PROBE_COMMANDS | EXECUTED_HERMETIC_COMMANDS``.
        changed_paths: repo-relative paths this same change modifies. When
            supplied, a check whose every path operand is inside that set is
            refused as INSIDE_OWN_DIFF — it greps text the author just wrote.

    Returns:
        An :class:`AdmissibilityVerdict`. Fails CLOSED on every ambiguity.
    """
    if not isinstance(check_value, str) or not check_value.strip():
        return AdmissibilityVerdict(
            admissible=False,
            rule=EnumAdmissibilityRule.NOT_EXECUTED,
            reason="check_value is empty or not a string, so nothing executes",
        )

    # (1) DENY self-reference FIRST and unconditionally. This is the rule that
    # defeats embedding a probe keyword as quoted text beside a circular grep.
    matched = is_self_referential(check_value)
    if matched is not None:
        return AdmissibilityVerdict(
            admissible=False,
            rule=EnumAdmissibilityRule.INSIDE_OWN_DIFF,
            reason="self-referential: reads back the receipt/contract tree the "
            "evidence author writes in the same PR, so its verdict is decided by "
            "text the author typed, not by any independent surface (matched "
            f"{matched.pattern!r})",
        )

    # (2) ALLOW only a probe in COMMAND POSITION from this consumer's vocabulary.
    commands = commands_in(check_value)
    probes = commands & set(admissible_probes)
    if not probes:
        non_falsifiable = commands & NON_FALSIFIABLE_COMMANDS
        if non_falsifiable:
            return AdmissibilityVerdict(
                admissible=False,
                rule=EnumAdmissibilityRule.NOT_FALSIFIABLE,
                reason="the only commands in command position "
                f"({sorted(non_falsifiable)}) have an exit status fixed by the "
                "text the author typed — the check cannot go RED",
            )
        return AdmissibilityVerdict(
            admissible=False,
            rule=EnumAdmissibilityRule.NOT_EXECUTED,
            reason="no admissible probe in command position — nothing here executes "
            "against a surface outside the change (commands found: "
            f"{sorted(commands) or 'none'}; expected one of: "
            f"{sorted(admissible_probes)})",
        )

    # (3) A `gh api` probe that only reads PR/issue metadata proves the change
    # exists, not that anything the change claims is true. See
    # _GH_METADATA_ENDPOINT_RE — this is STRICTER than the OMN-14505 source and
    # is the one deliberate, ticketed divergence (parity direction is asserted:
    # this predicate may refuse what deploy-gate admits, never the reverse).
    if probes == {"gh-api"}:
        metadata_only = _gh_api_is_metadata_only(check_value)
        if metadata_only is not None:
            return AdmissibilityVerdict(
                admissible=False,
                rule=EnumAdmissibilityRule.INSIDE_OWN_DIFF,
                reason="the only probe reads pull-request/issue metadata "
                f"({sorted(metadata_only)}) — that proves this change exists and "
                "merged, which is a fact about the change itself, not about "
                "anything it claims to have made true",
            )

    # (4) A TEXT READ of only your own diff is circular. An EXECUTION of your
    # own diff is not -- see TEXT_READING_COMMANDS for why the distinction is
    # load-bearing rather than a carve-out.
    if changed_paths and probes and probes <= TEXT_READING_COMMANDS:
        offending = _only_reads_own_diff(check_value, _normalise_changed(changed_paths))
        if offending is not None:
            return AdmissibilityVerdict(
                admissible=False,
                rule=EnumAdmissibilityRule.INSIDE_OWN_DIFF,
                reason="every path this check reads is modified by the same change "
                f"({sorted(offending)}) — it greps text the author just wrote and "
                "cannot go RED against the state it claims to prove",
            )

    return AdmissibilityVerdict(
        admissible=True,
        rule=EnumAdmissibilityRule.ADMISSIBLE,
        reason=f"executed probe in command position: {sorted(probes)}",
    )


def classify_evidence_item(
    check_type: str,
    check_value: object,
    *,
    admissible_probes: Collection[str] = LIVE_PROBE_COMMANDS,
    changed_paths: Collection[str] | None = None,
) -> AdmissibilityVerdict:
    """Apply the predicate to a ``dod_evidence`` check, honouring ``check_type``.

    Only ``check_type: command`` carries shell text. The other check types have
    structured ``check_value`` shapes, so running the shell analysis over them
    produces a correct verdict with a nonsense explanation (a bare path lexes to
    a "command" named after the file). This dispatcher gives each shape the
    diagnosis that fits it, without changing what the predicate decides.
    """
    kind = (check_type or "").strip().lower()

    if kind in EXISTENCE_CHECK_TYPES:
        return AdmissibilityVerdict(
            admissible=False,
            rule=EnumAdmissibilityRule.NOT_FALSIFIABLE,
            reason=f"check_type={kind!r} asserts only that a path exists "
            f"({check_value!r}); it cannot go RED once the change that adds the "
            "path is applied. Assert the file's CONTENT at a pinned ref instead "
            "(gh api repos/OWNER/REPO/contents/<path>?ref=<sha> ... | grep -q "
            "'<symbol>'), or execute the behaviour (check_type: test_passes).",
        )

    if kind in EXECUTED_CHECK_TYPES:
        if not str(check_value or "").strip():
            return AdmissibilityVerdict(
                admissible=False,
                rule=EnumAdmissibilityRule.NOT_EXECUTED,
                reason=f"check_type={kind!r} with an empty check_value runs nothing",
            )
        return AdmissibilityVerdict(
            admissible=True,
            rule=EnumAdmissibilityRule.ADMISSIBLE,
            reason=f"check_type={kind!r} executes behaviour ({check_value!r}) and goes "
            "RED when that behaviour is wrong",
        )

    if kind == "grep" and isinstance(check_value, dict):
        pattern = str(check_value.get("pattern") or "")
        # A grep check names its target as ``path`` or ``file``; neither means ".".
        target = check_value.get("path")
        if not target:
            target = check_value.get("file")
        path = str(target) if target else "."
        if not pattern:
            return AdmissibilityVerdict(
                admissible=False,
                rule=EnumAdmissibilityRule.NOT_EXECUTED,
                reason="check_type='grep' with no 'pattern' key greps nothing",
            )
        # Reuse the shell path so the DENY half and the own-diff rule apply
        # identically to the structured form.
        return classify_evidence(
            f"grep -rl {shlex.quote(pattern)} {shlex.quote(path)}",
            admissible_probes=set(admissible_probes) | {"grep"},
            changed_paths=changed_paths,
        )

    return classify_evidence(
        check_value,
        admissible_probes=admissible_probes,
        changed_paths=changed_paths,
    )


def admissible_evidence_guidance(repo: str = "OWNER/REPO") -> str:
    """Author-facing guidance describing the PROPERTY, never a magic substring.

    The original defect (OMN-14505) was that the gate advertised a keyword, so
    authors supplied the keyword instead of the evidence. This text names the
    three properties and gives one admissible shape per evidence class.
    """
    return (
        "Admissible evidence must be EXECUTED (a command actually runs), "
        "FALSIFIABLE (it can go RED), and OUTSIDE ITS OWN DIFF (it observes a "
        "surface this PR does not author).\n"
        "  Live runtime fact (out-of-band probe, recorded, then read back from a\n"
        "  surface the PR does not write — NOT drift/dod_receipts/):\n"
        f'    curl -fsS http://<host>:<port>/health | grep -q \'"status":"ok"\'\n'
        "  Compute-only / merged-code fact (hermetic, runs on any CI runner):\n"
        f"    gh api repos/{repo}/contents/<changed_path>?ref=<merge_sha> "
        "--jq .content | base64 -d | grep -q '<symbol the fix introduces>'\n"
        "  Behaviour fact (executed against the product checkout):\n"
        "    uv run pytest tests/test_<area>.py::test_<behaviour> -q\n"
        "REFUSED: grep -q '^status: PASS$' "
        "drift/dod_receipts/OMN-XXXX/<item>/command.yaml "
        "(reads back text this PR authors); test -f src/path/added_by_this_pr.py "
        "(cannot go RED once the PR is applied); gh api repos/OWNER/REPO/pulls/<n> "
        "--jq .merged (proves a PR exists, not that the code works); "
        "echo 'docker exec ...' (the probe name is quoted text, never executed)."
    )
