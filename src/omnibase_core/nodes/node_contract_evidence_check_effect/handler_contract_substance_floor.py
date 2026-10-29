# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Contract substance floor (OMN-14409).

A ticket contract must declare at least one dod_evidence check that could
*fail if the work were wrong*. A check that only proves the PR object exists
(``gh pr view <n> --json number,state``) establishes binding, not correctness:
it passes identically whether the code is right or catastrophically broken.

The live defect this gate closes
--------------------------------
The Evidence-Source autobind (OMN-13317 F1) mints a contract when a product PR
fails the Receipt Gate, and then mints the receipts that satisfy it — so it
authors *both the bar and the proof*. ``contracts/OMN-14400.yaml`` is the live
instance: every one of its autobind-declared checks is a ``gh pr view`` probe.
Every gate passed. The receipt did not lie and the receipt-gate was not broken —
the contract simply set a bar that nothing about the work had to clear.

Nothing in the chain required a ticket's DoD to be *related to the work the
ticket did*. This gate is that requirement.

Policy
------
Each dod_evidence check is mapped to the :class:`EnumProofTier` it can actually
establish (see :func:`derive_proof_tier`). A contract PASSES when at least one
check reaches **L1 or above**. Existence probes derive to **L0** and therefore
can never satisfy the floor on their own.

Binding/stamp items keep working
--------------------------------
This gate does NOT reject existence probes, and does NOT touch receipt
``status``. Evidence-Source binding items (``occ-self-bind-pr-*`` and the
autobind's ``gh pr view`` probes) remain completely valid for the job they
exist to do — stamping the Evidence-Source line. They simply do not *count*
toward the substance floor. A contract carrying a substantive item plus any
number of binding items passes. The autobind stamp path is therefore rejected
at a rate of exactly zero; only a DoD consisting *entirely* of existence probes
fails.

Independence, without touching receipt status
---------------------------------------------
"An automated producer may not supply the substantive proof" is enforced
structurally rather than by identity comparison: the autobind emits only
existence probes, which derive to L0 and can never be substantive. This
deliberately avoids the ``verifier``/``runner`` PASS→ADVISORY downgrade — the
receipt gate treats ADVISORY as FAIL, so that approach would fail every
autobind receipt and kill the stamp path (OMN-14409 analysis, M4).

Reuses the existing OMN-13338 vocabulary (``EnumProofTier``); introduces no
second proof taxonomy.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from omnibase_core.enums.ticket.enum_proof_tier import EnumProofTier
from omnibase_core.models.nodes.contract_evidence_check.model_contract_substance_floor_report import (
    ModelContractSubstanceFloorReport,
)
from omnibase_core.models.nodes.contract_evidence_check.model_contract_substance_floor_request import (
    ModelContractSubstanceFloorRequest,
)
from omnibase_core.models.nodes.contract_evidence_check.model_contract_substance_floor_verdict import (
    ModelContractSubstanceFloorVerdict,
)
from omnibase_core.nodes.node_contract_evidence_check_effect.substance_floor_finding import (
    CheckFinding,
)
from omnibase_core.nodes.node_contract_evidence_check_effect.substance_floor_result import (
    ContractResult,
)

# `gh pr view --json <fields>` restricted to these fields reads pure object
# metadata: it proves the PR record exists and what state it is in. It cannot
# discriminate correct code from broken code, so it derives to L0.
_EXISTENCE_JSON_FIELDS = frozenset(
    {
        "number",
        "state",
        "url",
        "title",
        "body",
        "headrefname",
        "headrefoid",
        "baserefname",
        "author",
        "isdraft",
        "mergedat",
        "createdat",
        "updatedat",
        "closedat",
        "mergeable",
        "mergestatestatus",
        "mergecommit",
    }
)

# COMMAND POSITION. A bare verb token must be *invoked*, not merely mentioned
# inside a path or argument. This anchor is the load-bearing lesson of this file.
#
# `\b` is NOT sufficient: `.` is a non-word character, so `\bsh\b` matches the
# EXTENSION in `scripts/verify.sh`, and `\bmake\b` / `\bdiff\b` match path
# SEGMENTS like `src/make/build.py` or `docs/diff/report.md`. `.sh` is the most
# common script extension in this repo, so an unanchored `sh` silently accepted
# every `gh api .../contents/*.sh` file-exists probe as if it were a real script
# run. The same bug was first caught on `onex` (path segment, via the ratchet on
# OMN-11220) — that instance was fixed without generalizing to its siblings.
#
# A verb counts at the start of the command, after a pipe/semicolon/&&/||, inside
# a `$(...)`, after a shell keyword (`then`/`do`/`else` — these ARE command
# position), or as the argument of a runner (`uv run X`, `exec X`, `xargs X`).
#
# `then`/`do` matter: omitting them silently gated a SUBSET of the circular
# self-attestation class (`if test -f …; then grep -q 'status: PASS' <own
# receipt>`), which GATE_SELF_REFERENTIAL deliberately leaves ungated. A partial,
# accidental activation of a class we consciously deferred is worse than either
# gating it or not — it makes the policy incoherent.
_CMD = r"(?:^|[|;&]\s*|\$\(\s*|\b(?:run|exec|xargs|sudo|time|env|then|do|else)\s+)"

# Probes that read live runtime state — they establish L2 (the change is live),
# not merely that it merged.
_RUNTIME_PROBE_RE = re.compile(rf"{_CMD}(kubectl|docker|psql|rpk|curl|httpx|wget)\b")

# Probes that execute the test suite — they establish L1 (the changed behavior
# is exercised).
_TEST_PROBE_RE = re.compile(
    rf"{_CMD}(pytest|vitest|jest|tox)\b|\b(npm\s+test|go\s+test|cargo\s+test|make\s+test)\b"
)

# Probes that read a real CI verdict for the PR — falsifiable: they fail when CI
# fails. `gh pr view --json statusCheckRollup` carries the same signal.
_CI_OUTCOME_RE = re.compile(
    r"(\bgh\s+(pr\s+checks|run\s+view)\b|statusCheckRollup)", re.IGNORECASE
)

# Static assertions over SOURCE — a grep/rg that pins a symbol or line in the
# tree is falsifiable about the change (it fails if the code is not there).
_STATIC_ASSERT_RE = re.compile(rf"{_CMD}(grep|rg|ast-grep)\b")

# Type/lint/gate runs. All fail on bad code.
_ANALYSIS_RE = re.compile(
    rf"{_CMD}(pre-commit|mypy|ruff|pyright|eslint|tsc|import-linter|lint-imports)\b"
)

# Executing a program, script, or assertion — the general falsifiable family.
#
# The test is FALSIFIABILITY, not membership in a hand-curated list: a check is
# substantive if it CAN FAIL when the work is wrong. `diff -u expected actual`
# fails when the output is wrong. `jq -e` fails when the assertion is false.
# `make verify` fails when the target fails. `uv run validate-yaml` — OCC's own
# canonical validator — fails when the contract is malformed. These are exactly
# the checks we want authors writing, so this matcher is deliberately GENEROUS.
#
# A too-narrow allowlist here is not friction, it is a PERVERSE INCENTIVE:
# rejecting `diff` while accepting a self-referential `grep 'status: PASS'`
# (which GATE_SELF_REFERENTIAL currently permits) would push authors away from
# real evidence and toward the circular pattern this gate exists to eliminate —
# manufacturing the very debt OMN-14417 tracks. When in doubt, ACCEPT: a false
# accept costs one weak receipt; a false reject teaches authors that writing
# honest evidence does not pay.
#
# Every bare verb below is anchored to command position (see _CMD).
_EXECUTABLE_RE = re.compile(
    rf"""(
          ^\s*\.{{0,2}}/\S+                      # ./verify.sh, /usr/bin/x, ../y
        | {_CMD}(bash|sh|zsh|make|just|task)\b               # shells + task runners
        | {_CMD}(python3?|node|deno|ruby|perl)\b             # interpreters
        | {_CMD}(uv|poetry|npm|npx|pnpm|yarn)\b              # package runners
        | {_CMD}onex\b                                       # ONEX CLI
        | {_CMD}(validate-[\w-]+|check-[\w-]+|scan-[\w-]+|verify-[\w-]+)\b  # OCC
        | \bjq\s+-\w*e\b                         # `jq -e`: the -e flag IS the assert
        | {_CMD}(diff|cmp)\b                                 # output comparison
    )""",
    re.VERBOSE,
)

# `gh api .../contents/<path>` is a file-EXISTS read over the GitHub API — the
# same family as `gh pr view`. It proves a file is present in a repo; it passes
# identically whether the code is correct or broken. Rejected outright rather
# than relying on the verb anchor, because its URL path is adversarially shaped:
# it routinely contains `.sh`, `make`, `diff`, `onex` — exactly the tokens a verb
# matcher trips over. Rejecting the command is durable; whack-a-mole on its path
# contents is not.
#
# Matched as a WHOLE command (fullmatch), never as a substring. Two compounds
# proved a blanket `gh api` reject does real damage:
#
#   * `gh api .../pulls/<n>/files --jq '.[].filename' | grep -cE '<pat>'`
#     — a genuine DIFF ASSERTION (fails when the PR doesn't touch those files).
#   * `if test -f <r>; then grep -q PASS <r>; else gh api .../contents/<r>
#     --jq .content | base64 -d | grep -q PASS; fi`
#     — the circular class, which GATE_SELF_REFERENTIAL deliberately leaves
#     ungated; rejecting it here would partially activate a deferred policy.
#
# The verb ANCHOR is what actually closes the path-token hole (`.sh`, `make`,
# `diff`, `onex` inside a URL are no longer in command position), and a bare
# `gh api .../pulls/1` still derives L0 via the default-reject branch. This rule
# is therefore a narrow, explicit statement of intent, not the load-bearing fix.
# The optional value token excludes anything that starts a flag, so a flag
# followed by a flag parses only one way (the original `(\s+\S+)?` let a
# `--a --b` tail split two ways inside the repeated group). Same language.
_GH_API_CONTENTS_RE = re.compile(
    r"\s*gh\s+api\s+\S*contents/\S*(?:\s+--\S+(?:\s+(?!--\S)\S+)?)*\s*"
)

# A diff assertion: `gh pr view --json files --jq '[.files[].path]'` names the
# files the PR must touch. It is falsifiable about the change (it fails if the
# diff is not what was claimed), so it is substantive — NOT an existence probe.
_DIFF_ASSERT_RE = re.compile(r"(--json[=\s]+[^|]*\bfiles\b|\.files\[)")

_GH_PR_VIEW_RE = re.compile(r"\bgh\s+pr\s+view\b")
_JSON_FLAG_RE = re.compile(r"--json[=\s]+([A-Za-z0-9_,]+)")

# ---------------------------------------------------------------------------
# Content-free probe families — all derive L0 (cannot satisfy the floor).
# ---------------------------------------------------------------------------

# The no-op family: commands that pass unconditionally. `check_value: "true"`
# is not evidence of anything; it is an unconditional PASS with extra steps.
_NO_OP_RE = re.compile(
    r"""^(
          true | : | exit\s+0 | echo(\s|$).* | printf(\s|$).* |
          ls(\s+[^|;&]*)? | pwd | test\s+-[fed]\s+\S+ | \[\s+-[fed]\s+\S+\s+\]
        )$""",
    re.VERBOSE,
)

# Self-referential: the probe reads the receipt corpus — i.e. its OWN evidence.
#     grep -q '^status: PASS$' drift/dod_receipts/OMN-XXXX/dod-001/command.yaml
# The receipt says PASS because the agent wrote PASS; the check confirms the
# agent wrote PASS. Circular by construction; it establishes nothing about the
# work. This is the OMN-14417 class.
_SELF_REFERENTIAL_RE = re.compile(r"drift/dod_receipts/")

# OMN-14417 KILL SWITCH — deliberately OFF.
#
# Deriving the self-referential class to L0 is correct, and it is a one-line
# flip. It is off because the pattern is not merely legacy debt — it is the
# CURRENT house style. Re-measured 2026-07-12 in a clean env against the pinned
# omnibase-core 0.46.7 wheel, with the deriver as it ships here:
#
#   flag OFF (shipped) ->   120 / 6,916 rejected (1.74%) — ALL grandfathered,
#                           0 un-grandfathered, and 0 / 187 contracts created in
#                           the last 7 days blocked (0.0% forward).
#   flag ON            -> 2,277 / 6,916 rejected (32.9%), of which 2,157 are NOT
#                           grandfathered, and 184 / 187 new contracts blocked
#                           (98.4% forward; an independent sweep over a slightly
#                           wider window measured 190/190 = 100%).
#
# Grandfathering does NOT rescue the ON case: at a ~100% forward rate the gate
# would reject essentially all new contract traffic, which is the
# reject-everything trap this ticket exists to avoid. The generator must be
# fixed first (OMN-14417 asks exactly that); then flip this to True and the
# substance floor gates the circular class with no further code change.
GATE_SELF_REFERENTIAL = False


def _is_existence_probe(command: str) -> bool:
    """Return True when ``command`` can only prove that the PR object exists.

    A ``gh pr view`` that requests *only* metadata fields is an existence probe.
    The same command requesting ``statusCheckRollup`` (CI outcome) or reviews is
    NOT — those fields say something falsifiable about the change, so they are
    left to derive a higher tier.
    """
    if not _GH_PR_VIEW_RE.search(command):
        return False

    fields: set[str] = set()
    for match in _JSON_FLAG_RE.finditer(command):
        fields.update(f.strip().lower() for f in match.group(1).split(",") if f.strip())

    # `gh pr view <n>` with no --json at all prints the PR body/metadata: still
    # pure existence.
    if not fields:
        return True

    # Any field outside the metadata set (e.g. statusCheckRollup) carries real
    # signal about the change — not an existence probe.
    return fields.issubset(_EXISTENCE_JSON_FIELDS)


def derive_proof_tier(check_type: str, check_value: str) -> EnumProofTier:
    """Map a dod_evidence check to the :class:`EnumProofTier` it can establish.

    This is the input the OMN-13338 tier apparatus never had. ``proof_packet``
    is populated on 0 of 10,164 live receipts, so a gate requiring a
    hand-authored packet is unsatisfiable. ``check_value`` is present on every
    check, so the tier can be *derived* rather than authored — no new authoring
    burden, and the existing tier vocabulary becomes operable.
    """
    command = (check_value or "").strip()

    # --- Content-free families: reject first, unconditionally. ---------------
    if not command:
        # No probe at all cannot establish anything.
        return EnumProofTier.L0

    if _NO_OP_RE.match(command):
        # `true`, `:`, `echo ok`, `exit 0`, bare `ls`, `test -f <path>`.
        # A command that cannot fail cannot be evidence.
        return EnumProofTier.L0

    if GATE_SELF_REFERENTIAL and _SELF_REFERENTIAL_RE.search(command):
        # Reads its own receipt. Circular (OMN-14417). Off by default — see the
        # kill-switch comment: ON rejects 98.4% of new contract traffic.
        return EnumProofTier.L0

    if _GH_API_CONTENTS_RE.fullmatch(command.strip()):
        # A WHOLE command that is nothing but a file-exists read over the API.
        # Compounds are deliberately excluded (see the regex comment).
        return EnumProofTier.L0

    if _is_existence_probe(command):
        # Proves the PR object exists; passes whether the code is right or not.
        return EnumProofTier.L0

    # --- Substantive families: an explicit allowlist. ------------------------
    if _RUNTIME_PROBE_RE.search(command):
        return EnumProofTier.L2

    substantive_shapes = (
        _TEST_PROBE_RE,
        _CI_OUTCOME_RE,
        _DIFF_ASSERT_RE,
        _STATIC_ASSERT_RE,
        _ANALYSIS_RE,
        _EXECUTABLE_RE,
    )
    if check_type == "test_passes" or any(
        shape.search(command) for shape in substantive_shapes
    ):
        return EnumProofTier.L1

    # --- Default: REJECT. ----------------------------------------------------
    # The polarity is deliberately inverted (OMN-14409 review): an unrecognized
    # command is NOT assumed substantive. Defaulting to L1 meant the floor read
    # as "any check that is not literally `gh pr view`" — which `true` satisfies.
    # A probe must be recognizably falsifiable to count as proof.
    return EnumProofTier.L0


def evaluate_contract(path: Path) -> ContractResult:
    """Evaluate one contract YAML against the substance floor."""
    raw = yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.SafeLoader) or {}
    result = ContractResult(path=path, ticket_id=str(raw.get("ticket_id") or path.stem))

    for item in raw.get("dod_evidence") or []:
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("id") or "<unnamed>")
        for check in item.get("checks") or []:
            if not isinstance(check, dict):
                continue
            check_type = str(check.get("check_type") or "")
            check_value = str(check.get("check_value") or "")
            result.findings.append(
                CheckFinding(
                    dod_item=item_id,
                    check_type=check_type,
                    check_value=check_value,
                    tier=derive_proof_tier(check_type, check_value),
                )
            )

    return result


class HandlerContractSubstanceFloor:
    """Judge the requested contracts against the proof-tier substance floor."""

    def handle(
        self, request: ModelContractSubstanceFloorRequest
    ) -> ModelContractSubstanceFloorReport:
        """Return one verdict per requested contract."""
        verdicts: list[ModelContractSubstanceFloorVerdict] = []
        for path in request.paths:
            result = evaluate_contract(path)
            verdicts.append(
                ModelContractSubstanceFloorVerdict(
                    path=path,
                    ticket_id=result.ticket_id,
                    passed=result.passed,
                    failure_message="" if result.passed else result.failure_message(),
                )
            )
        return ModelContractSubstanceFloorReport(verdicts=tuple(verdicts))
