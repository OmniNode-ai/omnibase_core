# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""lint_contract_check_values.py -- Pre-commit linter for fail-open patterns in
contract check_value fields.

Fail-open patterns cause DoD checks to pass when they should not:
  - `[ -z "$var" ] ||`  — empty-permissive short-circuit (truthy when var is absent)
  - `|| true`           — always-true tail
  - `|| exit 0`         — explicit pass on error
  - `2>/dev/null` at end of fragment (silenced errors without explicit exit check)

These patterns mask missing or failing gates and produce false positives.
The correct fail-closed form is simply `[ "$result" = "SUCCESS" ]`.

Also rejects legacy ``gh pr`` invocations that omit ``${PR_NUMBER}`` or a ``--repo``
argument.  These fail in detached-HEAD CI runs with "could not determine current
branch":

  - ``gh pr checks``          (bare — no PR number)
  - ``gh pr checks --watch``  (bare — no PR number)
  - ``gh pr checks 1430 ...`` (hardcoded integer PR number, mixed with ``${PR_NUMBER}``)
  - ``gh pr view {pr} ...``   (wrong-format ``{x}`` placeholder)

Correct form for checking THIS ticket's own PR:
``gh pr checks ${PR_NUMBER} --repo ${REPO}``

Correct form for a genuine, deliberate reference to a DIFFERENT (sibling/dependency)
PR: a standalone hardcoded PR number with a literal ``--repo``, e.g.
``gh pr checks 1721 --repo OmniNode-ai/omnimarket`` — with NO ``${PR_NUMBER}``
anywhere in the same value (see OMN-14431: ``run_contract_compliance_check.py``'s
``_substitute_tokens`` pre-replaces every ``${PR_NUMBER}``/``${REPO}``/``${TICKET_ID}``
occurrence in the WHOLE check_value string with the runner's OWN values before
``sh -c`` ever runs — before any ``VAR=literal`` prefix assignment in the same
string could take effect. So a value like
``PR_NUMBER=1721 REPO=org/repo gh pr checks ${PR_NUMBER} --repo ${REPO}`` looks
like it pins PR 1721, but the ``${PR_NUMBER}`` token is already gone by the time
the shell would apply the assignment: the assignment is inert, and the check
silently runs against whatever PR the runner is evaluating instead of 1721).

Also rejects predicates pinned to a MUTABLE external state (OMN-15540 Rule F) --
a specific workflow run's ``.conclusion`` (rewritten by a re-run), a deletable
feature-branch ref (404s once the branch is deleted on merge), or an
exact/upper bound on an unanchored, monotonically growing ``search/issues``
count. See the Rule F block below for the measured corpus instances.

Usage:
    uv run python -m omnibase_core.handlers.handler_contract_check_values_lint contracts/OMN-1234.yaml [...]

Exits non-zero if any fail-open, legacy-gh-pr, or mutable-state-pin pattern is
found.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

# ---------------------------------------------------------------------------
# Anti-pattern registry
# ---------------------------------------------------------------------------

# Each entry: (human_readable_name, compiled_regex).
#
# The empty-permissive pattern matches both bare `$VAR` and brace-wrapped
# `${VAR}` forms because shell writers use them interchangeably.
#
# The 2>/dev/null pattern uses `\Z` (absolute end of string) rather than
# `$` with re.MULTILINE. The MULTILINE form produces false positives on
# multi-line fragments where `2>/dev/null` appears at a line boundary but
# is followed by a valid exit check on the next line.
ANTI_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "empty-permissive [ -z ... ] ||",
        re.compile(
            r'\[\s*-z\s+"?\$(?:\{[A-Za-z_][A-Za-z0-9_]*\}|[A-Za-z_][A-Za-z0-9_]*)"?\s*\]\s*\|\|'
        ),
    ),
    (
        "trailing || true",
        re.compile(r"\|\|\s*true\b"),
    ),
    (
        "trailing || exit 0",
        re.compile(r"\|\|\s*exit\s+0\b"),
    ),
    (
        "silenced errors 2>/dev/null at end of fragment",
        re.compile(r"2>/dev/null[\s;]*\Z"),
    ),
]

# Legacy ``gh pr`` patterns that must be rejected.
# These are checked separately from ANTI_PATTERNS because they require
# inspecting the command prefix before applying the regex — a plain regex
# over the full value produces too many false positives on non-gh-pr lines.
#
# Canonical correct form (own PR): ``gh pr checks ${PR_NUMBER} --repo ${REPO}``
# Canonical correct form (genuine cross-PR pin): a standalone hardcoded PR
# number + literal --repo, with NO ${PR_NUMBER} anywhere in the value.
_GH_PR_PREFIX = ("gh pr checks", "gh pr view", "gh pr diff")

# Hardcoded integer PR number: "gh pr checks 1430 --repo ..."
_HARDCODED_PR_NUMBER_RE = re.compile(r"gh pr (?:checks|view|diff)\s+(\d+)\b")

# Wrong-format {pr} / {repo} placeholders
_BRACE_PR_RE = re.compile(r"\{pr\}")
_BRACE_REPO_RE = re.compile(r"\{repo\}")

# OMN-14431: runner-injected tokens that `_substitute_tokens()` pre-replaces
# in the WHOLE check_value string before `sh -c` ever runs. A `VAR=literal`
# prefix assignment sharing the same name as one of these tokens is
# unconditionally inert — the token is gone before the assignment could take
# effect — regardless of whether the command is a `gh pr` invocation.
_RUNNER_INJECTED_VARS = ("PR_NUMBER", "REPO", "TICKET_ID")


# ---------------------------------------------------------------------------
# OMN-15382 Rule A: executable-command-shape
#
# `check_type: command` values are handed verbatim to `sh -c` by
# `contract_compliance_check._check_command`. A value that OPENS with English
# prose describing what was run ("Recorded product receipt: uv run pytest ...")
# is not a command at all -- `sh` fails on the first word with "command not
# found" (exit 127), so the check always BLOCKs when actually executed. This
# was the root defect behind OMN-15382 (3/7 dod_verify failures on
# contracts/OMN-14968.yaml): four items were authored as human-readable
# descriptions of a command that had already been run by hand, never as an
# executable command a hosted runner can re-run.
#
# The rule: strip any leading simple `VAR=literal` (no internal whitespace,
# no `$()`/quoting) env-assignment tokens, then require the first remaining
# token to be either a recognized command head or a POSIX shell
# control-flow/builtin keyword that can legitimately open a compound
# fragment (`if`, `case`, `for`, `!`, `[`, `:`, ...). A value that opens with
# `IDENTIFIER=` but whose value is NOT a bare literal (a command-substitution
# or quoted assignment, e.g. ``state=$(gh pr view ...)`` or
# ``f="$(mktemp)" && ...``) is a legitimate multi-statement shell fragment
# and is exempted rather than mis-tokenized by a non-shell-aware parser.
#
# Extending the allowlist requires touching this file -- a deliberate
# ratchet (mirrors the OMN-9350 anti-pattern registry above).
# ---------------------------------------------------------------------------

_COMMAND_HEAD_ALLOWLIST: frozenset[str] = frozenset(
    {
        "gh",
        "git",
        "uv",
        "npm",
        "npx",
        "python",
        "python3",
        "bash",
        "sh",
        "pytest",
        "docker",
        "pre-commit",
        "rg",
        "grep",
        "find",
        "echo",
        "printf",
        "jq",
        "base64",
        "sha256sum",
        "cat",
        "ls",
        "cd",
        "env",
        "curl",
        # OMN-17446: read-only AWS probes are a real evidence class here — an
        # SSM invocation readback is how a live cluster measurement is made
        # re-resolvable without re-running it. `aws` is unambiguously a command
        # head, never prose, which is the distinction Rule A draws.
        "aws",
        "mktemp",
        "diff",
        "cmp",
        "sort",
        "cut",
        "sed",
        "awk",
        "tr",
        "wc",
        "head",
        "tail",
        "xargs",
        "mkdir",
        "rm",
        "touch",
        "true",
        "false",
        "ssh",
        "shellcheck",
    }
)

# POSIX shell control-flow / builtin tokens that can legitimately be the
# FIRST word of a `sh -c` fragment (compound commands, negation, grouping,
# the `test`/`:` builtins). These are not "commands" in the allowlist sense
# above but are unambiguously executable shell syntax, not prose.
_CONTROL_KEYWORD_HEADS: frozenset[str] = frozenset(
    {"if", "for", "while", "until", "case", "test", "!", "[", "{", "(", ":"}
)

# A leading `IDENTIFIER=` at the very start of the (stripped) value -- used
# to detect an assignment-prefixed fragment. Matched BEFORE and AFTER the
# literal-prefix strip: if it still matches after stripping, the assignment
# value was non-literal (command substitution / quoted) and the whole value
# is exempted rather than mis-tokenized.
_ENV_ASSIGN_HEAD_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")

# Repeated simple `VAR=literal` prefixes: value has no internal whitespace,
# no `$`, and no quote characters (a bare literal, e.g. `PR_NUMBER=1721`).
_LITERAL_ENV_PREFIX_RE = re.compile(r"^(?:[A-Za-z_][A-Za-z0-9_]*=[^\s;\"'$]*[\s;]+)+")


def _command_head_violation(value: str) -> str | None:
    """Return a label if *value* does not open with an executable command.

    Returns ``None`` when the value is clean (or not evaluable by this
    simple, non-shell-aware heuristic -- see module docstring above).
    """
    stripped = value.strip()
    if not stripped:
        return None

    m = _LITERAL_ENV_PREFIX_RE.match(stripped)
    rest = stripped[m.end() :] if m else stripped

    if _ENV_ASSIGN_HEAD_RE.match(rest):
        # Non-literal assignment prefix (command substitution / quoted) --
        # a legitimate multi-statement shell fragment. Exempt: prose never
        # opens with `IDENTIFIER=`.
        return None

    parts = rest.split()
    if not parts:
        return None
    first = parts[0]

    if first in _CONTROL_KEYWORD_HEADS or first in _COMMAND_HEAD_ALLOWLIST:
        return None

    # Subshell grouping / negation directly concatenated with the next word,
    # e.g. ``(gh pr view ...)`` with no space after the paren.
    if first[:1] in {"(", "!"} and (
        first[1:] in _COMMAND_HEAD_ALLOWLIST or len(first) == 1
    ):
        return None

    if first.endswith(":"):
        return (
            f"executable-command-shape: check_value opens with a prose label "
            f"({first!r}), not an executable command -- check_values are handed "
            "verbatim to `sh -c` and a prose opener always fails with "
            "'command not found' when actually run (OMN-15382)"
        )
    return (
        f"executable-command-shape: first token {first!r} is not a recognized "
        "command head or shell control keyword -- check_values must be "
        "literal, executable shell commands, not a description of a command "
        "already run by hand (OMN-15382)"
    )


# ---------------------------------------------------------------------------
# OMN-15382 Rule B: per-item PR binding
#
# A dod_evidence `id` that embeds a PR number (``pr-(\d+)``) declares intent
# to pin evidence to THAT specific PR. If every `gh pr view/checks/diff` call
# in its check_values uses only the bare ``${PR_NUMBER}`` runner placeholder
# -- never the literal number from the id -- the check silently re-targets
# whatever PR the compliance runner happens to be evaluating (the OMN-15382
# class-3 PR-number mis-binding defect: contracts/OMN-14968.yaml's
# `dod-OmniNode-ai-omnibase_infra-pr-2536` item used exactly this bare-token
# form and never actually pinned PR #2536).
# ---------------------------------------------------------------------------

_ITEM_ID_PR_RE = re.compile(r"pr-(\d+)")
_GH_PR_CALL_RE = re.compile(r"gh pr (?:view|checks|diff)\b")


def _is_generated_product_ci_item(dod_id: str) -> bool:
    """Return true for the generated product diff-scope companion item.

    The OCC companion producers intentionally keep the product ``-ci`` item in
    runner-placeholder form so public and private product repos share one hosted
    contract vocabulary. Rule B still applies to self-bind and non-CI
    PR-numbered evidence items, where a placeholder would silently target the
    OCC PR rather than the cited product PR.
    """
    return dod_id.startswith("dod-") and "-pr-" in dod_id and dod_id.endswith("-ci")


def _pr_binding_violation(dod_id: str, values: list[str]) -> str | None:
    """Return a label if a PR-numbered item never literally pins that PR."""
    match = _ITEM_ID_PR_RE.search(dod_id)
    if not match:
        return None
    if _is_generated_product_ci_item(dod_id):
        return None
    pr_number = match.group(1)

    gh_pr_values = [v for v in values if _GH_PR_CALL_RE.search(v)]
    if not gh_pr_values:
        return None

    for value in gh_pr_values:
        if pr_number in value:
            return None

    return (
        f"pr-binding: id {dod_id!r} embeds PR #{pr_number} but no "
        "`gh pr view/checks/diff` check_value in this item references that "
        "literal number -- a bare ${PR_NUMBER} placeholder resolves to "
        "whatever PR the compliance runner is evaluating, not the pinned PR "
        "(OMN-15382 class-3 mis-binding)"
    )


# ---------------------------------------------------------------------------
# OMN-15391 Rule C: tautological self-comparison
#
# A check_value whose truth value is fixed by its own text proves nothing.
# The shipped instance (OCC#5481, 8 items) was:
#
#     gh pr view 5408 --repo OmniNode-ai/onex_change_control --json number \
#       --jq '.number == 5408' | grep -qx true
#
# The number handed to `gh pr view` and the number it is compared against are
# the SAME literal, so the assertion is `N == N` -- true by construction for
# every PR that exists. It cannot go RED for any product reason; only deleting
# the PR from GitHub would move it. Such an item is EXECUTED and looks
# ADMISSIBLE to the OMN-15309 predicate (it is a real command with a real exit
# code) while being unfalsifiable, which is precisely the false-green class
# OMN-15391 exists to retire.
#
# The rule: if an identity field (`.number` / `.id` / `.databaseId`) is
# compared for equality against a literal that ALSO appears as the PR/issue
# selector of the same command, the comparison is a tautology.
#
# The fail-closed replacement binds a fact the selector does NOT determine --
# e.g. that the PR's file list contains this ticket's own contract:
#
#     gh api repos/OWNER/REPO/pulls/5408/files --paginate --jq '.[].filename' \
#       | grep -qx 'contracts/OMN-14979.yaml'
#
# which goes RED when pointed at any PR that does not carry that contract.
# ---------------------------------------------------------------------------

_PR_SELECTOR_RE = re.compile(
    r"(?:gh\s+pr\s+(?:view|checks|diff)\s+|/(?:pulls|issues)/)(\d+)"
)

# The `--jq <program>` operand, single- or double-quoted.
_JQ_PROGRAM_RE = re.compile(r"--jq\s+(?:'([^']*)'|\"([^\"]*)\")")

# A jq program that is NOTHING BUT an identity comparison. The `\Z` anchors
# are load-bearing: `.number == 5437 and .state == "MERGED"` must NOT match,
# because the `.state` conjunct is falsifiable and makes the whole check able
# to go RED. Only a bare `.number == N` is a pure tautology.
_JQ_PURE_IDENTITY_EQ_RE = re.compile(
    r"\A\s*\.(?:number|id|databaseId)\s*==\s*(\d+)\s*\Z"
)


def _tautological_selfcheck_violation(value: str) -> str | None:
    """Return a label if *value*'s ONLY assertion is a selector-determined id.

    Deliberately narrow. A jq program that ANDs the identity comparison with
    any other predicate (``.state``, ``.headRefName``, ...) is NOT flagged: the
    extra conjunct is falsifiable, so the check as a whole can go RED. Only a
    jq program consisting solely of ``.number == <selector>`` is a tautology.
    """
    compared: set[str] = set()
    for match in _JQ_PROGRAM_RE.finditer(value):
        program = match.group(1) if match.group(1) is not None else match.group(2)
        pure = _JQ_PURE_IDENTITY_EQ_RE.match(program or "")
        if pure:
            compared.add(pure.group(1))
    if not compared:
        return None
    selectors = {m.group(1) for m in _PR_SELECTOR_RE.finditer(value)}
    overlap = compared & selectors
    if not overlap:
        return None
    number = sorted(overlap)[0]
    return (
        f"tautological-self-comparison: the value selects PR/issue #{number} "
        f"and then asserts its identity field equals {number} -- an `N == N` "
        "comparison that is true by construction for every PR that exists and "
        "cannot go RED for any product reason. Bind a fact the selector does "
        "not already determine (e.g. that the PR's file list contains this "
        "ticket's contract) (OMN-15391 Rule C)"
    )


# ---------------------------------------------------------------------------
# OMN-15391 Rule D: fail-open zero-count pipe
#
# The shipped absence-control idiom (OCC#5481, 12 items) was:
#
#     gh api ... 'repos/O/R/contents/FILE?ref=PARENT' \
#       | grep -c 'MARKER' | grep -qx 0
#
# `check_value`s are handed to `sh -c` WITHOUT `pipefail`, so a failed
# producer (404, auth failure, deleted repo, network error) writes nothing to
# stdout, `grep -c` dutifully prints `0`, and `grep -qx 0` exits 0 -- GREEN.
# The leg therefore passes without ever reading the file it claims to have
# read. Proven by execution at authoring time: the shape returns rc=0 against
# `OmniNode-ai/no_such_repo_xyz`, a repository that does not exist.
#
# Adding `pipefail` does not rescue it either: `grep -c` exits 1 when the
# count is 0, so under `pipefail` the pipeline reports failure on exactly the
# case it is trying to assert. The shape is wrong in both shells.
#
# The two fail-closed replacement idioms are written out in the docstring of
# ``_fail_open_zero_count_violation`` below.
# ---------------------------------------------------------------------------

_COUNT_STAGE = r"(?:grep\s+-[A-Za-z]*c[A-Za-z]*(?:\s+[^|]*)?|wc\s+-l\s*)"
_ZERO_ASSERT = (
    r"grep\s+-[A-Za-z]*q[A-Za-z]*\s+(?:'\^?0\$?'|\"\^?0\$?\"|\^?0\$?)(?:\s|$)"
)
_ZERO_COUNT_PIPE_RE = re.compile(r"\|\s*" + _COUNT_STAGE + r"\|\s*" + _ZERO_ASSERT)


def _fail_open_zero_count_violation(value: str) -> str | None:
    """Return a label if *value* asserts absence via a zero-count pipe.

    The two sanctioned fail-closed replacements, depending on whether the file
    exists at the parent ref.

    1. File PRESENT at the parent ref. Read once, prove the read landed with a
       positive anchor that must be present, and only then assert absence::

           body=$(gh api ... 'repos/O/R/contents/FILE?ref=PARENT')
             && grep -qF 'ANCHOR' <<< "$body"
             && ! grep -qF 'MARKER' <<< "$body"

       A failed fetch yields an empty body, the anchor leg fails, and the check
       goes RED. Pick an anchor present at BOTH the parent and the merge ref so
       it tracks the read rather than the fix.

       Use a HERE-STRING (``<<<``), not ``printf '%s' "$body" | grep -qF``.
       Both forms read the same already-materialized variable, but the pipe
       form is itself SIGPIPE-fragile once ``$body`` is large enough: `grep
       -qF` exits at the first match and closes its stdin, `printf`'s blocked
       `write()` is then killed by SIGPIPE, and the compliance runner's `bash
       -o pipefail -c` (see the knowledge base's `dod-check-types.md`:
       https://github.com/OmniNode-ai/knowledge-base/blob/main/reference/dod-check-types.md)
       surfaces that as exit 141 for a chain in which every assertion actually
       passed. A here-string
       has no pipe stage at all, so it cannot be killed this way regardless
       of size or match position. See OMN-16916 (OMN-15772 discovered this
       measuring its own merged item, commit 4c48f4b40).

    2. File ABSENT at the parent ref (net-new). Pair a reachability control
       with the path-absence assertion, so a 404 counts as evidence of absence
       only after the same token has demonstrably read the same ref::

           gh api 'repos/O/R/commits/PARENT' --jq '.sha' | grep -qx 'PARENT'
             && ! gh api 'repos/O/R/contents/FILE?ref=PARENT' --silent
    """
    if not _ZERO_COUNT_PIPE_RE.search(value):
        return None
    return (
        "fail-open-zero-count: absence is asserted by piping a producer into "
        "`grep -c ... | grep -qx 0`. check_values run under `sh -c` without "
        "pipefail, so a producer that fails (404 / auth / deleted repo / "
        "network) emits nothing, the count prints 0, and the check passes "
        "GREEN without ever reading what it claims to have read. Read once "
        "into a variable, prove the read with a positive anchor, then assert "
        "absence with `! ... grep -qF` (OMN-15391 Rule D)"
    )


# ---------------------------------------------------------------------------
# OMN-15540 Rule F: predicate pinned to a MUTABLE external state
#
# A check_value whose predicate can only ever be satisfied by an
# IMMUTABLE-PAST state. Two directions, one root cause -- the predicate is
# written against a surface that keeps moving:
#
#   1. It can NEVER pass, because the state it pins has already been erased
#      (a workflow re-run, a deleted branch). Deterministic BLOCK forever.
#   2. It pins a MUTABLE state as if it were immutable -- green today by luck,
#      permanent BLOCK the moment the surface moves. The thing that moves it is
#      usually the very repair the ticket exists to make.
#
# This is the opposite direction from OMN-14767's `check_contract_dod_authoring`
# "impossible pre-merge" class (`state == MERGED` asserted while the PR is still
# open), which is a TIMING defect that resolves itself on merge. Rule F's class
# never resolves: it gets worse with time.
#
# Why this matters beyond a red check: an unsatisfiable check produces an
# unresolvable red, which produces a "red-but-accepted" adjudication request,
# which spends operator judgement on a defect that was AUTHORED rather than
# discovered. Stopping the class stops the escalations.
#
# --- F1: a specific workflow run's `.conclusion`, asserted -------------------
# Job and run conclusions are REWRITTEN in place by "Re-run jobs" / "Re-run
# failed jobs" -- the run id is stable, the conclusion under it is not.
# Measured at authoring time (2026-07-30) on the corpus' own instance,
# contracts/OMN-15484.yaml: the check asserts run 30565261108's
# `occ-preflight / eligibility` concluded `failure`; the job had since been
# re-run and reads `success`, so `bash -o pipefail -c '<the literal bytes>'`
# exits 1. Nothing can ever make it exit 0 again.
#
# Pinning `failure` is the strictly-never-passable direction and is what the
# class is named for, but pinning `success` is flagged too: it is the same
# unstable read, green only until someone re-runs the job. The durable form
# records the observed conclusion in a receipt under drift/dod_receipts/ and
# asserts the receipt, or asserts a MONOTONE property of the run (the gate job
# exists / reported at all) rather than one transient verdict.
#
# --- F2: a deletable branch head pinned as a content ref --------------------
# GitHub deletes a PR head branch on merge, after which every
# `?ref=<that-branch>` fetch 404s forever. Corpus instance
# contracts/OMN-10765.yaml (dod-001/dod-002) pins
# `?ref=<user>/omn-10765-port-change-aware-test-selection-to-omniintelligence`;
# live readback returns `HTTP 404 -- No commit found for the ref`. This is the
# exact failure the `reference_never_pin_a_feature_branch_head` rule names:
# pin the SQUASH COMMIT on the mainline, never the branch head.
#
# MAINLINE REFS ARE EXEMPT, DELIBERATELY. `?ref=dev` / `?ref=main` asserting
# that a fix is live on the mainline is the merged-is-not-deployed discipline,
# not a defect -- the branch is never deleted and the assertion is a live
# readback by design. There are 8 such instances in the corpus; flagging them
# would be exactly the noise the Rule E block above warns makes a rule
# something the corpus learns to ignore. Short SHAs (>=7 hex) are immutable and
# exempt; runner-substituted refs (`${PRODUCT_HEAD}`) are judged by the runner,
# not here; `<branch>`-style placeholders inside prose examples are not refs.
#
# --- F3: an unanchored-cumulative count bound -------------------------------
# An EXACT or UPPER bound (`== N`, `<= N`, `-eq N`, `grep -qx N`) on a
# `search/issues` count whose result set only ever grows. The set is bounded
# only by a CLOSED date range (`created:A..B`) or by `is:open` (which drains as
# PRs close); a bare `created:>X` is open-ended and bounds nothing above.
# Corpus instances live in contracts/OMN-15192.yaml. That contract's own R32
# block records the class going RED on a legitimate head-refresh re-mint in
# contract-compliance run 30462434211 -- routine producer behaviour (OMN-14941)
# permanently falsifies the bound.
#
# LOWER bounds (`>= N`) are monotone-safe on a growing set and are NOT flagged.
# `N == 0` is excluded: asserting zero over a forward window is a real forward
# invariant, and the fail-open shape of zero-assertions is already Rule D's
# territory -- two rules firing on one line teaches nothing.
# ---------------------------------------------------------------------------

# F1 -------------------------------------------------------------------------
_RUN_ID_RE = re.compile(r"actions/runs/\d+\b")
_CONCLUSION_FIELD_RE = re.compile(r"\.conclusion\b")
# Any consumer that turns the read into an exit status: a `grep -q` family
# filter, a `test`/`[` string comparison, or a jq boolean projection.
_CONCLUSION_ASSERT_RE = re.compile(
    r"\|\s*(?:grep|egrep|fgrep)\s+-[A-Za-z]*q"
    r"|\btest\s+[\"']"
    r"|\[\s+[\"']"
    r"|--jq\s+'[^']*(?:==|!=|<=|>=)"
)

# ATTEMPT-ANCHORED READS ARE EXEMPT -- this is the sanctioned repair, and
# flagging it would make Rule F block the fix rather than the defect.
#
# A workflow run's LATEST-attempt job record is overwritten by a re-run, but the
# PER-ATTEMPT records are immutable: a re-run appends attempt N+1 and never
# rewrites attempt N. Verified live on the corpus' own instance (run
# 30565261108, 2026-07-30):
#
#   ?filter=all -> [{attempt:1, conclusion:"failure"},
#                   {attempt:2, conclusion:"success"}]
#
# so the attempt-1 `failure` the OMN-15484 evidence needs survives the re-run
# that erased it from the default (latest-only) view. Two spellings qualify:
#
#   a) `/actions/runs/<id>/attempts/<n>/jobs` -- the attempt is in the path.
#   b) `?filter=all` AND a `run_attempt` selector -- all attempts are returned
#      and one is selected.
#
# BOTH halves of (b) are required, deliberately. `select(.run_attempt==1)`
# WITHOUT `filter=all` is still a defect and stays flagged: the default endpoint
# returns only the latest attempt, so after a re-run the selector matches
# nothing, the producer emits no output, and `grep -qx` goes RED on empty input
# -- the same permanent block by a different route.
_ATTEMPT_PATH_RE = re.compile(r"actions/runs/\d+/attempts/\d+\b")
_FILTER_ALL_RE = re.compile(r"[?&]filter=all\b")
_RUN_ATTEMPT_SELECTOR_RE = re.compile(r"\.run_attempt\s*==\s*\d+")


def _is_attempt_anchored(value: str) -> bool:
    """Return True when the run read is pinned to an immutable attempt record."""
    if _ATTEMPT_PATH_RE.search(value):
        return True
    return bool(_FILTER_ALL_RE.search(value) and _RUN_ATTEMPT_SELECTOR_RE.search(value))


# F2 -------------------------------------------------------------------------
# A git ref that is immutable by construction: an abbreviated-or-full commit
# SHA. GitHub resolves abbreviations from 7 characters.
_SHA_REF_RE = re.compile(r"^[0-9a-f]{7,40}$")
# Long-lived refs that are never deleted, so a pin against them is a live
# mainline readback rather than a dangling reference.
_MAINLINE_REFS: frozenset[str] = frozenset({"dev", "main", "master", "HEAD"})
# Release tags are immutable in practice (`v1.2.3`, `1.2.3`).
_TAG_REF_RE = re.compile(r"^v?\d+\.\d+")
_QUERY_REF_RE = re.compile(r"[?&]ref=([^&'\"\s|)]+)")
_COMMITS_SEGMENT_RE = re.compile(r"/commits/([^/'\"\s?&)]+)")


def _is_stable_ref(ref: str) -> bool:
    """Return True when *ref* cannot dangle (SHA, tag, mainline, or dynamic)."""
    # Runner- or shell-substituted: the value is not knowable statically, and
    # `_check_inert_token_prefix` / Rule B already govern placeholder misuse.
    if "$" in ref or "{" in ref:
        return True
    # Prose placeholders inside documentation-style values (`<branch>`, `<sha>`).
    if "<" in ref or ">" in ref or "`" in ref:
        return True
    bare = ref[len("refs/heads/") :] if ref.startswith("refs/heads/") else ref
    if ref.startswith("refs/tags/"):
        return True
    if bare in _MAINLINE_REFS:
        return True
    return any(shape.match(bare) for shape in (_SHA_REF_RE, _TAG_REF_RE))


# F3 -------------------------------------------------------------------------
_SEARCH_ISSUES_RE = re.compile(r"search/issues\?q=")
_TOTAL_COUNT_RE = re.compile(r"total_count")
# A CLOSED date range (`created:A..B`) genuinely bounds the set from above.
# A bare `created:>X` does not -- it is open-ended forward.
_CLOSED_RANGE_ANCHOR_RE = re.compile(
    r"(?:created|merged|closed|updated)(?:%3A|:)[^+'\"\s]*\.\."
)
# `is:open` drains as PRs close, so it bounds an open-count assertion.
_IS_OPEN_ANCHOR_RE = re.compile(r"is(?:%3A|:)open")
_UPPER_OR_EXACT_BOUND_RE = re.compile(
    r"total_count\s*(?:<=|<|==)\s*(\d+)"
    r"|-(?:eq|le|lt)\s+(\d+)"
    r"|grep\s+-[A-Za-z]*q[A-Za-z]*\s+'?\"?\^?(\d+)"
)


def mutable_run_conclusion_violation(value: str) -> str | None:
    """Return a label if *value* asserts a pinned workflow run's conclusion."""
    if not (
        _RUN_ID_RE.search(value)
        and _CONCLUSION_FIELD_RE.search(value)
        and _CONCLUSION_ASSERT_RE.search(value)
    ):
        return None
    if _is_attempt_anchored(value):
        return None
    return (
        "mutable-state-pin/run-conclusion: the predicate asserts the "
        "`.conclusion` of a specific `actions/runs/<id>`. Run and job "
        "conclusions are rewritten in place by 'Re-run jobs', so the run id is "
        "stable while the verdict under it is not -- asserting `failure` is "
        "erased by the first re-run or repair (deterministic BLOCK, the "
        "OMN-15484 shape), and asserting `success` is green only until someone "
        "re-runs the job. Record the observed conclusion in a receipt under "
        "drift/dod_receipts/ and assert the receipt, or assert a monotone "
        "property of the run (the gate job reported at all) rather than one "
        "transient verdict. The attempt-anchored form is exempt: "
        "`?filter=all` plus a `.run_attempt==N` selector, or the "
        "`/actions/runs/<id>/attempts/<n>/jobs` path (OMN-15540 Rule F)"
    )


def deletable_branch_ref_violation(value: str) -> str | None:
    """Return a label if *value* pins a ref that can be deleted."""
    refs = [m.group(1) for m in _QUERY_REF_RE.finditer(value)]
    refs += [m.group(1) for m in _COMMITS_SEGMENT_RE.finditer(value)]
    for ref in refs:
        if _is_stable_ref(ref):
            continue
        return (
            f"mutable-state-pin/deletable-branch-ref: the predicate pins ref "
            f"`{ref}`, which is neither a commit SHA, a tag, nor a mainline "
            "branch. GitHub deletes a PR head branch on merge, after which "
            "every fetch at that ref 404s and the check can never pass again "
            "(the OMN-10765 shape). Pin the squash commit on the mainline "
            "instead -- `reference_never_pin_a_feature_branch_head` "
            "(OMN-15540 Rule F)"
        )
    return None


def unanchored_cumulative_bound_violation(value: str) -> str | None:
    """Return a label if *value* upper-bounds an unbounded growing count."""
    if not (_SEARCH_ISSUES_RE.search(value) and _TOTAL_COUNT_RE.search(value)):
        return None
    if _CLOSED_RANGE_ANCHOR_RE.search(value) or _IS_OPEN_ANCHOR_RE.search(value):
        return None
    match = _UPPER_OR_EXACT_BOUND_RE.search(value)
    if match is None:
        return None
    bound = next(g for g in match.groups() if g is not None)
    if int(bound) == 0:
        return None
    return (
        f"mutable-state-pin/unanchored-cumulative: the predicate bounds a "
        f"`search/issues` count from above (<= {bound}) but the query carries "
        "no closed date range (`created:A..B`) and no `is:open`, so the result "
        "set only ever grows -- the bound is falsified permanently by the next "
        "routine head-refresh re-mint (OMN-14941; already observed going RED "
        "in contract-compliance run 30462434211). Anchor the query to a closed "
        "window, scope it to `is:open`, or assert a monotone lower bound "
        "(`>= N`) instead (OMN-15540 Rule F)"
    )


# ---------------------------------------------------------------------------
# OMN-15411 Rule E: SIGPIPE-fragile early-exit consumer (WARNING tier)
#
# `grep -q` exits at the FIRST match and closes its stdin. If the upstream
# stage still has bytes to write, it is killed by SIGPIPE and exits 141
# (128+13). omnimarket#1949 (OMN-15382) correctly moved the dod_verify command
# runner to `bash -o pipefail`, so that 141 now propagates as the pipeline's
# exit status -- a **false RED on genuinely-passing evidence**. The same
# command exits 0 when run outside pipefail, which is what makes the class so
# confusing in the field: the check reproduces green by hand and red in the
# runner.
#
# Whether a given pipeline is exposed depends on whether the producer still
# has unwritten output when grep exits -- i.e. on output volume relative to
# the pipe buffer, and on how many write syscalls the producer makes. That is
# not statically decidable, so this rule flags only producer shapes MEASURED
# to reproduce 141 against the corpus' own real inputs (5 runs each, under
# `bash -o pipefail -c`, 2026-07-29):
#
#   gh api <contents> --jq .content | base64 -d | grep -q ...   -> 141,0,141,0,141
#   gh pr diff <n> --repo <r>       | grep -q ...               -> 141,141,0,141,141
#   git log --oneline -200          | grep -q ...               -> 141 x5
#   find contracts -name '*.yaml'   | grep -q ...               -> 141 x5
#
# and shapes measured NOT to reproduce it, which this rule must NOT flag or it
# becomes noise the corpus learns to ignore:
#
#   gh pr view <n> --json state --jq .state | grep -qx MERGED   -> 0 x5
#   gh api .../pulls/<n> --jq '<scalar>'    | grep -qx true     -> 0 x5
#   find <single-receipt-dir> -type f       | grep -q .         -> 0 x5
#   cat <30KB file>                         | grep -q ...       -> 0 x5
#
# TIER 1 (`_SIGPIPE_FRAGILE_PRODUCERS`) is the ratcheted set: producers whose
# output size is unbounded by construction (a decoded file body, a PR diff, a
# git history walk, a paginated REST list, an iterating jq projection).
#
# TIER 2 (`_SIGPIPE_VOLUME_DEPENDENT_PRODUCERS`) is advisory only: `find`,
# `cat`, `rg`, `docker logs`, `uv run pytest` reproduce 141 on a large input
# and 0 on a small one. The corpus' 84 `find <one-receipt-dir> | grep -q .`
# instances are provably NOT exposed, so ratcheting tier 2 would freeze 85
# non-defects into a debt list.
#
# WARNING TIER, DELIBERATELY: this is a reliability foot-gun, not a fail-open
# hole -- a SIGPIPE false RED fails CLOSED (it blocks a Done flip; it never
# passes something that should fail). Per the ticket, Rule E does NOT change
# this linter's exit code. Growth of the class is stopped by the corpus
# ratchet in tests/unit/scripts/test_lint_contract_check_values_corpus_baseline.py,
# which DOES hard-fail on a new non-generated instance.
#
# The fail-closed replacement is a buffered read: assign the producer's output
# to a shell variable first, so it runs to completion and exits before anything
# reads from it, then assert against that variable with a HERE-STRING --
# `grep -qF 'MARKER' <<< "$body"`, not `printf '%s' "$body" | grep -qF`.
#
# CORRECTION (OMN-16916). The original form of this fix recommended piping a
# `printf` of the buffered variable into `grep -qF`. That is still a pipe,
# and still SIGPIPE-fragile: once `$body` is large enough that printf's
# `write()` blocks on the pipe, an early match by `grep -qF` closes the read
# end and kills printf with SIGPIPE -- the exact 141 this rule exists to
# name, now reproduced by the rule's own prescribed repair. OMN-15772
# measured this on its own merged item (10/10 plain-`bash -c` runs exit 0,
# 10/10 `bash -o pipefail -c` runs exit 141, deterministic for that instance)
# and repaired it append-only in commit 4c48f4b40 by switching to a
# here-string, which involves no pipe at all and so cannot be SIGPIPE'd
# regardless of size or match position. `printf | grep -qF` is NOT added to
# either producer tuple below -- see OMN-16916 AC3 for the scoped corpus
# remediation and the decision to leave that census/repair for a follow-up
# rather than bundle a corpus-scan-affecting detector change into a
# guidance-text fix. See the OCC#5496, OCC#5523, and OCC#7500 repairs for
# merged examples.
#
# ---------------------------------------------------------------------------

# `grep -q` / `grep -qx` / `grep -qF` / `egrep -q`... -- any early-exit form.
_EARLY_EXIT_CONSUMER_RE = re.compile(
    r"\|\s*(?:grep|egrep|fgrep)\s+-[A-Za-z]*q[A-Za-z]*\b"
)

# Tier 1: output unbounded by construction. Ratcheted.
_SIGPIPE_FRAGILE_PRODUCERS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("base64-decoded file body", re.compile(r"\bbase64\s+(?:-d\b|--decode\b|-D\b)")),
    ("gh pr diff", re.compile(r"\bgh\s+pr\s+diff\b")),
    (
        "git history walk",
        re.compile(r"\bgit\s+(?:log|diff|show|ls-files|grep|blame)\b"),
    ),
    ("paginated REST list", re.compile(r"--paginate\b")),
    (
        "iterating jq projection",
        re.compile(r"--jq\s+(?:'[^']*\.\[\][^']*'|\"[^\"]*\.\[\][^\"]*\")"),
    ),
)

# Tier 2: exposed only above a volume threshold. Advisory, never ratcheted.
_SIGPIPE_VOLUME_DEPENDENT_PRODUCERS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("find", re.compile(r"(?:^|[|;&(]\s*)find\s")),
    ("cat", re.compile(r"(?:^|[|;&(]\s*)cat\s")),
    ("recursive grep", re.compile(r"(?:^|[|;&(]\s*)(?:rg|ag)\s")),
    ("docker logs", re.compile(r"\bdocker\s+logs\b")),
    ("pytest output", re.compile(r"\buv\s+run\s+pytest\b")),
)


# Command separators that end one simple command inside a pipeline stage.
_SIMPLE_COMMAND_SEPARATORS = ("&&", "||", ";")

# Shell keywords that introduce a fresh simple command inside a compound
# fragment (`if ...; then <cmd>`, `else <cmd>`, `do <cmd>`).
_COMPOUND_INTRODUCERS_RE = re.compile(r"(?:^|\s)(?:then|else|do|\{)\s")


@dataclass
class _ShellScanState:
    """Quoting / nesting state carried across one check_value scan."""

    in_single: bool = False
    in_double: bool = False
    in_backtick: bool = False
    depth: int = 0


def _consume_quoted(value: str, i: int, state: _ShellScanState, buf: list[str]) -> int:
    """Consume one quoted/escaped span. Return chars consumed, 0 if none."""
    ch = value[i]
    nxt = value[i + 1] if i + 1 < len(value) else ""

    if state.in_single:
        if ch == "'":
            state.in_single = False
        buf.append(ch)
        return 1

    if ch == "\\":
        buf.append(ch)
        if nxt:
            buf.append(nxt)
            return 2
        return 1

    if state.in_double:
        if ch == "$" and nxt == "(":
            state.depth += 1
            buf.append(ch)
            buf.append(nxt)
            return 2
        if ch == ")" and state.depth > 0:
            state.depth -= 1
        elif ch == '"':
            state.in_double = False
        buf.append(ch)
        return 1

    return 0


def _consume_structural(
    value: str, i: int, state: _ShellScanState, buf: list[str]
) -> int:
    """Consume one unquoted char, updating nesting state. Return chars consumed."""
    ch = value[i]
    nxt = value[i + 1] if i + 1 < len(value) else ""

    if ch == "$" and nxt == "(":
        state.depth += 1
        buf.append(ch)
        buf.append(nxt)
        return 2

    if ch == "'":
        state.in_single = True
    elif ch == '"':
        state.in_double = True
    elif ch == "`":
        state.in_backtick = not state.in_backtick
    elif ch == "(":
        state.depth += 1
    elif ch == ")":
        state.depth = max(0, state.depth - 1)

    buf.append(ch)
    return 1


def _split_top_level_pipeline(value: str) -> list[str]:
    """Split *value* on `|` characters that are genuine pipeline separators.

    Naive ``value.split("|")`` is wrong here in the one way that matters most:
    the SANCTIONED repair for this very rule --
    ``body="$(producer | base64 -d)" && printf '%s' "$body" | grep -qF 'X'`` --
    contains a `|` INSIDE a command substitution. Treating that as a pipeline
    separator makes ``base64 -d`` look like the stage feeding grep, so Rule E
    flags its own fix and no repair could ever clear it. This scanner tracks
    quoting and `$( )` / `( )` nesting so only top-level pipes split, and
    leaves `||` alone (a logical OR, not a pipe).
    """
    stages: list[str] = []
    buf: list[str] = []
    state = _ShellScanState()

    i = 0
    while i < len(value):
        consumed = _consume_quoted(value, i, state, buf)
        if consumed:
            i += consumed
            continue

        ch = value[i]
        nxt = value[i + 1] if i + 1 < len(value) else ""
        if ch == "|" and nxt == "|":
            buf.append(ch)
            buf.append(nxt)
            i += 2
            continue
        if ch == "|" and state.depth == 0 and not state.in_backtick:
            stages.append("".join(buf))
            buf = []
            i += 1
            continue

        i += _consume_structural(value, i, state, buf)

    stages.append("".join(buf))
    return stages


def _writer_command(stage: str) -> str:
    """Return the last simple command of *stage* -- the process holding the pipe.

    In ``body="$(...)" && printf '%s' "$body"`` only ``printf`` inherits the
    pipe's write end; the command substitution ran to completion in a child that
    was never connected to it. Likewise for ``if ...; then <cmd>``.
    """
    tail = stage
    for separator in _SIMPLE_COMMAND_SEPARATORS:
        pieces = tail.split(separator)
        tail = pieces[-1]
    matches = list(_COMPOUND_INTRODUCERS_RE.finditer(tail))
    if matches:
        tail = tail[matches[-1].end() :]
    return tail


def _sigpipe_producer_label(
    value: str, producers: tuple[tuple[str, re.Pattern[str]], ...]
) -> str | None:
    """Return the matched producer label for the first exposed `grep -q`.

    Only the writer IMMEDIATELY upstream of the early-exit consumer is
    examined: that is the process the closed pipe kills. A `base64 -d` three
    stages back is irrelevant if a small `--jq` scalar or a `wc -c` sits
    directly in front of the grep -- it was already drained.
    """
    stages = _split_top_level_pipeline(value)
    for index, stage in enumerate(stages[1:], start=1):
        if not _EARLY_EXIT_CONSUMER_RE.match("|" + stage):
            continue
        writer = _writer_command(stages[index - 1])
        for label, pattern in producers:
            if pattern.search(writer):
                return label
    return None


def sigpipe_fragile_violation(value: str) -> str | None:
    """Return a tier-1 (ratcheted) Rule E label, or ``None``."""
    label = _sigpipe_producer_label(value, _SIGPIPE_FRAGILE_PRODUCERS)
    if label is None:
        return None
    return (
        f"sigpipe-fragile: an unbounded producer ({label}) is piped straight "
        "into `grep -q`, which exits at the first match and closes the pipe. "
        "The producer is then killed by SIGPIPE (exit 141) and, under the "
        "dod_verify runner's `bash -o pipefail`, 141 becomes the pipeline's "
        "exit status -- a false RED on evidence that is actually present "
        "(the same command exits 0 when run by hand outside pipefail). "
        "Buffer the producer instead, and assert against the buffered "
        "variable with a HERE-STRING, not a pipe -- `printf | grep -qF` is "
        "itself SIGPIPE-fragile once the variable is large (OMN-16916): "
        'body="$(<producer>)" && grep -qF \'MARKER\' <<< "$body" '
        "(OMN-15411 Rule E)"
    )


def sigpipe_volume_dependent_violation(value: str) -> str | None:
    """Return a tier-2 (advisory, never ratcheted) Rule E label, or ``None``."""
    if sigpipe_fragile_violation(value) is not None:
        return None
    label = _sigpipe_producer_label(value, _SIGPIPE_VOLUME_DEPENDENT_PRODUCERS)
    if label is None:
        return None
    return (
        f"sigpipe-possible: a volume-dependent producer ({label}) is piped "
        "straight into `grep -q`. This reproduces exit 141 under the "
        "dod_verify runner's `bash -o pipefail` once the producer's output "
        "outgrows the pipe buffer, and exits 0 below it -- so it is a latent "
        "false RED that appears when the input grows. Buffer the producer if "
        "its output is not bounded small by construction, and assert against "
        "the buffered variable with a HERE-STRING (`grep -qF 'MARKER' <<< "
        '"$body"`), not `printf | grep -qF` -- that pipe form is itself '
        "SIGPIPE-fragile once the variable is large (OMN-16916) (OMN-15411 "
        "Rule E, advisory tier)"
    )


def lint_contract_warnings(path: Path) -> list[tuple[str, str, str]]:
    """Return non-blocking Rule E findings for *path*.

    Kept separate from :func:`lint_contract` on purpose: these findings must
    never contribute to this script's exit code (see the Rule E block above).
    """
    warnings: list[tuple[str, str, str]] = []

    try:
        raw = path.read_text(encoding="utf-8")
        data = yaml.load(raw, Loader=yaml.SafeLoader)
    except (OSError, yaml.YAMLError):
        # lint_contract() already reports read/parse failures as hard findings.
        return warnings

    if not isinstance(data, dict):
        return warnings

    dod_evidence = data.get("dod_evidence", []) or []
    if not isinstance(dod_evidence, list):
        return warnings
    superseded = _superseded_dod_ids(dod_evidence)

    for item in dod_evidence:
        if not isinstance(item, dict):
            continue
        raw_dod_id = item.get("id", "<unknown>")
        dod_id = raw_dod_id if isinstance(raw_dod_id, str) else "<unknown>"
        if dod_id in superseded:
            continue

        for value in _item_check_values(item):
            for detector in (
                sigpipe_fragile_violation,
                sigpipe_volume_dependent_violation,
            ):
                label = detector(value)
                if label is not None:
                    warnings.append(
                        (str(path), f"{dod_id}: {label}", value.strip()[:80])
                    )

    return warnings


def _item_check_values(item: dict[object, object]) -> list[str]:
    """Return every non-empty check_value string on *item* (nested + legacy flat)."""
    values: list[str] = []
    checks = item.get("checks", [])
    if isinstance(checks, list):
        for check in checks:
            if not isinstance(check, dict):
                continue
            value = check.get("check_value", "")
            if isinstance(value, str) and value.strip():
                values.append(value)
    flat_value = item.get("check_value", "")
    if isinstance(flat_value, str) and flat_value.strip():
        values.append(flat_value)
    return values


# ---------------------------------------------------------------------------
# Core linting logic
# ---------------------------------------------------------------------------


def lint_contract(path: Path) -> list[tuple[str, str, str]]:
    """Lint a single contract file.

    Returns a list of (path_str, pattern_label, offending_fragment) tuples.
    An empty list means the contract is clean.
    """
    findings: list[tuple[str, str, str]] = []

    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as e:
        return [(str(path), "read-error", str(e))]

    try:
        data = yaml.load(raw, Loader=yaml.SafeLoader)
    except yaml.YAMLError as e:
        return [(str(path), "yaml-parse-error", str(e))]

    if not isinstance(data, dict):
        return findings

    dod_evidence = data.get("dod_evidence", []) or []
    superseded = _superseded_dod_ids(dod_evidence)

    for item in dod_evidence:
        if not isinstance(item, dict):
            continue

        raw_dod_id = item.get("id", "<unknown>")
        dod_id = raw_dod_id if isinstance(raw_dod_id, str) else "<unknown>"
        if dod_id in superseded:
            continue
        _scan_dod_item(str(path), item, dod_id, findings)

    return findings


def _scan_dod_item(
    path_label: str,
    item: dict[object, object],
    dod_id: str,
    findings: list[tuple[str, str, str]],
) -> None:
    # dod_evidence items nest checks under a `checks` list.
    checks = item.get("checks", [])
    if not isinstance(checks, list):
        checks = []

    command_values: list[str] = []
    all_values: list[str] = []

    for check in checks:
        if not isinstance(check, dict):
            continue
        value = check.get("check_value", "")
        if not isinstance(value, str) or not value.strip():
            continue
        _scan_value(path_label, dod_id, value, findings)
        all_values.append(value)
        if check.get("check_type", "command") == "command":
            command_values.append(value)

    # Also handle flat check_value at the item level (legacy schema form).
    # The legacy flat form predates check_type and was always a shell command.
    flat_value = item.get("check_value", "")
    if isinstance(flat_value, str) and flat_value.strip():
        _scan_value(path_label, dod_id, flat_value, findings)
        all_values.append(flat_value)
        command_values.append(flat_value)

    # OMN-15382 Rule A: every command-shaped check_value must open with an
    # executable command, not prose describing one.
    for value in command_values:
        label = _command_head_violation(value)
        if label is not None:
            fragment = value.strip()[:80]
            findings.append((path_label, f"{dod_id}: {label}", fragment))

    # OMN-15382 Rule B: a dod_evidence id embedding a PR number must pin that
    # literal number in every gh pr view/checks/diff call it makes.
    binding_label = _pr_binding_violation(dod_id, all_values)
    if binding_label is not None:
        findings.append((path_label, binding_label, dod_id))


def _superseded_dod_ids(dod_evidence: list[object]) -> set[str]:
    """Return ids superseded by later append-only replacement items."""
    seen: set[str] = set()
    superseded: set[str] = set()
    for item in dod_evidence:
        if not isinstance(item, dict):
            continue
        item_id = item.get("id")
        artifact = item.get("evidence_artifact")
        if isinstance(artifact, str):
            prefix = "supersedes_dod_evidence:"
            if artifact.startswith(prefix):
                target = artifact[len(prefix) :].strip()
                if target in seen:
                    superseded.add(target)
        if isinstance(item_id, str):
            seen.add(item_id)
    return superseded


def _check_legacy_gh_pr(value: str) -> str | None:
    """Return a human-readable label if *value* is a legacy ``gh pr`` invocation.

    Returns ``None`` when the command is clean (or not a ``gh pr checks/view/diff``
    command at all).

    Legacy forms:
    * Wrong-format ``{pr}`` / ``{repo}`` placeholders.
    * A hardcoded integer PR number mixed with ``${PR_NUMBER}`` in the same
      value (OMN-14431: ambiguous — the token wins at pre-substitution time,
      silently discarding the literal).
    * Missing both ``${PR_NUMBER}`` and a genuine standalone hardcoded PR
      number.
    * A genuine standalone hardcoded PR number (own-PR checks aside) that
      omits a literal ``--repo`` argument — ``${REPO}`` is NOT accepted here
      because it resolves to the RUNNER's own repo, which is not necessarily
      the repo the pinned PR lives in.
    * Missing both ``${REPO}`` and a literal ``--repo`` argument (own-PR form).

    A standalone hardcoded PR number with NO ``${PR_NUMBER}`` anywhere in the
    value and a literal ``--repo`` argument is the sanctioned, genuinely
    cross-PR form (OMN-14431) — it is executable exactly as written, with no
    runner-side substitution required, so it is accepted.
    """
    stripped = value.strip()
    if not stripped.startswith(_GH_PR_PREFIX):
        return None

    if _BRACE_PR_RE.search(stripped):
        return "legacy-gh-pr: wrong-format {pr} placeholder (use ${PR_NUMBER})"
    if _BRACE_REPO_RE.search(stripped):
        return "legacy-gh-pr: wrong-format {repo} placeholder (use ${REPO})"

    has_hardcoded_pr = bool(_HARDCODED_PR_NUMBER_RE.search(stripped))
    has_pr_token = "${PR_NUMBER}" in stripped

    if has_hardcoded_pr and has_pr_token:
        return (
            "legacy-gh-pr: hardcoded PR number mixed with ${PR_NUMBER} in the "
            "same command is ambiguous — ${PR_NUMBER} is pre-substituted with "
            "the runner's own PR before the literal could ever apply; use "
            "EITHER a standalone hardcoded cross-PR reference (no ${PR_NUMBER} "
            "anywhere in the value) OR ${PR_NUMBER} alone, never both"
        )

    if has_hardcoded_pr:
        # Genuine, standalone cross-PR reference — must be executable exactly
        # as written, so --repo must be a literal (not ${REPO}, which would
        # resolve to the runner's own repo, not necessarily the pinned PR's).
        if "--repo" not in stripped or "${REPO}" in stripped:
            return (
                "legacy-gh-pr: hardcoded cross-PR reference requires a "
                "literal --repo argument (${REPO} resolves to the runner's "
                "own repo, not necessarily the pinned PR's repo)"
            )
        return None

    if not has_pr_token:
        return (
            "legacy-gh-pr: missing ${PR_NUMBER} placeholder or a genuine "
            "standalone hardcoded PR number"
        )
    if "${REPO}" not in stripped and "--repo" not in stripped:
        return "legacy-gh-pr: missing --repo argument"
    return None


def _check_inert_token_prefix(value: str) -> str | None:
    """Return a label if *value* contains an inert ``VAR=literal`` prefix.

    OMN-14431: ``_substitute_tokens()`` in ``run_contract_compliance_check.py``
    replaces every ``${PR_NUMBER}`` / ``${REPO}`` / ``${TICKET_ID}`` occurrence
    in the WHOLE check_value string with the runner's own values BEFORE
    ``sh -c`` is ever invoked — i.e. before any ``VAR=literal`` prefix
    assignment in the same string could take effect. A fragment like
    ``PR_NUMBER=1721 ... ${PR_NUMBER}`` therefore looks like it pins PR 1721,
    but the ``${PR_NUMBER}`` token is already gone by the time the shell would
    apply the assignment: the assignment is dead decoration and the check
    silently runs against whatever PR the runner is evaluating instead of the
    literal 1721. This is NOT limited to ``gh pr`` commands — it applies to
    any command referencing these three runner-injected token names.
    """
    for var in _RUNNER_INJECTED_VARS:
        if re.search(rf"\b{var}=\S", value) and f"${{{var}}}" in value:
            return (
                f"inert-token-prefix: {var}=<literal> prefix is silently "
                f"discarded because ${{{var}}} is pre-substituted with the "
                "runner's own value before the shell ever sees the "
                "assignment take effect — the check runs against the "
                "runner's value, not the literal"
            )
    return None


def _scan_value(
    path_str: str,
    dod_id: str,
    value: str,
    findings: list[tuple[str, str, str]],
) -> None:
    """Scan a single check_value string against all anti-patterns."""
    for name, pattern in ANTI_PATTERNS:
        match = pattern.search(value)
        if match:
            # Provide 20-char context window around match
            start = max(0, match.start() - 20)
            end = min(len(value), match.end() + 20)
            fragment = value[start:end].strip()
            findings.append((path_str, f"{dod_id}: {name}", fragment))

    legacy_label = _check_legacy_gh_pr(value)
    if legacy_label is not None:
        fragment = value.strip()[:80]
        findings.append((path_str, f"{dod_id}: {legacy_label}", fragment))

    inert_label = _check_inert_token_prefix(value)
    if inert_label is not None:
        fragment = value.strip()[:80]
        findings.append((path_str, f"{dod_id}: {inert_label}", fragment))

    # OMN-15391 Rule C: `N == N` comparisons that cannot go RED.
    tautology_label = _tautological_selfcheck_violation(value)
    if tautology_label is not None:
        fragment = value.strip()[:80]
        findings.append((path_str, f"{dod_id}: {tautology_label}", fragment))

    # OMN-15391 Rule D: absence asserted through a fail-open zero-count pipe.
    zero_count_label = _fail_open_zero_count_violation(value)
    if zero_count_label is not None:
        fragment = value.strip()[:80]
        findings.append((path_str, f"{dod_id}: {zero_count_label}", fragment))

    # OMN-15540 Rule F: predicate pinned to a MUTABLE external state. HARD
    # tier (unlike warning-tier Rule E): these fail CLOSED but they fail
    # PERMANENTLY, and an unsatisfiable check is what turns into a
    # "red-but-accepted" operator adjudication.
    for detector in (
        mutable_run_conclusion_violation,
        deletable_branch_ref_violation,
        unanchored_cumulative_bound_violation,
    ):
        mutable_label = detector(value)
        if mutable_label is not None:
            fragment = value.strip()[:80]
            findings.append((path_str, f"{dod_id}: {mutable_label}", fragment))


def _err(message: str) -> None:
    sys.stderr.write(message + "\n")


def main(argv: list[str]) -> int:
    if len(argv) <= 1:
        _err("usage: lint_contract_check_values.py <contract.yaml> [...]")
        return 2

    all_findings: list[tuple[str, str, str]] = []
    all_warnings: list[tuple[str, str, str]] = []
    for arg in argv[1:]:
        path = Path(arg)
        all_findings.extend(lint_contract(path))
        all_warnings.extend(lint_contract_warnings(path))

    # OMN-15411 Rule E is WARNING tier: printed, never fatal. Emitted before
    # the hard findings so it is not buried under a failure block.
    if all_warnings:
        _err(
            "WARN: SIGPIPE-fragile early-exit consumers found in contract "
            "check_value fields (OMN-15411 Rule E -- advisory, does NOT fail "
            "this hook):"
        )
        for path_str, pattern_label, fragment in all_warnings:
            _err(f"  {path_str}: {pattern_label}")
            _err(f"    ...{fragment}...")
        _err(
            "\nFix SIGPIPE-fragile pipelines by buffering the producer:\n"
            "  BAD:  gh api '...?ref=SHA' --jq .content | base64 -d"
            " | grep -q 'MARKER'\n"
            "  GOOD: body=\"$(gh api '...?ref=SHA' --jq .content | base64 -d)\""
            " && printf '%s' \"$body\" | grep -qF 'MARKER'\n"
        )

    # The OCC copy filtered findings through its frozen corpus baselines
    # (OMN-16007); core carries no such baseline, so every finding blocks.
    blocking = all_findings

    if blocking:
        _err("FAIL: invalid patterns found in contract check_value fields:")
        for path_str, pattern_label, fragment in blocking:
            _err(f"  {path_str}: {pattern_label}")
            _err(f"    ...{fragment}...")
        _err(
            "\nFix fail-open guards with fail-closed form, e.g.:\n"
            '  BAD:  [ -z "$result" ] || [ "$result" = "SUCCESS" ]\n'
            '  GOOD: [ "$result" = "SUCCESS" ]\n'
            "\nFix legacy gh pr commands with canonical placeholder form, e.g.:\n"
            "  BAD:  gh pr checks {pr} --repo {repo}\n"
            "  BAD:  gh pr checks --watch\n"
            "  GOOD (own PR):       gh pr checks ${PR_NUMBER} --repo ${REPO}\n"
            "  GOOD (cross-PR pin): gh pr checks 1721 --repo OmniNode-ai/omnimarket"
            "  (standalone hardcoded PR + literal --repo, NO ${PR_NUMBER}"
            " anywhere in the value)\n"
            "  BAD (OMN-14431):     PR_NUMBER=1721 REPO=org/repo gh pr checks"
            " ${PR_NUMBER} --repo ${REPO}  (the ${PR_NUMBER} token is"
            " pre-substituted with the runner's OWN PR before the assignment"
            " could ever apply -- the 1721 literal is silently discarded)\n"
            "\nFix tautological self-comparisons (OMN-15391 Rule C):\n"
            "  BAD:  gh pr view 5408 --repo O/R --json number"
            " --jq '.number == 5408' | grep -qx true   (asserts N == N)\n"
            "  GOOD: gh api repos/O/R/pulls/5408/files --paginate"
            " --jq '.[].filename' | grep -qx 'contracts/OMN-14979.yaml'\n"
            "\nFix fail-open absence controls (OMN-15391 Rule D):\n"
            "  BAD:  gh api '...?ref=PARENT' | grep -c 'MARKER' | grep -qx 0"
            "   (a failed fetch prints 0 and passes)\n"
            "  GOOD: body=$(gh api '...?ref=PARENT')"
            " && printf '%s' \"$body\" | grep -qF 'ANCHOR'"
            " && ! printf '%s' \"$body\" | grep -qF 'MARKER'\n"
            "  GOOD (path absent at parent): gh api 'repos/O/R/commits/PARENT'"
            " --jq '.sha' | grep -qx 'PARENT'"
            " && ! gh api 'repos/O/R/contents/FILE?ref=PARENT' --silent\n"
            "\nFix predicates pinned to MUTABLE state (OMN-15540 Rule F):\n"
            "  BAD:  gh api repos/O/R/actions/runs/30565261108/jobs"
            " --jq '...|.conclusion' | grep -qx failure"
            "   (a re-run rewrites the conclusion -- permanent BLOCK)\n"
            "  GOOD: assert a receipt under drift/dod_receipts/ that RECORDED"
            " the conclusion, or assert a monotone property of the run\n"
            "  BAD:  gh api '...?ref=user/omn-1234-my-feature'"
            "   (the head branch is deleted on merge -- 404s forever)\n"
            "  GOOD: gh api '...?ref=<squash-commit-sha-on-dev>'\n"
            "  BAD:  COUNT=\"$(gh api 'search/issues?q=...' --jq .total_count)\""
            ' && [ "$COUNT" -eq 2 ]'
            "   (the set only grows -- the next re-mint falsifies it)\n"
            "  GOOD: anchor the query to a closed window"
            " (`created:A..B`), scope it `is:open`, or assert `>= N`\n"
            "\nRun: uv run python scripts/migrate_dod_contracts.py"
            " --apply --tickets <ID>"
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
