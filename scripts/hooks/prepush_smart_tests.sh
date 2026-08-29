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

# Cross-platform (Linux `.201` / macOS `.200`) load probe: os.getloadavg()[0]
# and os.cpu_count() are both POSIX-portable via the stdlib, which sidesteps
# needing separate /proc/loadavg-vs-sysctl branches (and their escaping) in
# both the local AND the remote-via-ssh cases below. No quote characters
# appear in this snippet -- it is embedded inside a single-quoted remote
# command string in the ssh branch, so it must stay that way.
_PREPUSH_LOAD_PROBE_PY='import os,sys
n=os.cpu_count() or 0
sys.exit(1) if n<=0 else print(os.getloadavg()[0], n)'

# Prefer GNU coreutils timeout(1); fall back to gtimeout(1) (Homebrew name on
# macOS); fall back to no wrapper at all (ssh -o ConnectTimeout already bounds
# the connection phase, and the remote command is a single fast python3 -c).
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
host_load_ratio() {
  local target="$1" raw load1 ncpu timeout_cmd
  if [ -z "$target" ]; then
    if [ -n "${PREPUSH_LOAD_OVERRIDE_LOCAL:-}" ]; then
      raw="$PREPUSH_LOAD_OVERRIDE_LOCAL"
    else
      raw="$(python3 -c "$_PREPUSH_LOAD_PROBE_PY" 2> /dev/null)" || return 1
    fi
  else
    if [ -n "${PREPUSH_LOAD_OVERRIDE_REMOTE:-}" ]; then
      raw="$PREPUSH_LOAD_OVERRIDE_REMOTE"
    else
      timeout_cmd="$(_prepush_timeout_cmd)"
      if [ -n "$timeout_cmd" ]; then
        raw="$("$timeout_cmd" 6 ssh -o ConnectTimeout=3 -o BatchMode=yes -o StrictHostKeyChecking=accept-new \
          "$target" "python3 -c '${_PREPUSH_LOAD_PROBE_PY}'" 2> /dev/null)" || return 1
      else
        raw="$(ssh -o ConnectTimeout=3 -o BatchMode=yes -o StrictHostKeyChecking=accept-new \
          "$target" "python3 -c '${_PREPUSH_LOAD_PROBE_PY}'" 2> /dev/null)" || return 1
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

guard_full_suite_host() {
  local host lc_host lc_target lc_201 heavy_what
  # OMN-15408: the caller names WHICH heavyweight run is being guarded, so the
  # refusal names the real cause. Default preserves the OMN-15059 wording for
  # the flag-driven escalation call sites, which pass no argument.
  heavy_what="${1:-heavy fail-closed full-suite escalation}"
  host="$(hostname -s 2>/dev/null || true)"
  if [ -z "$host" ]; then
    # Fail CLOSED (OMN-16489): see the routing note above PREPUSH_200_HOSTNAME.
    die "could not determine the local hostname while deciding where ${heavy_what} may run" \
        "heavy gate runs are routed by host identity (OMN-15059) and an unidentifiable host cannot be routed. Fix 'hostname -s' (macOS: 'sudo scutil --set HostName <name>'; Linux: 'hostnamectl set-hostname <name>'), or run the push from a designated gate host (.200 '${PREPUSH_200_HOSTNAME}' or the .201 gate-runner '${PREPUSH_201_GATE_RUNNER_HOSTNAME}')"
  fi
  lc_host="$(printf '%s' "$host" | tr '[:upper:]' '[:lower:]')"
  lc_target="$(printf '%s' "$PREPUSH_200_HOSTNAME" | tr '[:upper:]' '[:lower:]')"
  lc_201="$(printf '%s' "$PREPUSH_201_GATE_RUNNER_HOSTNAME" | tr '[:upper:]' '[:lower:]')"
  if [ "$lc_host" = "$lc_target" ] || [ "$lc_host" = "$lc_201" ]; then
    # OMN-16295: identity alone is not enough -- this known-good host must
    # also have capacity right now.
    if host_is_fit ""; then
      return 0
    fi
    if [ -n "${PREPUSH_ALLOW_LOCAL_FULL_SUITE:-}" ]; then
      log "WARNING: DEGRADED-CAPACITY OVERRIDE IN EFFECT (PREPUSH_ALLOW_LOCAL_FULL_SUITE set) -- running ${heavy_what} on '${host}' at/over the ${PREPUSH_LOAD_THRESHOLD}x-core load threshold. Treat any evidence from this run as WEAKER than a fit-host-run gate."
      return 0
    fi
    local other_target other_label other_rc other_note
    if [ "$lc_host" = "$lc_target" ]; then
      other_target="$PREPUSH_201_SSH_TARGET"
      other_label="the .201 gate-runner (${PREPUSH_201_GATE_RUNNER_HOSTNAME})"
    else
      other_target="$PREPUSH_200_SSH_TARGET"
      other_label=".200 (${PREPUSH_200_HOSTNAME})"
    fi
    other_rc=0
    host_is_fit "$other_target" || other_rc=$?
    case "$other_rc" in
      0) other_note="${other_label} currently HAS capacity -- route there instead" ;;
      2) other_note="${other_label} could not be reached to check capacity" ;;
      *) other_note="${other_label} is ALSO at/over the load threshold" ;;
    esac
    die "${heavy_what} triggered on '${host}' (the designated host by identity), but its load is at/over the ${PREPUSH_LOAD_THRESHOLD}x-core threshold" \
        "${other_note}. See docs/runbooks/200-build-lane-execution-pattern.md for the .201 gate-runner recipe, or set PREPUSH_ALLOW_LOCAL_FULL_SUITE=1 to run here anyway (degraded evidence -- do not use as a routine bypass)"
  fi
  if [ -n "${PREPUSH_ALLOW_LOCAL_FULL_SUITE:-}" ]; then
    log "WARNING: DEGRADED-HOST OVERRIDE IN EFFECT (PREPUSH_ALLOW_LOCAL_FULL_SUITE set) -- running ${heavy_what} on '${host}', NOT the designated .200 host ('${PREPUSH_200_HOSTNAME}'). This host has weaker isolation/headroom than .200; treat any evidence from this run as WEAKER than a .200-run gate. See docs/runbooks/200-build-lane-execution-pattern.md."
    return 0
  fi
  die "${heavy_what} triggered on host '${host}', not the designated .200 build host ('${PREPUSH_200_HOSTNAME}')" \
      "push from .200 instead (ssh jonah@stickybeatz-studio.tail75df5e.ts.net, wrap remote commands as zsh -lc \"...\"; see docs/runbooks/200-build-lane-execution-pattern.md for the full pattern), OR set PREPUSH_ALLOW_LOCAL_FULL_SUITE=1 to run the full suite on this host anyway (visible, degraded-evidence override -- do not use as a routine bypass)"
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
trap 'rm -f "$CHANGED_FILE" "$SELECTION_FILE" "$SELECTION_ERR"' EXIT

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
  log "running FULL suite (fail-closed escalation): uv run pytest ${FULL_SUITE_TARGET} --ignore=tests/integration ${PREPUSH_TIMEOUT_FLAGS} ${PREPUSH_PYTEST_ARGS:-}"
  (
    _pytest_timeout_flags="${PREPUSH_TIMEOUT_FLAGS}"
    _pytest_extra_args="${PREPUSH_PYTEST_ARGS:-}"
    scrub_prepush_override_env
    # shellcheck disable=SC2086
    exec uv run pytest "${FULL_SUITE_TARGET}" --ignore=tests/integration --tb=short ${_pytest_timeout_flags} ${_pytest_extra_args}
  ) || RC=$?
elif [ "${#PATHS[@]}" -gt 0 ]; then
  # OMN-15408: guard on the SELECTED WORK, not the is_full_suite flag. A
  # selection that covers a whole heavy target is the heavy run under another
  # name and must be routed to .200 exactly as the flagged escalation is.
  if selection_is_whole_suite "$HEAVY_SELECTION_TARGETS" "${PATHS[@]}"; then
    guard_full_suite_host "whole-suite-equivalent impacted selection (is_full_suite=${IS_FULL}, selected paths [ ${PATHS_STR}] cover an entire heavyweight target [ ${HEAVY_SELECTION_TARGETS} ])"
  fi
  log "running impacted subset: uv run pytest ${PATHS_STR}--ignore=tests/integration ${PREPUSH_TIMEOUT_FLAGS} ${PREPUSH_PYTEST_ARGS:-}"
  (
    _pytest_timeout_flags="${PREPUSH_TIMEOUT_FLAGS}"
    _pytest_extra_args="${PREPUSH_PYTEST_ARGS:-}"
    scrub_prepush_override_env
    # shellcheck disable=SC2086
    exec uv run pytest "${PATHS[@]}" --ignore=tests/integration --tb=short ${_pytest_timeout_flags} ${_pytest_extra_args}
  ) || RC=$?
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
