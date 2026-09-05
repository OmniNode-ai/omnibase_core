#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
#
# Pre-push governed impacted-test selector (OMN-13973 / WS7 OMN-14655, D6a lane).
#
# Runs the FAST LOCAL IMPACTED SUBSET of the unit suite once per `git push`,
# using the SAME governed selector CI uses -- scripts/ci/detect_test_paths.py +
# scripts/ci/test_selection_adjacency.yaml -- NOT a hand-typed `-k`. The selector
# is fail-closed: it escalates to the full unit suite whenever it cannot prove
# narrowing is safe (a shared module, a dependency-bearing pyproject.toml change,
# a scripts/ci/ change, >=8 changed modules, or the main branch). See root
# CLAUDE.md Rule #4.
#
# This hook is deliberately NOT byte-parity with an enforced CI context. On CI the
# selector is gated behind ENABLE_SMART_TESTS (off by default during rollout) and
# the enforced merge gate is the FULL suite. This hook is *net-new, fast local
# subset enforcement* -- a fast local mirror that is ADVISORY of the full CI
# suite, run before the push leaves the machine. It retires the "run the whole
# suite by hand before every push" default (CLAUDE.md Rule #4: "until OMN-13973
# lands, the full local suite remains the fail-closed default").
#
# FAIL-LOUD (CLAUDE.md Rule #8; plan section 3d.4): if the diff base, the
# selector, or its adjacency config cannot resolve, this hook HARD-ERRORS with a
# remediation message and a non-zero exit. It never degrades to a green skip -- a
# gate that cannot run must be indistinguishable from a failing gate.
#
# CI-CONTRACT CLASS for `.github/**` diffs (OMN-16917, applying the OMN-16745
# ruling -- omnibase_infra#2988, docs/reference/selector-workflow-diff-ruling.md).
# A `.github/**` diff used to be unresolvable to the import graph, which failed
# the WHOLE selection closed to the `["tests/unit/"]` sentinel: a
# whole-suite-equivalent selection (split_count=39, 1,478 files) carrying
# `is_full_suite=false`, which the OMN-15408 predicate below then correctly
# routed into the OMN-15059 host-load guard. That escalation proved nothing --
# no test under tests/unit/ that never reads `.github/**` has an outcome a
# workflow YAML edit can change -- while consuming exactly the capacity the
# guard refuses pushes over. It is how OMN-16346 / OMN-16625 got stranded.
# The selector now resolves those paths to the CI-contract class instead: the
# tests that read `.github/**` off disk and assert its contents, plus any test
# module the diff itself touches. This is a SUBSTITUTION of proof, not a
# removal: the class may never select nothing (OMN-15541 -- a workflow edit can
# turn full-suite escalation itself fail-OPEN), and an empty or unenumerable
# class escalates. No env override, no allowlist to zero tests, no bypass token;
# the vars below are untouched and can still only make this hook run MORE tests.
#
# Env overrides (all optional):
#   PREPUSH_BASE_REF     git ref to diff against            (default: origin/dev)
#   PREPUSH_ADJACENCY    adjacency yaml path            (default: selector built-in)
#   PREPUSH_PYTEST_ARGS  extra args appended to the pytest invocation
#   ENABLE_SMART_TESTS   set false/0/off to force the FULL suite (parity with the
#                        CI var name); default here is smart selection ON, because
#                        the whole point of the local hook is the impacted subset.
#   PREPUSH_FULL_SUITE   set non-empty to force the FULL suite.

set -euo pipefail

log() { printf '[prepush-smart-tests] %s\n' "$1" >&2; }
die() {
  log "ERROR: $1"
  log "REMEDIATION: $2"
  exit 1
}

# =============================================================================
# Recursion guard (OMN-16489, F-01)
# =============================================================================
# This hook spawns pytest, and the spawned suite contains tests that exec THIS
# script again (tests/scripts/test_prepush_hook_host_identity_guard.py and
# siblings). OMN-16425 proved one leaked override var turns that re-entry into
# a recursive full-suite launcher (~9h03m lost across 5 failed ~1h45m runs;
# friction report F-01) — and its fix covered the test sites, not the hook.
# The env scrub at the pytest invocations below closes the override-
# inheritance vector; this sentinel closes the re-entry class itself: a nested
# invocation refuses fail-closed before the selector resolves or any pytest
# spawns. The sentinel deliberately survives the override scrub — children
# must inherit it for this guard to hold. A test that intends to exercise this
# script's FIRST-entry behavior must strip ONEX_PREPUSH_HOOK_ACTIVE from the
# subprocess env it constructs.
if [ -n "${ONEX_PREPUSH_HOOK_ACTIVE:-}" ]; then
  die "nested invocation refused: this hook is already active in an ancestor process (ONEX_PREPUSH_HOOK_ACTIVE=${ONEX_PREPUSH_HOOK_ACTIVE}, this pid $$)" \
      "a pre-push hook run must never be spawned from inside another pre-push hook run (OMN-16425 recursion class). If a test means to exercise first-entry behavior, construct the subprocess env explicitly and strip ONEX_PREPUSH_HOOK_ACTIVE"
fi
export ONEX_PREPUSH_HOOK_ACTIVE="$$"

# =============================================================================
# Inheritable env-var gate overrides are REJECTED AT ENTRY (OMN-16480)
# =============================================================================
# Ported to this repo by OMN-17159, and deliberately BEFORE the lab-dispatch
# picker below rather than after it. OMN-17159's own DoD names the ordering:
# porting the picker first would add a new PASS path to this gate with no entry
# rejection behind it, so the two land in the same commit with the rejection
# reachable first.
#
# This gate's escape hatch used to BE an environment variable
# (`PREPUSH_ALLOW_LOCAL_FULL_SUITE=1`). An environment variable is inherited by
# every descendant process, is bound to no repo/commit/run, never expires, and
# leaves no receipt -- so "permission to bypass the load gate once, for this
# push" was really "permission for every process this shell ever spawns to
# bypass this gate, silently". Same failure shape Rule 10 was hardened against
# for `[skip-*` tokens (OMN-9731 / OMN-13388), one layer down.
#
# Measured: on 2026-08-23 that variable leaked from an operator shell into a
# guard test's `env=dict(os.environ)` subprocess copy; the sibling hook took its
# degraded-override branch and recursively launched another full 44,064-test
# suite, which reached the same test and recursed again -- ~9h03m, ~72% of all
# serialized suite wall-clock in that window (friction report F-01/F-04).
# Compliance was PERFECT that night: zero `[skip-*`, zero `--no-verify`. The
# damage came from the sanctioned escape path being used correctly.
#
# So the variable is no longer an arming signal in either direction: its
# presence is a HARD REFUSAL, not a bypass. That is what makes inheritance
# harmless -- a leaked override can no longer arm anything, and it surfaces
# immediately instead of silently disarming the gate for a whole process tree.
# The supported path is a single-use, repo+HEAD-scoped, TTL-bounded, receipted
# grant token: scripts/hooks/prepush_override_grant.py.
#
# Matched by PREFIX, not by one exact name, so a future
# `PREPUSH_ALLOW_SOMETHING_ELSE` cannot quietly reopen the class.
reject_inherited_env_overrides() {
  local leaked
  leaked="$(env | sed -n 's/^\(PREPUSH_ALLOW_[A-Za-z0-9_]*\)=..*/\1/p' | sort -u | tr '\n' ' ')"
  leaked="${leaked% }"
  [ -n "$leaked" ] || return 0
  die "inheritable gate-override environment variable(s) present: ${leaked} -- these are REJECTED, never honored (OMN-16480)" \
      "unset them in this shell (e.g. \`unset ${leaked%% *}\`), then, if this run genuinely must proceed on this host, mint a scoped single-use grant: \`uv run python scripts/hooks/prepush_override_grant.py mint --reason '<why>'\`. The grant is bound to this repo and this HEAD sha, expires in minutes, is consumed by the first guard that reads it (so no child process can reuse it), and appends a receipt line to .onex_state/prepush_override/receipts.jsonl"
}
reject_inherited_env_overrides

# consume_override_grant CONTEXT -- 0 when a valid single-use grant was claimed
# for this run, 1 otherwise. Delegates to the one implementation
# (scripts/hooks/prepush_override_grant.py) that the pytest-side guard also
# uses, so the two entry points can never drift apart on what a valid grant is.
# Routed through `uv run` per the OMN-14953 pinned-interpreter gate.
consume_override_grant() {
  uv run python "${REPO_ROOT}/scripts/hooks/prepush_override_grant.py" \
    consume --context "$1"
}

# =============================================================================
# .200-default host guard for the heavy (full-suite) escalation (OMN-15059)
# =============================================================================
# CLAUDE.md documents that pushes / heavy gate runs default to the `.200`
# execution host, not the local Mac -- but a rule stated only in a doc/prompt
# has zero enforcement force without a call-site mechanism (memory
# feedback_a_rule_is_not_a_mechanism). Evidence this is load-bearing: a
# 2026-07-24 session drove the local Mac to load ~55 / 93% swap running this
# exact full-suite escalation for 115+ minutes before .200 was invoked as a
# rescue instead of having been the execution target from the start. This
# guard fires ONLY on the heavy branch below (full-suite fail-closed
# escalation), never on the fast impacted-subset path -- gating every push
# would get this hook disabled within a week, which is worse than no guard.
#
# An UNRESOLVABLE hostname fails CLOSED (OMN-16489 defect 3, redesign plan
# 2026-08-24 §4 S0 item 3 / C2 — supersedes the earlier fail-open note here).
# Heavy runs are routed BY host identity; a host that cannot be identified
# cannot be routed, and proceeding on that silence is the same assumed-
# headroom failure class as the load-probe incidents below. The refusal is
# cheap (<1s, before any pytest) and names its remediation, consistent with
# this hook's fail-loud doctrine: a gate that cannot run must be
# indistinguishable from a failing gate.
PREPUSH_200_HOSTNAME="${PREPUSH_200_HOSTNAME:-stickybeatz-studio}"

# =============================================================================
# Live-load host selection (OMN-16295)
# =============================================================================
# Extends the host-IDENTITY guard below with a CAPACITY dimension: `.200`
# being the right host by IDENTITY does not mean it has headroom. Measured
# 2026-08-20: `.200` load average 32-34 against 24 cores (and, live during
# this same investigation, 56/24 -- 2.3x oversubscribed) driving an 89-93
# minute full-suite run with orphaned pytest processes left behind. Same
# failure class as the 2026-07-24 incident described below, recurring under
# concurrent-session load. OMN-16295 adds a second execution target -- a
# hard-capped gate-runner container on `.201`
# (docker/docker-compose.gate-runner.yml in omnibase_infra), selected ONLY
# when `.200` is over threshold, never the default.
#
# FAIL-CLOSED, unlike the host-IDENTITY guard's fail-open posture below --
# deliberately different, not inconsistent. An unresolvable HOSTNAME is
# ambiguous evidence about WHERE we are (fail open: don't lock a developer out
# of their own repo on a shaky read). An unresolvable LOAD reading is a
# failure to prove EITHER candidate host has capacity, and proceeding anyway
# on that silence is exactly how the 2026-07-24 / 2026-08-20 incidents
# happened -- assumed headroom that was not there. "Neither host reachable"
# refuses; it does not skip the check.
PREPUSH_201_GATE_RUNNER_HOSTNAME="${PREPUSH_201_GATE_RUNNER_HOSTNAME:-gate-runner-201}"
PREPUSH_200_SSH_TARGET="${PREPUSH_200_SSH_TARGET:-jonah@stickybeatz-studio.tail75df5e.ts.net}"  # onex-allow-internal-ip OMN-16295 reason="pre-push guard needs the real host target to probe live load"
PREPUSH_201_SSH_TARGET="${PREPUSH_201_SSH_TARGET:-jonah@192.168.86.201}"  # onex-allow-internal-ip OMN-16295 reason="pre-push guard needs the real host target to probe live load" # fallback-ok: real .201 host target, not a dev/local placeholder
# load1/cores at or under this ratio counts as "fit". 1.0 == "not
# oversubscribed" (a standard load-average heuristic); correctly reads the
# observed-fit `.201` snapshot (~0.4x, 2026-08-20) as fit and both observed
# `.200` snapshots above (1.33x and 2.3x) as over threshold.
PREPUSH_LOAD_THRESHOLD="${PREPUSH_LOAD_THRESHOLD:-1.0}"

# Cross-platform (Linux `.201` / macOS `.200`) load probe, printing
# "<load1> <nproc>". Deliberately interpreter-free (OMN-17159, matching the
# OMN-16991 shape already shipped in omnibase_infra): the previous form here
# ran `python3 -c` on BOTH the local and the ssh branch, which this repo's own
# pinned-interpreter doctrine (OMN-14953) wants routed through `uv run` -- and
# the ssh branch cannot, because `.201` has no `uv` binary at all (probed
# 2026-08-20, re-probed 2026-08-31). Dropping the interpreter satisfies that
# constraint rather than carving an exception out of it, and keeps interpreter
# startup off the pre-push critical path. It also makes the probe usable on a
# host with no python3 on its non-interactive PATH, which is the normal shape
# of an ssh login session on the lab Macs.
#
# Two portability constraints, both load-bearing:
#   1. Field extraction uses cut(1), NOT `set -- $(...)` word splitting.
#      `.200`'s remote login shell is zsh, which does not word-split unquoted
#      command substitution, so `set --` would collapse the whole line into $1
#      there while working fine on `.201`'s bash.
#   2. This snippet is handed to ssh(1) as the remote command and executed by
#      whatever login shell the remote user has, so it stays POSIX and carries
#      no single quotes (it is itself a single-quoted assignment here).
# shellcheck disable=SC2016  # intentionally unexpanded: evaluated by the local
# `sh -c` / the remote login shell, not by this script.
_PREPUSH_LOAD_PROBE_SH='n=$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 0)
[ "$n" -gt 0 ] || exit 1
if [ -r /proc/loadavg ]; then
  l=$(cut -d" " -f1 /proc/loadavg)
else
  l=$(sysctl -n vm.loadavg 2>/dev/null | cut -d" " -f2)
fi
[ -n "$l" ] || exit 1
printf "%s %s\n" "$l" "$n"'

# Prefer GNU coreutils timeout(1); fall back to gtimeout(1) (Homebrew name on
# macOS); fall back to no wrapper at all (ssh -o ConnectTimeout already bounds
# the connection phase, and the remote command is a single fast shell probe).
_prepush_timeout_cmd() {
  if command -v timeout > /dev/null 2>&1; then
    printf 'timeout'
  elif command -v gtimeout > /dev/null 2>&1; then
    printf 'gtimeout'
  fi
}

# host_load_ratio TARGET -- prints "<load1> <nproc> <ratio>" and returns 0, or
# prints nothing and returns 1 on any read/parse/timeout failure. TARGET is
# empty for "read this host directly" or an ssh(1) target string for a
# bounded remote read. Deterministic, network-free overrides for tests (each a
# "<load1> <nproc>" pair -- the ratio is still computed from it, never
# hardcoded):
#   PREPUSH_LOAD_OVERRIDE_LOCAL   overrides the direct (TARGET="") read
#   PREPUSH_LOAD_OVERRIDE_REMOTE  overrides every ssh-target read
# `ssh -n` IS LOAD-BEARING, not hygiene (OMN-16991 verify finding 1, ported here
# by OMN-17159). This probe is called from inside the host-table row loop in
# pick_capacity_host, whose stdin is the row list. Without -n, ssh(1) reads and
# discards that stdin, so the FIRST probe swallows every remaining row and the
# picker evaluates exactly one host -- live, infra's picker probed h200 and
# never saw h201/h101/h105, and a lab with three idle hosts refused the push.
# The defect is silent: a truncated scan looks exactly like a small lab.
host_load_ratio() {
  local target="$1" raw load1 ncpu timeout_cmd
  # OMN-16995: REAP FIRST, MEASURE SECOND. A leaked no-op spin-loop orphan is
  # indistinguishable from real work in load1, and 19 of them once put `.200`
  # at 1.64x-core and refused every heavy escalation in the lab. The reaper is
  # defined in prepush_dispatch.sh, which is sourced below this definition and
  # therefore resolved by the time any caller runs.
  reap_spin_loop_orphans "$target" || true
  if [ -z "$target" ]; then
    if [ -n "${PREPUSH_LOAD_OVERRIDE_LOCAL:-}" ]; then
      raw="$PREPUSH_LOAD_OVERRIDE_LOCAL"
    else
      raw="$(sh -c "$_PREPUSH_LOAD_PROBE_SH" 2> /dev/null)" || return 1
    fi
  else
    if [ -n "${PREPUSH_LOAD_OVERRIDE_REMOTE:-}" ]; then
      raw="$PREPUSH_LOAD_OVERRIDE_REMOTE"
    else
      timeout_cmd="$(_prepush_timeout_cmd)"
      if [ -n "$timeout_cmd" ]; then
        raw="$("$timeout_cmd" 6 ssh -n -o ConnectTimeout=3 -o BatchMode=yes -o StrictHostKeyChecking=accept-new \
          "$target" "$_PREPUSH_LOAD_PROBE_SH" 2> /dev/null)" || return 1
      else
        raw="$(ssh -n -o ConnectTimeout=3 -o BatchMode=yes -o StrictHostKeyChecking=accept-new \
          "$target" "$_PREPUSH_LOAD_PROBE_SH" 2> /dev/null)" || return 1
      fi
    fi
  fi
  [ -n "$raw" ] || return 1
  # shellcheck disable=SC2086
  set -- $raw
  load1="${1:-}"
  ncpu="${2:-}"
  [ -n "$load1" ] && [ -n "$ncpu" ] && [ "$ncpu" != "0" ] || return 1
  awk -v l="$load1" -v n="$ncpu" 'BEGIN { if (n + 0 <= 0) exit 1; printf "%s %s %.3f\n", l, n, (l / n) }'
}

# host_is_fit TARGET -- 0 if measured load1/nproc is at/under
# PREPUSH_LOAD_THRESHOLD, 1 if over threshold, 2 if the read itself failed
# (unreachable/unresolvable). Callers must not conflate 1 and 2 anywhere the
# difference is user-visible ("over capacity" vs "could not check").
host_is_fit() {
  local target="$1" ratio
  ratio="$(host_load_ratio "$target" | awk '{print $3}')" || return 2
  [ -n "$ratio" ] || return 2
  awk -v r="$ratio" -v thr="$PREPUSH_LOAD_THRESHOLD" 'BEGIN { exit !(r <= thr + 0) }'
}

# =============================================================================
# Lab-wide distribution helpers (OMN-16991, ported by OMN-17159)
# =============================================================================
# Sourced AFTER host_load_ratio/host_is_fit/_prepush_timeout_cmd, which the
# library reuses rather than reimplementing, and BEFORE guard_full_suite_host,
# which is its only caller. Located relative to this script so it resolves the
# same way whether git invokes the hook through .git/hooks or core.hooksPath.
#
# The file is a BYTE-FOR-BYTE copy of omnibase_infra's
# scripts/hooks/prepush_dispatch.sh. That is enforced, not merely intended:
# tests/scripts/test_prepush_host_table.py pins its sha256, so a local edit
# that silently forks the picker fails this repo's own suite. OMN-17159 DoD
# item 3 -- the "three copies byte-identical" cross-repo assertion is not
# implementable from a repo-local harness, so each repo pins the digest of the
# copy it ships.
# shellcheck source=scripts/hooks/prepush_dispatch.sh
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/prepush_dispatch.sh"

# REMOTE_LAB_RUN_VERDICT (OMN-16991) -- set to 1 when a designated lab host ran
# this exact tree green over the remote leg, so the caller elides the local
# pytest entirely.
REMOTE_LAB_RUN_VERDICT=0

# dispatch_to_lab_host HEAVY_WHAT -- try to satisfy HEAVY_WHAT by running it on
# a designated lab host, cheapest-loaded first.
# 0 = satisfied (green), 1 = no evidence (caller falls through), and it does
# NOT return on a remote RED: a suite that genuinely failed on a designated
# host is a failing gate, so it refuses here rather than letting the caller
# fall through to the degraded-evidence override grant.
#
# It walks the RANKED candidate list rather than betting the whole escalation on
# one host (OMN-16991 verify finding 3). Only a verdict -- green or red -- ends
# the walk. "No evidence" (unreachable on arrival, no completion marker) and
# "slot taken between the probe and the run" (rc 4) are placement misses, not
# statements about the tree, so they advance to the next fit host instead of
# refusing a push that another idle lab host could have cleared.
#
# `authorizing` is passed EXPLICITLY: this is the verdict-bearing path, and a
# shadow row's verdict cannot satisfy the escalation by definition. Ranking one
# in would spend a bundle, an scp, a `uv sync` and a full suite to produce an
# answer that is then thrown away, while the authorizing host that could have
# answered goes unprobed.
dispatch_to_lab_host() {
  local heavy_what repo rc=0 idx=1 total
  heavy_what="$1"
  repo="$(basename "$REPO_ROOT")"
  if ! pick_capacity_host "$PREPUSH_LC_HOST" "$repo" authorizing; then
    log "no lab host is fit for ${heavy_what}: ${PREPUSH_PROBE_LOG:-no hosts probed}"
    return 1
  fi
  total="$(prepush_candidate_count)"
  while [ "$idx" -le "$total" ]; do
    prepush_select_candidate "$idx" || break
    if [ -z "$PREPUSH_PICK_SSH" ]; then
      # This candidate IS this host: there is nothing to DISTRIBUTE, so the
      # remote leg cannot answer for it and the ranked hosts after it still
      # can. Skipping it here is correct -- but it used to be SILENT, and that
      # silence is how OMN-17280 stayed invisible: for an actor who can reach
      # no other host, this was the only fit candidate in the lab, and the walk
      # dropped it without a word before falling through to die(). The
      # same-host route now lives in prepush_local_actor_route, one rung below
      # this call in guard_full_suite_host; naming the skip makes the transcript
      # explain how control got there.
      log "lab placement: ${PREPUSH_PICK_LABEL} IS this host, so it carries no remote leg; the same-host route is evaluated after the lab walk (OMN-17280)"
      idx=$((idx + 1))
      continue
    fi
    rc=0
    prepush_remote_run "$heavy_what" || rc=$?
    case "$rc" in
      0)
        REMOTE_LAB_RUN_VERDICT=1
        return 0
        ;;
      3)
        die "${heavy_what} FAILED on the designated lab host '${PREPUSH_PICK_HOSTNAME}' (${PREPUSH_PICK_LABEL})" \
            "the suite genuinely failed on a host we designated -- this is a red gate, not a capacity problem. Read the streamed [${PREPUSH_PICK_LABEL}] output above (the tail of that host's suite.log is printed there), fix the failing tests, then re-push. A remote red is never satisfied by minting an override grant"
        ;;
      4)
        log "lab placement: ${PREPUSH_PICK_LABEL}'s heavy-suite slot was taken on arrival; trying the next fit host"
        ;;
      *)
        log "lab placement: ${PREPUSH_PICK_LABEL} returned no usable evidence; trying the next fit host"
        ;;
    esac
    idx=$((idx + 1))
  done
  log "no fit lab host produced a verdict for ${heavy_what}: ${PREPUSH_PROBE_LOG:-no hosts probed}"
  return 1
}

# prepush_lock_holder_is_ancestor WORKROOT -- 0 when the heavy-suite slot lock
# under WORKROOT is held by a process in THIS process's ancestry, else 1.
#
# The holder record written by prepush_lock_acquire is "<pid> <hostname> <ts>".
# The hostname field is checked first for the same reason the library's own
# reclaim path checks it: a pid recorded by another machine says nothing about
# ours, and matching it against our process tree would be reading a foreign
# number as a local ancestor.
#
# The walk is bounded rather than `while :` -- a `ps` that returns junk, or a
# ppid cycle on a platform that reparents oddly, must not spin a gate.
prepush_lock_holder_is_ancestor() {
  local workroot holder_file holder_pid holder_host self_host pid depth
  workroot="$1"
  [ -n "$workroot" ] || return 1
  holder_file="${workroot}/LOCK/holder"
  [ -r "$holder_file" ] || return 1
  holder_pid="$(cut -d' ' -f1 "$holder_file" 2>/dev/null || true)"
  holder_host="$(cut -d' ' -f2 "$holder_file" 2>/dev/null || true)"
  case "$holder_pid" in
    '' | *[!0-9]*) return 1 ;;
  esac
  self_host="$(hostname -s 2>/dev/null || echo unknown)"
  [ "$holder_host" = "$self_host" ] || return 1
  pid="$$"
  depth=0
  while [ "$depth" -lt 64 ]; do
    pid="$(ps -o ppid= -p "$pid" 2>/dev/null | tr -d ' ')"
    case "$pid" in
      '' | 0 | 1 | *[!0-9]*) return 1 ;;
    esac
    [ "$pid" != "$holder_pid" ] || return 0
    depth=$((depth + 1))
  done
  return 1
}

guard_full_suite_host() {
  local host lc_host label heavy_what designated
  # OMN-15408: the caller names WHICH heavyweight run is being guarded, so the
  # refusal names the real cause. Default preserves the OMN-15059 wording for
  # the flag-driven escalation call sites, which pass no argument.
  heavy_what="${1:-heavy fail-closed full-suite escalation}"
  host="$(hostname -s 2>/dev/null || true)"
  if [ -z "$host" ]; then
    # Fail CLOSED (OMN-16489): see the routing note above PREPUSH_200_HOSTNAME.
    die "could not determine the local hostname while deciding where ${heavy_what} may run" \
        "heavy gate runs are routed by host identity (OMN-15059) and an unidentifiable host cannot be routed. Fix 'hostname -s' (macOS: 'sudo scutil --set HostName <name>'; Linux: 'hostnamectl set-hostname <name>'), or run the push from a designated gate host listed in ${PREPUSH_HOST_TABLE_REL}"
  fi
  lc_host="$(printf '%s' "$host" | tr '[:upper:]' '[:lower:]')"
  PREPUSH_LC_HOST="$lc_host"

  # OMN-17159: host identity now resolves against the COMMITTED host table
  # instead of the two hard-coded names this guard used to test
  # (`[ "$lc_host" = "$lc_target" ] || [ "$lc_host" = "$lc_201" ]`). That
  # literal `||` -- not policy -- was the entire structural reason this repo's
  # heavy escalation could reach no lab host but `.201`, and could reach that
  # one only by a human hand-routing a lane into `~/push-lanes/QUEUE`. It is
  # also why `.201` only ever matched from INSIDE the gate-runner container:
  # the container sets hostname gate-runner-201 while the host itself reports
  # omninode-pc, so every push on the host needed
  # PREPUSH_201_GATE_RUNNER_HOSTNAME exported to pass. Both names are now rows,
  # so `.201` is designated intrinsically and no env var has to survive a
  # process or ssh boundary for the guard to see it.
  #
  # An UNREADABLE table fails CLOSED, on the same reasoning as the unresolvable
  # hostname above: heavy runs are routed by host identity, and identity that
  # cannot be resolved cannot be routed.
  if ! prepush_table_text > /dev/null 2>&1; then
    die "the pre-push host table (${PREPUSH_HOST_TABLE_REL}) could not be read from HEAD, so no host can be identified as a designated gate host for ${heavy_what}" \
        "the table is read from the COMMITTED tree so an uncommitted row cannot self-designate this machine as an authorizing gate host. Commit ${PREPUSH_HOST_TABLE_REL} (or, if you have edited it, commit the edit so HEAD and the working tree agree), then re-push"
  fi
  label="$(prepush_identity_label "$lc_host" || true)"
  designated="$(prepush_designated_hostnames)"

  if [ -n "$label" ]; then
    # OMN-16295: identity alone is not enough -- this known-good host must
    # also have capacity right now.
    if host_is_fit ""; then
      # OMN-16174/OMN-16991: the LOCAL heavy path took no lock of any kind
      # before this change, which is why five concurrent full suites once ran
      # on one host with one of them taking 97+ minutes. It is the busiest
      # path in the hook and was the only unserialized one. Take the same
      # exclusive slot a remote host would have to take.
      local lw lock_rc=0
      lw="$(prepush_local_workroot "$lc_host" || true)"
      [ -n "$lw" ] || lw="${REPO_ROOT}/.onex_state/prepush_distribution"
      prepush_lock_acquire "$lw" || lock_rc=$?
      if [ "$lock_rc" -eq 0 ]; then
        # No `trap ... EXIT` here: prepush_hook_cleanup (installed once, below)
        # already releases the lock. Installing a second EXIT trap would drop
        # the temp-file cleanup this hook installed first.
        return 0
      fi
      if [ "$lock_rc" -eq 2 ]; then
        # The workroot is unusable, which says nothing about this host's
        # capacity. Proceed exactly as the hook did before this lock existed
        # rather than inventing a refusal out of an infrastructural failure.
        # OMN-17280. Before degrading to an UNSERIALIZED run, ask whether this is
        # the actor case: a workroot we cannot write is the signature of running as
        # someone other than whoever provisioned this host, and when NO capacity row
        # is reachable for that actor the same-host route is the governed answer --
        # it takes a per-actor slot under $HOME instead of running with no lock at
        # all, and it writes the receipt that names why the suite ran here. It
        # declines the moment any lab host is reachable, so an OWNER whose workroot
        # is genuinely broken still gets exactly the warning below.
        if prepush_local_actor_route "${heavy_what:-heavy fail-closed full-suite escalation}" \
          "$(prepush_identity_label "$PREPUSH_LC_HOST" || true)"; then
          return 0
        fi
        log "WARNING: could not create the heavy-suite slot lock under '${lw}' -- running unserialized on this host (pre-OMN-17159 behavior). Fix the workroot to restore serialization (OMN-16174)."
        return 0
      fi
      # RE-ENTRANCY (OMN-17159). The slot is held -- but by WHOM decides whether
      # this is contention at all. If the recorded holder is an ANCESTOR of this
      # process, this hook run is nested INSIDE the run that already owns the
      # host's heavy slot; it is the same physical occupancy, not a second
      # consumer arriving from outside. Refusing here protects nothing (the
      # outer suite is running either way) and costs the repo the ability to run
      # its own hook tests under its own gate: this repo's heavy escalation
      # covers `tests/scripts/`, several of whose tests spawn the real hook, so
      # a non-re-entrant lock makes every such test fail whenever the gate is
      # the thing running them. That is exactly how this was found -- the
      # governed pre-push for the commit ADDING this lock went red on
      # test_prepush_hook_host_identity_guard.py while 44,608 other tests
      # passed. omnibase_infra never hit it only because its heavy target is
      # `tests/unit/` while its hook tests live in `tests/ci/`.
      #
      # Ancestry is read from the live process table, so unlike an env var this
      # cannot be forged by a caller that merely wants the lock skipped. It is
      # also NOT the recursion guard: unbounded hook-inside-hook recursion is
      # still ONEX_PREPUSH_HOOK_ACTIVE's job (OMN-16425/OMN-16489), untouched
      # here and still fail-closed for a real first-entry recursion.
      if prepush_lock_holder_is_ancestor "$lw"; then
        log "heavy-suite slot at '${lw}' is held by an ANCESTOR of this process -- this run is nested inside the run that owns the slot, not competing with it. Proceeding without taking a second lock (OMN-17159)."
        return 0
      fi
      log "this host is fit but its heavy-suite slot is already held; looking for another lab host before refusing"
    fi
    # Precedence, in order of EVIDENCE STRENGTH -- not convenience:
    #   1. A designated lab host running this exact tree (OMN-16991). A real
    #      suite actually ran on hardware we designate, bound to this sha by a
    #      completion marker carrying {head_sha, argv_sha, exit, collected,
    #      log_sha256}.
    #   2. Single-use receipted degraded-capacity grant. Weakest: it runs a
    #      contended suite here and says so.
    #   3. die().
    # omnibase_infra additionally consults a sha-pinned GitHub-hosted full-suite
    # run AHEAD of (1) (OMN-16688). That leg is NOT ported here yet -- it needs
    # this repo's own sharded-CI shape wired into prepush_remote_verify.py --
    # and it is tracked as the remaining half of OMN-17159. Its absence cannot
    # make this gate accept less work: it only means this repo has one fewer
    # evidence source above the grant, never a new pass.
    if dispatch_to_lab_host "$heavy_what"; then
      return 0
    fi
    # OMN-17280 -- SAME-HOST ROUTE, above the grant on evidence strength.
    # Placed here, and only here, so it can fire ONLY after the lab has been
    # asked and answered nothing. It refuses itself the moment any capacity row
    # is reachable for this actor, which is every one of the owner's own
    # pushes, so the OMN-17392 / OMN-17485 off-box preference is untouched. It
    # is above consume_override_grant because it produces a real full suite on
    # a designated authorizing host -- strictly stronger evidence than a
    # receipted degraded-capacity grant, and it burns no grant to get there.
    if prepush_local_actor_route "$heavy_what" "$label"; then
      return 0
    fi
    if consume_override_grant "degraded-capacity: ${heavy_what} on '${host}' at/over the ${PREPUSH_LOAD_THRESHOLD}x-core load threshold"; then
      log "WARNING: DEGRADED-CAPACITY OVERRIDE IN EFFECT (single-use grant consumed) -- running ${heavy_what} on '${host}' at/over the ${PREPUSH_LOAD_THRESHOLD}x-core load threshold. Treat any evidence from this run as WEAKER than a fit-host-run gate."
      return 0
    fi
    die "${heavy_what} triggered on '${host}' (designated gate host '${label}'), but its load is at/over the ${PREPUSH_LOAD_THRESHOLD}x-core threshold and no other lab host could take the work" \
        "probed hosts: ${PREPUSH_PROBE_LOG:-none}. The table's own header (${PREPUSH_HOST_TABLE_REL}) documents how to add or re-enable a lab host. Or mint a single-use grant to run here anyway (degraded evidence -- do not use as a routine bypass): uv run python scripts/hooks/prepush_override_grant.py mint --reason '<why>'"
  fi
  # Not a designated host. Same precedence, same ordering, same reasoning.
  if dispatch_to_lab_host "$heavy_what"; then
    return 0
  fi
  if consume_override_grant "degraded-host: ${heavy_what} on '${host}', not a designated gate host"; then
    log "WARNING: DEGRADED-HOST OVERRIDE IN EFFECT (single-use grant consumed) -- running ${heavy_what} on '${host}', NOT a designated gate host (${designated}). This host has weaker isolation/headroom; treat any evidence from this run as WEAKER than a designated-host gate. See ${PREPUSH_HOST_TABLE_REL} for the designated set."
    return 0
  fi
  die "${heavy_what} triggered on host '${host}', not the designated .200 build host ('${PREPUSH_200_HOSTNAME}') nor any other designated gate host (${designated})" \
      "probed lab hosts: ${PREPUSH_PROBE_LOG:-none}. Push from a designated host, OR add/enable a lab host (the procedure is in ${PREPUSH_HOST_TABLE_REL}'s header), OR mint a single-use override grant to run the full suite on this host anyway (visible, receipted, degraded-evidence override -- do not use as a routine bypass): uv run python scripts/hooks/prepush_override_grant.py mint --reason '<why>'"
}

# -----------------------------------------------------------------------------
# Heavyweight-SELECTION predicate (OMN-15408)
# -----------------------------------------------------------------------------
# The OMN-15059 guard above was wired to fire on the selector's `is_full_suite`
# FLAG. That is the wrong key: the selector routinely emits
# `is_full_suite=False` with `selected_paths=["tests/"]` -- the entire suite
# arriving as an "impacted subset" -- and those runs sail straight past the
# guard. Measured on host `omnibook` through real `git push` runs on
# 2026-07-29, against the identical predicate in the sibling copies of this
# hook: omnimarket selected `is_full_suite=False paths=[ tests/ ]` and executed
# 13,898 tests in 506s locally with the guard never invoked; omnibase_infra
# likewise ran 2,429 tests in 245s unguarded. The SAME selected work forced via
# `PREPUSH_FULL_SUITE=1` (`is_full_suite=True reason=feature_flag_off
# paths=[ tests/ ]`) WAS refused. Identical cost, opposite outcome, decided by
# a flag.
#
# SEAM -- what "heavyweight selection" means, exactly: the selection is
# heavyweight when the paths pytest is about to be handed COVER THE ENTIRETY of
# any HEAVY TARGET (`$HEAVY_SELECTION_TARGETS`, defined next to the pytest
# invocation below so the predicate and the actual run can never drift apart).
# Concretely: some selected path is a heavy target itself or a directory
# ANCESTOR of one. Expressed against the selector's own output -- NOT a parallel
# cost model, no test counting, no timing heuristic, nothing this hook does not
# already parse.
#
# There are exactly TWO heavy targets, and the second one is the OMN-15408
# remediation. Round 1 measured the selection against `$FULL_SUITE_TARGET`
# (`tests/`) alone, which made the fix INERT for this repo's own dominant
# heavyweight shape:
#
#   * `$FULL_SUITE_TARGET` (`tests/`) -- what the fail-closed escalation runs.
#     Reached when the selector sets `is_full_suite=True` (guarded on the flag
#     branch too) or emits `selected_paths=["tests/"]`.
#   * `$SELECTOR_WHOLE_TREE_SENTINEL` (`tests/unit/`) -- the selector's OWN
#     fail-closed "I could not narrow this" answer. It is a DESCENDANT of
#     `tests/`, never an ancestor, so a target set of `tests/` alone can never
#     trip on it. Measured on host `omnibook` 2026-07-29 against the SHIPPED
#     round-1 hook at merged commit c5b0a9e1, real selector, on round-1's own
#     two-file diff (`PREPUSH_BASE_REF=c5b0a9e1^`):
#     `selection: is_full_suite=False reason=None paths=[ tests/unit/ ]` ->
#     `running impacted subset` -> guard NEVER invoked, exit 0, push allowed.
#     That sentinel is 1452 of the 1520 test files the escalation itself would
#     run (95.5%; `tests/` minus the always-ignored `tests/integration`), and
#     the selector's own cost model shards it 37 ways versus 40 for the true
#     full suite. It is the full-suite run wearing a different label, not a
#     narrowing in any practical sense.
#
# This is deliberately NOT "any large selection" -- the sentinel is heavy
# because it is the selector's declared no-narrowing-achieved answer, a signal
# the selector already emits. A genuine narrow selection (`tests/scripts/`,
# `tests/unit/scripts/`, a single test module) is strictly below every heavy
# target and stays runnable locally -- the guard must not brick every push from
# a developer's machine, only the ones that are the full-suite run relabelled.
# Repos whose fail-closed sentinel is a genuine minority of their suite
# (omnimarket: `tests/unit/` is 411 of 1251 files, 33%) correctly do NOT list it
# as a heavy target; a heavy-target list is a per-repo measured claim, not a
# constant to copy.
#
# Keep this function self-contained (targets passed in, no globals): it is
# extracted and EXECUTED directly by
# tests/scripts/test_prepush_hook_host_identity_guard.py.
selection_is_whole_suite() {
  # $1 = space-separated heavy-target list; remaining args = selected paths.
  # Word-splitting $1 is INTENTIONAL (the target list is a hook-declared
  # constant, never user input, and pytest directory targets contain no
  # whitespace). A single target still behaves exactly as it did in round 1.
  local targets normalized_target p normalized t
  targets="$1"
  shift
  [ -n "$targets" ] || return 1
  # shellcheck disable=SC2086
  for t in $targets; do
    [ -n "$t" ] || continue
    normalized_target="${t%/}/"
    for p in "$@"; do
      [ -n "$p" ] || continue
      normalized="${p%/}/"
      case "$normalized_target" in
        "$normalized"*) return 0 ;;
      esac
    done
  done
  return 1
}

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" \
  || die "not inside a git worktree" \
         "run 'git push' from within the omnibase_core repository"
cd "$REPO_ROOT"

BASE_REF="${PREPUSH_BASE_REF:-origin/dev}"

# Deterministic diff base (plan section 3d.3): fetch the base ref best-effort so
# an online push gets an up-to-date merge-base, then REQUIRE it to resolve.
# Offline is tolerated ONLY when the ref already exists locally; an entirely
# unresolvable base HARD-ERRORS rather than silently diffing against nothing.
git fetch --quiet origin "${BASE_REF#origin/}" 2>/dev/null || true
if ! git rev-parse --verify --quiet "${BASE_REF}^{commit}" >/dev/null; then
  die "base ref '${BASE_REF}' could not be resolved" \
      "fetch it ('git fetch origin ${BASE_REF#origin/}') or set PREPUSH_BASE_REF to a resolvable ref"
fi

BASE_SHA="$(git merge-base "${BASE_REF}" HEAD 2>/dev/null)" \
  || die "no common ancestor between '${BASE_REF}' and HEAD" \
         "rebase your branch onto ${BASE_REF} so a merge-base exists"

BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo HEAD)"

CHANGED_FILE="$(mktemp)"
SELECTION_FILE="$(mktemp)"
SELECTION_ERR="$(mktemp)"
# ONE exit trap for the whole hook (OMN-16991). bash keeps exactly one EXIT trap
# per shell, so a later `trap prepush_lock_release EXIT` installed by
# guard_full_suite_host would silently REPLACE this temp-file cleanup and leak
# three mktemp files on every heavy run that took the host slot. Both jobs live
# in one handler instead, so neither can displace the other.
prepush_hook_cleanup() {
  rm -f "${CHANGED_FILE:-}" "${SELECTION_FILE:-}" "${SELECTION_ERR:-}" 2> /dev/null || true
  prepush_lock_release
}
trap prepush_hook_cleanup EXIT

git diff --name-only "${BASE_SHA}" HEAD > "$CHANGED_FILE"

# Feature-flag: default ON (impacted subset). Honor the CI var name and an
# explicit full-suite override. Neither knob is a silent bypass -- forcing OFF
# runs MORE tests (the whole suite), never fewer.
FLAG="on"
case "${ENABLE_SMART_TESTS:-}" in
  false | False | FALSE | 0 | off | OFF) FLAG="off" ;;
esac
if [ -n "${PREPUSH_FULL_SUITE:-}" ]; then
  FLAG="off"
fi

# DRY: invoke the EXACT module CI runs (scripts.ci.detect_test_paths), same flags.
# Split on the optional adjacency override to avoid empty-array expansion under
# `set -u` on bash 3.2 (macOS system bash).
run_selector() {
  if [ -n "${PREPUSH_ADJACENCY:-}" ]; then
    uv run python -m scripts.ci.detect_test_paths \
      --changed-files-from "$CHANGED_FILE" \
      --ref-name "$BRANCH" \
      --event-name pull_request \
      --feature-flag "$FLAG" \
      --base-ref "$BASE_SHA" \
      --adjacency "$PREPUSH_ADJACENCY"
  else
    uv run python -m scripts.ci.detect_test_paths \
      --changed-files-from "$CHANGED_FILE" \
      --ref-name "$BRANCH" \
      --event-name pull_request \
      --feature-flag "$FLAG" \
      --base-ref "$BASE_SHA"
  fi
}

if ! run_selector > "$SELECTION_FILE" 2> "$SELECTION_ERR"; then
  log "selector stderr follows:"
  cat "$SELECTION_ERR" >&2 || true
  die "governed test selector failed to resolve a selection" \
      "verify scripts/ci/detect_test_paths.py + scripts/ci/test_selection_adjacency.yaml resolve under 'uv run' in this worktree"
fi

# Parse the selection with stdlib json -- fail loud on any parse error.
read_sel() {
  python3 - "$SELECTION_FILE" "$1" << 'PY'
import json
import sys

with open(sys.argv[1]) as fh:
    data = json.load(fh)
val = data[sys.argv[2]]
if isinstance(val, list):
    print("\n".join(val))
else:
    print(val)
PY
}

IS_FULL="$(read_sel is_full_suite)" \
  || die "could not parse selector output (is_full_suite)" \
         "the selector emitted non-JSON; inspect $SELECTION_FILE"
REASON="$(read_sel full_suite_reason 2> /dev/null || true)"

PATHS=()
PATHS_STR=""
while IFS= read -r p; do
  if [ -n "$p" ]; then
    PATHS+=("$p")
    PATHS_STR="${PATHS_STR}${p} "
  fi
done < <(read_sel selected_paths)

log "selection: is_full_suite=${IS_FULL} reason=${REASON:-none} paths=[ ${PATHS_STR}] (feature-flag=${FLAG})"

# Assemble the pytest target set. tests/integration is always ignored -- it needs
# real services and stays a CI-only concern (plan section 2 CI-only).
RC=0
# Bounded-timeout flags (OMN-14967): mirror the explicit CI invocation
# (.github/workflows/ci.yml) so this hook is immune to whichever pytest ini
# file wins config-precedence in a given worktree. tests/pytest.ini's addopts
# has no -n/--timeout and silently outranks pyproject.toml's
# [tool.pytest.ini_options] safety net whenever pytest is invoked with
# `tests/` (or a tests/ subpath) as an argument -- pytest config discovery
# picks the nearest ini to the invocation args, not pyproject.toml, and the
# two do NOT merge. Passing these on the command line here means the
# per-test timeout applies regardless of which ini file pytest resolves.
# OMN-15977: signal method, not thread -- thread-based timeout cannot kill a
# CPU-bound pure-Python loop holding the GIL (the watcher thread never gets
# scheduled), which is exactly the failure mode that produced two
# 46min/53min unkillable local runaways on 2026-08-12. Signal delivers
# SIGALRM at the next bytecode boundary regardless of GIL contention.
PREPUSH_TIMEOUT_FLAGS="-n4 --dist=loadgroup --timeout=60 --timeout-method=signal"

# SINGLE SOURCE OF TRUTH for "what the heavy run is" (OMN-15408): the
# fail-closed escalation runs exactly this target, and `selection_is_whole_suite`
# measures the impacted-subset selection against this same value. Changing the
# escalation target automatically moves the guard predicate with it.
FULL_SUITE_TARGET="tests/"

# The governed selector's OWN fail-closed whole-tree sentinel -- the single-entry
# answer it emits to mean "no narrowing achieved" (with `is_full_suite=False`,
# which is exactly why round 1 missed it). Single-sourced from the selector:
# `scripts/ci/test_selection_closure.py::TEST_UNIT_PREFIX`, which
# `compute_closure_selection` returns as `selected_files=[TEST_UNIT_PREFIX]` on
# every ambiguity, and which `scripts/ci/detect_test_paths.py` passes straight
# through. tests/scripts/test_prepush_hook_host_identity_guard.py asserts this
# literal still equals that constant AND that it still covers a supermajority of
# the escalation target, so neither half of the claim can drift silently.
SELECTOR_WHOLE_TREE_SENTINEL="tests/unit/"

# The heavy-target set the selection is measured against. Space-separated; see
# the SEAM comment on `selection_is_whole_suite` above for why there are two and
# what each one is.
HEAVY_SELECTION_TARGETS="${FULL_SUITE_TARGET} ${SELECTOR_WHOLE_TREE_SENTINEL}"

# The integration-path addendum the remote leg appends to a heavy escalation's
# argv (`prepush_remote_argv` in prepush_dispatch.sh). It is EMPTY in this repo,
# declared rather than omitted, for two independent reasons:
#
#   1. bash 3.2 -- macOS's system bash, which runs this hook on every lab Mac --
#      raises "unbound variable" for `${#NAME[@]}` on a NEVER-DECLARED array
#      under `set -u`. Newer bash quietly answers 0. prepush_dispatch.sh is a
#      byte-identical copy of omnibase_infra's and therefore reads this name
#      unconditionally, so leaving it undeclared would abort the remote leg on
#      exactly the hosts this port exists to reach.
#   2. It is genuinely empty HERE, not merely unset. OMN-16825's invariant is
#      that an escalation must never run FEWER of the impacted tests than the
#      narrowing it replaces. omnibase_infra needs an addendum because its
#      escalation target is `tests/unit/`, which excludes `tests/integration/
#      chains/`. This repo's target is `tests/` -- the whole tree -- so it is
#      already a superset of every selectable path, and both the local site and
#      the remote wrapper append the same `--ignore=tests/integration`. There is
#      no path the escalation could drop.
RUNNABLE_INTEGRATION_PATHS=()

# =============================================================================
# Override-inheritance sanitization (OMN-16489, F-04)
# =============================================================================
# PREPUSH_* overrides (and ENABLE_SMART_TESTS) are honored at THIS hook's
# entry only. They must never inherit into the pytest subprocess tree: a test
# down there that re-invokes this script would receive the OUTER push's bypass
# grants -- the exact mechanism that turned one sanctioned override into a
# recursive 44k-test full-suite launcher (friction report F-01/F-04, ~9h03m).
# Called inside the subshell wrapping each pytest invocation, after the
# command's own knobs have been captured into non-PREPUSH names, so the parent
# hook's variables are untouched. Only EXPORTED names can inherit, so only
# those are scrubbed. ONEX_PREPUSH_HOOK_ACTIVE deliberately survives -- the
# recursion guard above depends on children inheriting it. This stops
# inheritance ONLY; override semantics at hook entry are unchanged (the
# override-mechanism redesign is OMN-16480, review-gated).
scrub_prepush_override_env() {
  local v
  for v in $(compgen -A export PREPUSH_ || true); do
    unset "$v" || true
  done
  unset ENABLE_SMART_TESTS || true
}

if [ "$IS_FULL" = "True" ] || [ "$IS_FULL" = "true" ]; then
  guard_full_suite_host
  if [ "$REMOTE_LAB_RUN_VERDICT" -eq 1 ]; then
    # A designated lab host already ran THIS EXACT TREE green over the remote
    # leg (OMN-16991), bound to this sha by a completion marker carrying
    # {head_sha, argv_sha, exit, collected, log_sha256}. Re-running the same
    # suite locally would burn hours to re-derive an answer we hold, on the
    # host the guard just measured as unfit. Skipping it is not a discount on
    # the gate: the verdict came from a real pytest exit code on hardware this
    # repo designates, and a remote RED never reaches here -- dispatch_to_lab_host
    # refuses the push itself in that case.
    log "SKIPPING the local full suite: it already ran GREEN on a designated lab host for this exact tree."
  else
    log "running FULL suite (fail-closed escalation): uv run pytest ${FULL_SUITE_TARGET} --ignore=tests/integration ${PREPUSH_TIMEOUT_FLAGS} ${PREPUSH_PYTEST_ARGS:-}"
    (
      _pytest_timeout_flags="${PREPUSH_TIMEOUT_FLAGS}"
      _pytest_extra_args="${PREPUSH_PYTEST_ARGS:-}"
      scrub_prepush_override_env
      # shellcheck disable=SC2086
      exec uv run pytest "${FULL_SUITE_TARGET}" --ignore=tests/integration --tb=short ${_pytest_timeout_flags} ${_pytest_extra_args}
    ) || RC=$?
  fi
elif [ "${#PATHS[@]}" -gt 0 ]; then
  # OMN-15408: guard on the SELECTED WORK, not the is_full_suite flag. A
  # selection that covers a whole heavy target is the heavy run under another
  # name and must be routed to a designated host exactly as the flagged
  # escalation is.
  if selection_is_whole_suite "$HEAVY_SELECTION_TARGETS" "${PATHS[@]}"; then
    guard_full_suite_host "whole-suite-equivalent impacted selection (is_full_suite=${IS_FULL}, selected paths [ ${PATHS_STR}] cover an entire heavyweight target [ ${HEAVY_SELECTION_TARGETS} ])"
  fi
  if [ "$REMOTE_LAB_RUN_VERDICT" -eq 1 ]; then
    # Same reasoning as the escalation branch above. Reachable only through
    # guard_full_suite_host, which is only called here for a whole-suite-
    # equivalent selection -- a narrowed selection never sets this sentinel.
    log "SKIPPING the local run: this whole-suite-equivalent selection already ran GREEN on a designated lab host for this exact tree."
  else
    log "running impacted subset: uv run pytest ${PATHS_STR}--ignore=tests/integration ${PREPUSH_TIMEOUT_FLAGS} ${PREPUSH_PYTEST_ARGS:-}"
    (
      _pytest_timeout_flags="${PREPUSH_TIMEOUT_FLAGS}"
      _pytest_extra_args="${PREPUSH_PYTEST_ARGS:-}"
      scrub_prepush_override_env
      # shellcheck disable=SC2086
      exec uv run pytest "${PATHS[@]}" --ignore=tests/integration --tb=short ${_pytest_timeout_flags} ${_pytest_extra_args}
    ) || RC=$?
  fi
else
  log "no impacted unit tests mapped for this push (no source/test change contributed a target); nothing to run."
fi

if [ "$RC" -ne 0 ]; then
  log "ERROR: impacted tests failed (pytest exit ${RC})"
  log "REMEDIATION: fix the failing tests, then re-push. Reproduce with: uv run pytest ${PATHS_STR:-tests/} --ignore=tests/integration"
  exit "$RC"
fi

log "impacted tests passed; allowing push."
exit "$RC"
