# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Contract-compliance check primitives, ported from onex_change_control (OMN-17427).

The pure, side-effect-free half of ``onex_change_control``'s
``src/onex_change_control/scripts/contract_compliance_check.py`` (pinned at
6adc28168d023d027bf9c1172f262ac03c9d9055): the admissibility verdict of one
check (``is_inert_check``), the non-hermetic guard (``non_hermetic_reason``) and
the runner's token substitution (``substitute_tokens`` /
``validate_substitution_context``). The bodies are copied unchanged so the
port answers exactly as the original; ``tests/unit/handlers/
test_occ_contract_checks_parity.py`` holds the two together on a recorded
corpus. The executing runner itself (subprocess, gh, credential preflight) is
not ported here.
"""

from __future__ import annotations

import re
import shlex

from omnibase_core.handlers.handler_evidence_admissibility import (
    EXECUTED_HERMETIC_COMMANDS,
    LIVE_PROBE_COMMANDS,
    AdmissibilityVerdict,
    classify_evidence_item,
)
from omnibase_core.models.configuration.model_network_defaults import (
    ModelNetworkDefaults,
)
from omnibase_core.models.nodes.contract_evidence_check.model_contract_compliance_check_request import (
    ModelContractComplianceCheckRequest,
)
from omnibase_core.models.nodes.contract_evidence_check.model_contract_compliance_check_verdict import (
    ModelContractComplianceCheckVerdict,
)

__all__ = [
    "HandlerContractComplianceCheck",
    "is_inert_check",
    "non_hermetic_reason",
    "substitute_tokens",
    "validate_substitution_context",
]

_REPO_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")

# OMN-15309 -- admissibility is decided by ONE predicate, shared with deploy-gate.
#
# Operator ruling 2026-07-29: the OMN-14505 deploy-gate falsifiability predicate
# (EXECUTED, FALSIFIABLE, OUTSIDE ITS OWN DIFF) is THE admissibility rule for
# evidence everywhere. It lives in
# ``onex_change_control.validation.evidence_admissibility`` and is adopted from
# ``omniclaude/.github/actions/deploy-gate/validate_pr_deploy_required.py``
# (``classify_check_value``), which remains the cited source; the two are held
# in parity by execution against a shared corpus (tests/data/
# evidence_admissibility_cases.yaml, run against BOTH implementations by the
# ``predicate-parity`` step of the contract-compliance CI job).
#
# History this replaces, and why the replacement is strictly larger:
#   OMN-14436 introduced two regexes (``drift/dod_receipts/`` and
#   ``contracts/OMN-``) to catch checks that could only observe the OCC store,
#   after finding the runner's ``--workspace`` had been mis-pointed at the OCC
#   clone so the receipt was the only file a check could reach (~32% of the
#   corpus grepped exactly those paths). Those two regexes are the DENY half of
#   the predicate and are preserved verbatim inside it. What they never caught,
#   and the predicate does, is the rest of the same disease: a probe name
#   appearing as *quoted text* beside a circular grep, an ``echo``/``true``
#   whose exit status the author fixed by typing it, a ``test -f`` on a path the
#   PR itself adds, and a grep whose every path operand is a file this same
#   change writes. All of those "observe the product" under the old regexes and
#   still prove nothing.
#
# The word INERT is retained for the verdict label and the demotion machinery
# (see ``_demote`` / ``_has_effective_check``) so the ratchet's blast radius is
# unchanged in SHAPE: an inadmissible check is reported loudly and demoted to
# WARN so it can never gate, and it is never allowed to produce a PASS that
# would launder a red PR into green evidence (the OMN-14391 /
# omnibase_infra#2264 case). Legacy content-pinned contracts stay grandfathered;
# a NEW or touched contract is held to the real bar from its first PR.
#
# This runner EXECUTES check_value, so its ALLOW vocabulary is the live-probe
# set PLUS commands that genuinely run against the product checkout in CI. A
# text-only consumer (deploy-gate, which never executes) passes the live set
# alone. That single parameter is the ONLY difference between consumers -- the
# DENY half and the command-position analysis are identical.
_RUNNER_ADMISSIBLE_PROBES: frozenset[str] = (
    LIVE_PROBE_COMMANDS | EXECUTED_HERMETIC_COMMANDS
)


def _classify_check(
    check_value: object,
    changed_paths: frozenset[str] | None = None,
    check_type: str = "command",
) -> AdmissibilityVerdict:
    """Apply the single admissibility predicate to one dod_evidence check."""
    return classify_evidence_item(
        check_type,
        check_value,
        admissible_probes=_RUNNER_ADMISSIBLE_PROBES,
        changed_paths=changed_paths,
    )


def _is_inert_check(
    check_value: object,
    changed_paths: frozenset[str] | None = None,
    check_type: str = "command",
) -> bool:
    """True if the check is INADMISSIBLE under the OMN-15309 predicate.

    Inadmissible means at least one of the three required properties is missing:
    it does not execute, it cannot go RED, or everything it reads is authored by
    this same change. Such a check is structurally incapable of saying anything
    about the product repo the PR actually changes.
    """
    return not _classify_check(check_value, changed_paths, check_type).admissible


# OMN-14051 -- non-hermetic check_value guard (reject at validation time).
#
# A dod_evidence check of check_type "command" has its check_value executed
# verbatim by this runner inside the CI environment. CI runners have no ssh, no
# route to the .201 Tailscale/LAN hosts, and no live docker/k8s daemon, so a
# command that shells out to ssh/scp, a live container daemon, or network egress
# to a non-loopback host can NEVER pass in CI -- it BLOCKs the PR with a cryptic
# runtime error ("sh: 1: ssh: not found", exit 127) even when the underlying
# work is real. Observed on OCC PR #3642 (OMN-14001): a `dod-deploy-scope` item
# inlined `ssh <user>@<lab-host-ip> "docker ps ..."` and produced
# "3/4 PASS, 1 BLOCK".
#
# OMN-15309 CORRECTION -- this block used to prescribe exactly the shape the
# same file unconditionally refuses to credit:
#
#   check_value: >-
#     grep -q '^status: PASS$'
#     "$CONTRACT_REPO_DIR/drift/dod_receipts/<TICKET>/<evidence-id>/command.yaml"
#
# Following that instruction produced a permanent WARN and could never produce a
# PASS: the OMN-14051 guard rejected the inline live probe, and the OMN-14436
# INERT rule demoted the receipt grep the guard told the author to write
# instead. Three surfaces rejected the same shape on 2026-07-28 (deploy-gate's
# annotation on omnimarket#1927, this evaluator's demotion, and this comment
# prescribing it), which is why the contradiction was filed rather than patched.
#
# The admissible hermetic form for a fact this runner cannot probe live is a
# CONTENT READ AT A PINNED REF against the product repo -- executed on any CI
# runner, falsifiable, and outside the diff the evidence author writes:
#
#   check_value: >-
#     gh api repos/OWNER/REPO/contents/<changed_path>?ref=<merge_sha>
#     --jq .content | base64 -d | grep -q '<symbol the fix introduces>'
#
# `gh` is deliberately absent from the deny lists below for exactly this reason.
# See ``admissible_evidence_guidance()`` in
# ``onex_change_control.validation.evidence_admissibility`` for the full set of
# admissible shapes per evidence class -- that function is the single author-
# facing text, and it is what this runner prints on refusal.
#
# This guard rejects the non-hermetic form up front with that actionable
# message, so the failure surfaces at authoring/validation time instead of as a
# late, cryptic CI error. It is folded into the *existing* validator (no new
# gate/workflow -- net-negative-surface) and is subject to the same OMN-14436
# demotion rules as any other BLOCK: a grandfathered (content-pinned legacy)
# contract is demoted to WARN -- so the pre-existing corpus of `docker exec`
# runtime-proof checks is reported but not wedged -- while a NEW or touched
# contract is enforced from its first PR.
#
# Detection is deliberately conservative (per the ticket: "start conservative,
# expand as needed"). Known gap: a binary hidden inside a command substitution
# (`$(ssh ...)`) is not yet detected; only command-position invocations are.
_MAX_SNIPPET_LEN = 160

# Shell tokens that begin a new command word (so the next token is in command
# position). shlex emits these as standalone tokens when whitespace-separated.
_SHELL_OPERATORS: frozenset[str] = frozenset(
    {"|", "||", "&&", ";", ";;", "&", "|&", "(", ")", "{", "}"}
)
# Command wrappers whose *argument* is the real command; stay in command
# position past them (and past `env FOO=bar` assignment tokens).
_WRAPPER_BINS: frozenset[str] = frozenset(
    {"sudo", "env", "time", "nice", "nohup", "command", "exec", "xargs", "then", "do"}
)
# Remote shell / remote copy: always non-hermetic.
_REMOTE_SHELL_BINS: frozenset[str] = frozenset(
    {"ssh", "scp", "sftp", "rsync", "telnet"}
)
# Container / orchestration: need a live daemon absent from CI runners.
_DAEMON_BINS: frozenset[str] = frozenset(
    {"docker", "docker-compose", "podman", "nerdctl", "kubectl"}
)
# Network fetch: non-hermetic only when the target host is not loopback.
_NET_FETCH_BINS: frozenset[str] = frozenset({"curl", "wget", "nc", "ncat"})

_ASSIGNMENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
# Full-octet IPv4 in the private / Tailscale-CGNAT ranges. Anchored to a
# complete dotted quad so version strings ("10.2") never match.
_LAN_IP_RE = re.compile(
    r"\b("
    r"192\.168\.\d{1,3}\.\d{1,3}"
    r"|10\.\d{1,3}\.\d{1,3}\.\d{1,3}"
    r"|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}"
    r"|100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.\d{1,3}\.\d{1,3}"
    r")\b"
)
_URL_HOST_RE = re.compile(r"https?://([^/\s]+)")
_LOOPBACK_HOSTS: frozenset[str] = ModelNetworkDefaults.load().loopback_hosts_with_alias


def _command_binaries(command: str) -> list[str]:
    """Basenames of the binaries invoked in command position in ``command``.

    Quote-aware via ``shlex`` so a binary name embedded in a quoted argument --
    e.g. the word "docker" in ``grep -q 'no docker exec' file`` -- is NOT
    reported; only tokens that actually start a command word are. Shell
    operators (``;`` ``&&`` ``||`` ``|``) and wrappers (``sudo``, ``env VAR=x``)
    keep the scan in command position.
    """
    try:
        tokens = shlex.split(command, posix=True)
    except ValueError:
        # Unbalanced quotes etc. -- best-effort whitespace split rather than
        # silently passing the guard on a malformed command.
        tokens = command.split()
    binaries: list[str] = []
    expect_command = True
    for token in tokens:
        if token in _SHELL_OPERATORS:
            expect_command = True
            continue
        if not expect_command:
            continue
        if _ASSIGNMENT_RE.match(token):
            # `env FOO=bar cmd` -- leading assignments are not the command.
            continue
        binary = token.rsplit("/", 1)[-1]
        if binary in _WRAPPER_BINS:
            continue  # stay in command position; the next token is the command
        binaries.append(binary)
        expect_command = False
    return binaries


def _is_loopback_host(host: str) -> bool:
    """True if ``host`` (optionally ``user@host:port``) is a loopback target."""
    text = host.strip().strip("\"'[]").lower()
    if "@" in text:
        text = text.rsplit("@", 1)[1]
    if text.startswith("127.") or text in _LOOPBACK_HOSTS:
        return True
    return text.split(":", 1)[0] in _LOOPBACK_HOSTS


def _has_nonloopback_url(command: str) -> bool:
    """True if ``command`` contains an http(s) URL whose host is not loopback."""
    return any(not _is_loopback_host(h) for h in _URL_HOST_RE.findall(command))


def _non_hermetic_message(reason: str, command: str) -> str:
    """Actionable rejection message steering the author to the receipt pattern."""
    snippet = (
        command
        if len(command) <= _MAX_SNIPPET_LEN
        else command[:_MAX_SNIPPET_LEN] + "..."
    )
    return (
        f"NON-HERMETIC check_value -- {reason}. A CI runner has no ssh, no route "
        "to the .201/LAN/Tailscale hosts, and no live docker/k8s daemon, so this "
        "command can never pass in CI (OMN-14051); it would BLOCK the PR with a "
        "cryptic runtime error even when the work is real. Run the live probe out "
        "of band, record it in a committed receipt "
        "(drift/dod_receipts/<TICKET>/<evidence-id>/command.yaml with fields "
        "probe_command, probe_stdout, exit_code, status: PASS), then set the "
        "contract check to grep that receipt:\n"
        "  check_value: >-\n"
        "    grep -q '^status: PASS$'\n"
        '    "$CONTRACT_REPO_DIR/drift/dod_receipts/<TICKET>'
        '/<evidence-id>/command.yaml"\n'
        f"  offending check_value: {snippet}"
    )


def _non_hermetic_reason(check: object) -> str | None:
    """Rejection message if ``check``'s command check_value is non-hermetic, else None.

    "Non-hermetic" == the command depends on ssh/remote-copy, a live
    docker/k8s daemon, or network egress to a non-loopback host -- none of which
    exist on a CI runner. Returns ``None`` for a hermetic command (local file
    assertions, receipt greps, pure compute, loopback probes) so those still run.

    Only executed shell checks (``check_type: command`` and ``test_passes``)
    are inspected. grep / file_exists / test_exists check_values are file/glob
    assertions that may legitimately *contain* an IP or the word "docker"
    (e.g. grepping a committed config), so scanning them would be a
    false-positive machine.
    """
    if not isinstance(check, dict) or check.get("check_type") not in {
        "command",
        "test_passes",
    }:
        return None
    command = str(check.get("check_value", ""))
    if not command.strip():
        return None

    binaries = _command_binaries(command)
    for binary in binaries:
        if binary in _REMOTE_SHELL_BINS:
            return _non_hermetic_message(
                f"invokes the remote-access binary {binary!r}", command
            )
        if binary in _DAEMON_BINS:
            return _non_hermetic_message(
                f"invokes {binary!r}, which needs a live container/orchestration "
                "daemon that CI runners do not have",
                command,
            )
    lan_ip = _LAN_IP_RE.search(command)
    if lan_ip is not None:
        return _non_hermetic_message(
            f"references the non-routable LAN/Tailscale host {lan_ip.group(1)!r}",
            command,
        )
    for binary in binaries:
        if binary in _NET_FETCH_BINS and _has_nonloopback_url(command):
            return _non_hermetic_message(
                f"performs network egress via {binary!r} to a non-loopback host",
                command,
            )
    return None


def _substitute_tokens(
    cmd: str,
    pr_number: int,
    repo: str,
    ticket_id: str,
) -> str:
    """Substitute templating tokens in a check command.

    Two complementary placeholder forms are supported so contract YAML can
    pick whichever reads best:

    * ``{pr}``, ``{repo}``, ``{ticket_id}`` — runner-level substitution that
      happens before ``sh -c`` is invoked (safe in any shell context, including
      single-quoted strings).
    * ``${PR_NUMBER}``, ``${REPO}``, ``${TICKET_ID}`` — shell-style placeholders
      that ALSO get pre-substituted here so they work in single-quoted strings
      (where ``sh -c`` would not expand them). The same names are exported as
      env vars by the caller, so unquoted ``${PR_NUMBER}`` references in
      double-quoted strings keep working too.

    Pre-substitution is preferred over relying solely on env-var expansion
    because a contract author that writes ``'gh pr checks ${PR_NUMBER}'`` (with
    single quotes) would otherwise see the literal token reach ``gh``.
    """
    return (
        cmd.replace("{pr}", str(pr_number))
        .replace("{repo}", repo)
        .replace("{ticket_id}", ticket_id)
        .replace("${PR_NUMBER}", str(pr_number))
        .replace("${REPO}", repo)
        .replace("${TICKET_ID}", ticket_id)
    )


def _validate_substitution_context(
    cmd: str, pr_number: int, repo: str, ticket_id: str
) -> str | None:
    """Reject unsafe or incomplete values before shell substitution.

    Placeholder values are inserted into a command before ``bash -c`` runs it.
    The normal CI call supplies a positive integer PR, an ``org/repo`` slug and
    an ``OMN-<number>`` ticket, so validating those shapes keeps the historical
    placeholder contract while preventing shell metacharacters from entering
    the command through runner context.
    """
    if ("${PR_NUMBER}" in cmd or "{pr}" in cmd) and (
        not isinstance(pr_number, int) or pr_number <= 0
    ):
        return "Invalid PR number for command placeholder"
    if ("${REPO}" in cmd or "{repo}" in cmd) and not _REPO_PATTERN.fullmatch(repo):
        return "Invalid repository for command placeholder"
    if ("${TICKET_ID}" in cmd or "{ticket_id}" in cmd) and not re.fullmatch(
        r"OMN-[0-9]+", ticket_id
    ):
        return "Invalid ticket ID for command placeholder"
    return None


# Public names. The underscore spellings above are kept so the bodies stay
# byte-identical to the original and a reader can diff them against it.
is_inert_check = _is_inert_check
non_hermetic_reason = _non_hermetic_reason
substitute_tokens = _substitute_tokens
validate_substitution_context = _validate_substitution_context


class HandlerContractComplianceCheck:
    """Classify one dod_evidence check: inert or not, hermetic or not."""

    def handle(
        self, request: ModelContractComplianceCheckRequest
    ) -> ModelContractComplianceCheckVerdict:
        """Return the inert verdict and the non-hermetic reason of the check."""
        changed = (
            frozenset(request.changed_paths)
            if request.changed_paths is not None
            else None
        )
        return ModelContractComplianceCheckVerdict(
            inert=_is_inert_check(request.check_value, changed, request.check_type),
            non_hermetic_reason=_non_hermetic_reason(
                {"check_type": request.check_type, "check_value": request.check_value}
            ),
        )
