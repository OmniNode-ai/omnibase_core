#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
#
# =============================================================================
# Lab-wide pre-push distribution (OMN-16991) -- sourced helper library
# =============================================================================
# Sourced by scripts/hooks/prepush_smart_tests.sh. Adds three things the hook
# has never had:
#
#   1. A host TABLE replacing the two-hostname literal that was the structural
#      reason .101/.105 could not be used (they were absent by a literal `||`,
#      not by policy).
#   2. SLOT-AWARE placement. Measured 2026-08-30T05:0xZ: .201 read load1
#      14.08/32 = 0.44x -- the FITTEST ratio in the lab -- while running three
#      concurrent prepush suites behind a 10-deep queue. load1 is a CPU-time
#      proxy; the scarce resource is an exclusive heavy-suite slot, so a host
#      with a held slot is UNFIT (rc 3), not merely low-ranked.
#   3. A real remote EXECUTION leg (bundle transplant + identical argv +
#      completion-marker readback), where before the hook only ever probed the
#      other host and interpolated the answer into a refusal string.
#
# NON-NEGOTIABLES, all preserved here:
#   * Nothing in this file can make the gate accept LESS work. Every path
#     either produces a real green suite run on a designated host, or returns
#     "no evidence" and lets the caller fall through to the pre-existing
#     precedence (GitHub-hosted verify -> grant -> die).
#   * A remote RED is a REFUSAL, never a fall-through to the override grant.
#   * Unreachable / unreadable / below-floor / busy all mean SKIP, never
#     "assumed fit" -- the same fail-closed posture as the load probe.
#   * bash 3.2 compatible (macOS system bash): no associative arrays, no
#     `${var,,}`, no `{fd}` redirection, guarded empty-array expansion.

# -----------------------------------------------------------------------------
# Table access -- COMMITTED tree only
# -----------------------------------------------------------------------------
PREPUSH_HOST_TABLE_REL="scripts/hooks/prepush_hosts.tsv"

# prepush_table_text -- prints the committed table, or returns 1 with a reason
# on stderr. Reading from HEAD (not the working tree) is what stops an
# uncommitted row from self-designating this machine as an authorizing gate
# host; the working-tree divergence check stops the inverse trick of editing
# the file after a commit that CI already saw.
prepush_table_text() {
  local head_copy work_copy
  if ! head_copy="$(git -C "$REPO_ROOT" show "HEAD:${PREPUSH_HOST_TABLE_REL}" 2> /dev/null)"; then
    printf 'host table absent at HEAD (%s)\n' "$PREPUSH_HOST_TABLE_REL" >&2
    return 1
  fi
  if [ -f "${REPO_ROOT}/${PREPUSH_HOST_TABLE_REL}" ]; then
    work_copy="$(cat "${REPO_ROOT}/${PREPUSH_HOST_TABLE_REL}")"
    if [ "$work_copy" != "$head_copy" ]; then
      printf 'host table differs between the working tree and HEAD\n' >&2
      return 1
    fi
  fi
  printf '%s\n' "$head_copy"
}

# prepush_table_rows -- data rows only (comments and blanks dropped).
prepush_table_rows() {
  prepush_table_text | sed -e 's/#.*$//' -e '/^[[:space:]]*$/d'
}

# prepush_field ROW N -- Nth tab-separated field of ROW.
prepush_field() {
  printf '%s' "$1" | cut -d'	' -f"$2"
}

# prepush_override_var LABEL -- the env var name that REPLACES this row's
# hostname. An override REPLACES the row it names; it never ADDS a name to the
# designated set. That distinction is load-bearing: under a table that lists
# several hosts, an override that merely appended a name could no longer
# DE-designate the local machine, silently inverting the OMN-15059 guard (and
# with it test_guard_refuses_full_suite_escalation_on_non_200_host, which
# proves the refusal by forcing a nonsense hostname).
prepush_override_var() {
  printf 'PREPUSH_HOST_OVERRIDE_%s' "$(printf '%s' "$1" | tr '[:lower:]' '[:upper:]' | tr -c 'A-Z0-9' '_')"
}

# prepush_row_hostname ROW -- the row's effective hostname, lowercased, after
# applying its override. Two legacy aliases are still honored so no existing
# invocation or test breaks: PREPUSH_200_HOSTNAME replaces row h200 and
# PREPUSH_201_GATE_RUNNER_HOSTNAME replaces row h201c (the CONTAINER row --
# that variable always named the container, never the .201 host itself).
prepush_row_hostname() {
  local row label name var val
  row="$1"
  label="$(prepush_field "$row" 1)"
  name="$(prepush_field "$row" 3)"
  case "$label" in
    h200) [ -n "${PREPUSH_200_HOSTNAME:-}" ] && name="$PREPUSH_200_HOSTNAME" ;;
    h201c) [ -n "${PREPUSH_201_GATE_RUNNER_HOSTNAME:-}" ] && name="$PREPUSH_201_GATE_RUNNER_HOSTNAME" ;;
  esac
  var="$(prepush_override_var "$label")"
  eval "val=\${$var:-}"
  [ -n "$val" ] && name="$val"
  printf '%s' "$name" | tr '[:upper:]' '[:lower:]'
}

# prepush_identity_label LC_HOST -- prints the label of the AUTHORIZING row
# this host is, or nothing. Only mode=authorizing rows confer identity: a
# `shadow` host is a placement target whose verdict may not satisfy the
# escalation, so it must not be treated as a designated gate host either --
# otherwise the identity guard would start passing on a host still in
# shadow, which is the exact inversion this table is meant to prevent.
prepush_identity_label() {
  local lc_host row
  lc_host="$1"
  while IFS= read -r row; do
    [ -n "$row" ] || continue
    [ "$(prepush_field "$row" 12)" = "authorizing" ] || continue
    if [ "$(prepush_row_hostname "$row")" = "$lc_host" ]; then
      prepush_field "$row" 1
      return 0
    fi
  done <<EOF
$(prepush_table_rows)
EOF
  return 1
}

# prepush_designated_hostnames -- every authorizing hostname, for messages.
prepush_designated_hostnames() {
  local row out=""
  while IFS= read -r row; do
    [ -n "$row" ] || continue
    [ "$(prepush_field "$row" 12)" = "authorizing" ] || continue
    out="${out}'$(prepush_row_hostname "$row")' "
  done <<EOF
$(prepush_table_rows)
EOF
  printf '%s' "${out% }"
}

# -----------------------------------------------------------------------------
# Slot state -- the dimension load1 is blind to
# -----------------------------------------------------------------------------
# A host is BUSY when a heavy pre-push is already executing there or is queued
# behind one. Returns 0 free / 2 unknown / 3 busy. `unknown` is NOT free: a
# host we cannot prove idle is skipped exactly like one we cannot reach.
#
# The probe counts live prepush_smart_tests.sh processes because that is the
# only signal that sees FOREIGN detached runs -- the ones .201's queue can
# neither observe nor preempt (OMN-16968). A lock that only counts its own
# holders reproduces that defect one host wider.
#
# SLOT-AWARE (OMN-17269): a row with `slots=N` gets N independently lockable
# candidates -- slot 1 at the pre-existing bare `<workroot>/LOCK` (unchanged
# path, so every slots=1 row is byte-identical to before) and slot k>=2 at
# `<workroot>/LOCK.<k>`. `held` is the COUNT of currently-held lock dirs across
# EVERY slot on the row, read fresh on each probe. The generalized busy check
# is `heavy_pids <= self + held`: on a slots=1 row `held` degenerates to `l`
# itself, reproducing the pre-OMN-17269 `p <= self` check exactly. On a
# multi-slot row it lets a legitimately-held OTHER slot explain its own
# process without flagging an untracked foreign process as fit -- if more
# heavy pids are running than held locks explain, that is an untracked
# process this table cannot account for, and the probe stays fail-closed.
# THIS SNIPPET RUNS UNDER THE REMOTE LOGIN SHELL, WHICH IS zsh ON THE LAB MACS
# (measured 2026-09-02: `ssh <h101|h105> 'echo $SHELL'` -> /bin/zsh). Three
# properties below exist because of that, and each of them was a live defect
# that silently made every `slots>1` row unreachable (OMN-17606; found by
# the OMN-17602 lane, which widened a host table to slots=2 and got the
# first slot-2 verdicts this probe had ever been asked for -- all of them
# wrong):
#
#   1. NO UNMATCHED GLOB MAY REACH THE SHELL. zsh's default `nomatch` makes an
#      unmatched glob a FATAL parse-time error that aborts the whole command
#      line -- the redirection on the command never applies, because the
#      command never runs. `ls -d "$W"/LOCK "$W"/LOCK.* 2>/dev/null` therefore
#      printed NOTHING whenever no LOCK.<k> existed, so `held` read 0 on every
#      remote Mac probe, precisely in the state where slot 2 is placeable
#      (slot 1 locked, slot 2 free). `find -name` does its own matching, so no
#      glob is ever handed to the shell.
#   2. ONE LEG MUST COUNT AS ONE PROCESS. The remote leg is launched as
#      `zsh -c 'cd ...; ./prepush_smart_tests.sh ...'`, so BOTH the wrapper
#      shell and the script itself carry `prepush_smart_tests.sh` in their
#      argv and a plain grep counted a single leg TWICE (measured on h101,
#      h105 and h201: p=2 with exactly one leg running). Dropping ` -c `
#      lines counts the leg, not the shell that spawned it.
#   3. THE FIELD COUNT IS FIXED AT FOUR. `grep -c .` on an EXISTING BUT EMPTY
#      file prints 0 and exits 1, so the old `|| echo 0` fired as well and
#      emitted a second line -- `$q` became two words, every later field
#      shifted left, and `l` was read out of `p`. Live on h201, whose
#      ~/push-lanes/QUEUE exists and is empty: the trail printed `lock=2`,
#      a value the code cannot otherwise produce.
#
# Together (1) and (2) are why LOCK.2 had never been created once anywhere in
# the fleet: with p double-counted and held stuck at 0 the busy predicate
# `p <= self + held` read `2 <= 0` for the one state slot 2 exists to serve.
# Fixing either alone is not enough -- `2 <= 1` and `1 <= 0` both still refuse.
_PREPUSH_SLOT_PROBE_SH='q=0
if [ -r "$HOME/push-lanes/QUEUE" ]; then
  q=$(grep -c . "$HOME/push-lanes/QUEUE" 2>/dev/null)
  [ -n "$q" ] || q=0
fi
p=$(ps ax -o args= 2>/dev/null | grep prepush_smart_tests.sh | grep -v grep | grep -cv -e " -c " || true)
[ -n "$p" ] || p=0
si="${PREPUSH_SLOT_INDEX:-1}"
lockdir="$PREPUSH_WORKROOT/LOCK"
[ "$si" = "1" ] || lockdir="$PREPUSH_WORKROOT/LOCK.$si"
l=0
if [ -n "$PREPUSH_WORKROOT" ] && [ -d "$lockdir" ]; then l=1; fi
held=0
if [ -n "$PREPUSH_WORKROOT" ]; then
  held=$(find "$PREPUSH_WORKROOT" -maxdepth 1 -type d -name "LOCK*" 2>/dev/null | grep -c . || true)
  [ -n "$held" ] || held=0
fi
printf "%s %s %s %s\n" "$q" "$p" "$l" "$held"'

# prepush_slot_state TARGET WORKROOT SELF_PIDS [SLOT_INDEX] -- SELF_PIDS is how
# many prepush_smart_tests.sh processes are expected to be OUR OWN on that host
# (1 when probing the local host -- this very hook -- else 0). SLOT_INDEX
# defaults to 1 (OMN-17269), which reproduces the pre-OMN-17269 bare-LOCK
# behavior exactly; a caller probing slot k>=2 of a multi-slot row passes it
# explicitly.
prepush_slot_state() {
  local target workroot self slot raw q p l held tcmd
  target="$1"; workroot="$2"; self="$3"; slot="${4:-1}"
  if [ -n "${PREPUSH_SLOT_OVERRIDE:-}" ]; then
    raw="$PREPUSH_SLOT_OVERRIDE"
  elif [ -z "$target" ]; then
    raw="$(PREPUSH_WORKROOT="$workroot" PREPUSH_SLOT_INDEX="$slot" sh -c "$_PREPUSH_SLOT_PROBE_SH" 2> /dev/null)" || return 2
  else
    tcmd="$(_prepush_timeout_cmd)"
    if [ -n "$tcmd" ]; then
      raw="$("$tcmd" 12 ssh -n -o ConnectTimeout=4 -o BatchMode=yes -o StrictHostKeyChecking=accept-new \
        "$target" "PREPUSH_WORKROOT='${workroot}'; PREPUSH_SLOT_INDEX='${slot}'; $_PREPUSH_SLOT_PROBE_SH" 2> /dev/null)" || return 2
    else
      raw="$(ssh -n -o ConnectTimeout=4 -o BatchMode=yes -o StrictHostKeyChecking=accept-new \
        "$target" "PREPUSH_WORKROOT='${workroot}'; PREPUSH_SLOT_INDEX='${slot}'; $_PREPUSH_SLOT_PROBE_SH" 2> /dev/null)" || return 2
    fi
  fi
  [ -n "$raw" ] || return 2
  # shellcheck disable=SC2086
  set -- $raw
  # EXACTLY four fields, or UNKNOWN. The old parse took ${1..4} positionally
  # with defaults, so a probe that emitted five words (the empty-QUEUE double
  # `q` above) was not rejected -- it was silently READ SHIFTED, and reported
  # one host's heavy_pids as its lock count. A field-count mismatch is now
  # fail-closed: unknown is skipped exactly like unreachable, which is the
  # rule this whole probe is built on.
  [ "$#" -eq 4 ] || return 2
  q="$1"; p="$2"; l="$3"; held="$4"
  [ -n "$q" ] && [ -n "$p" ] && [ -n "$l" ] || return 2
  PREPUSH_SLOT_DETAIL="queue=${q} heavy_pids=${p} lock=${l} held=${held} slot=${slot}"
  [ "$l" -eq 0 ] || return 3
  [ "$q" -eq 0 ] || return 3
  [ "$p" -le "$((self + held))" ] || return 3
  return 0
}

# -----------------------------------------------------------------------------
# uv floor -- presence is not enough
# -----------------------------------------------------------------------------
# Verified by VERSION, not by path existence: the live fleet spread is 0.8.3
# (.101, 13 months old) to 0.11.32 (.200) against a lockfile at revision 3.
# Below the floor, or unreadable, means SKIP.
prepush_uv_version_ok() {
  local target uv floor out tcmd
  target="$1"; uv="$2"; floor="$3"
  [ -n "$uv" ] && [ "$uv" != "-" ] || return 2
  if [ -n "${PREPUSH_UV_VERSION_OVERRIDE:-}" ]; then
    out="$PREPUSH_UV_VERSION_OVERRIDE"
  elif [ -z "$target" ]; then
    out="$("$uv" --version 2> /dev/null)" || return 2
  else
    tcmd="$(_prepush_timeout_cmd)"
    if [ -n "$tcmd" ]; then
      out="$("$tcmd" 12 ssh -n -o ConnectTimeout=4 -o BatchMode=yes -o StrictHostKeyChecking=accept-new \
        "$target" "'${uv}' --version" 2> /dev/null)" || return 2
    else
      out="$(ssh -n -o ConnectTimeout=4 -o BatchMode=yes -o StrictHostKeyChecking=accept-new \
        "$target" "'${uv}' --version" 2> /dev/null)" || return 2
    fi
  fi
  out="$(printf '%s' "$out" | sed -n 's/^uv \([0-9][0-9.]*\).*/\1/p')"
  [ -n "$out" ] || return 2
  PREPUSH_UV_VERSION_SEEN="$out"
  awk -v have="$out" -v want="$floor" 'BEGIN {
    nh = split(have, h, "."); nw = split(want, w, ".");
    n = (nh > nw ? nh : nw);
    for (i = 1; i <= n; i++) {
      a = (i <= nh ? h[i] + 0 : 0); b = (i <= nw ? w[i] + 0 : 0);
      if (a > b) exit 0;
      if (a < b) exit 1;
    }
    exit 0
  }'
}

# -----------------------------------------------------------------------------
# Deterministic, network-free per-host overrides (tests only)
# -----------------------------------------------------------------------------
# The pre-existing PREPUSH_LOAD_OVERRIDE_LOCAL/_REMOTE pair collapses EVERY ssh
# target to one value, which cannot express "host A is fit, host B is busy" --
# the only interesting input to a multi-host picker. These maps are keyed by
# row LABEL so a test can drive the real picker with no network at all.
#
# Same risk profile as the two overrides already shipped: a forged value can
# only change WHERE work is routed, never whether it passed. The verdict still
# comes from a real pytest exit code bound to the tree by a completion marker,
# so no map value can turn a red suite green.
#
# prepush_map_lookup MAP LABEL -- value for LABEL in a "a=1,b=2" map, or empty.
prepush_map_lookup() {
  printf '%s' "$1" | tr ',' '\n' | sed -n "s/^${2}=//p" | head -1
}

# -----------------------------------------------------------------------------
# Orphaned spin-loop reaper (OMN-16995) -- runs BEFORE load is measured
# -----------------------------------------------------------------------------
# omnibase_infra's own suite leaked one `sh -c while :; do :; done` per run:
# `tests/unit/scripts/test_heavy_lock.py` killed the heavy_lock WRAPPER and not
# the shell it wrapped, so the shell was reparented to PID 1 and burned a full
# core forever. Measured on `.200` 2026-08-30: 19 such orphans, every one
# PPID 1, aged 2h47m-12h17m, ~18.6 of 24 cores -- load1 39.31/24 = 1.64x
# against this gate's 1.0x threshold, so EVERY heavy escalation refused. After
# reaping them load1 fell to 17.06 (0.71x) in under 90s and the same escalation
# ran green. `.201` showed the same shape (11 orphans, 14.87 -> 5.95).
#
# The root cause is fixed in the test. This is the STOPGAP that keeps gate
# hosts usable while that fix propagates to every clone and every host, and
# the standing defense against the next process that leaks the same shape:
# load1 is read as a host-fitness FACT by lanes several tickets away from
# whatever produced the load, and no lane can diagnose it from where it stands.
#
# It is deliberately the narrowest possible matcher. All three conditions must
# hold, and a process that fails any one of them is untouched:
#   1. argv is EXACTLY `sh -c while :; do :; done` -- the no-op spin signature.
#      Not a prefix, not a substring, not `bash -c`, not a loop with a body.
#   2. PPID is exactly 1 -- already orphaned, so it has no supervisor that
#      could be waiting on it. (A container-reparented orphan, the `.201`
#      shape, has a non-1 PPID and is deliberately OUT of scope: reaping under
#      a live init we did not start is a bigger claim than this stopgap makes.)
#   3. Age >= PREPUSH_SPIN_ORPHAN_MIN_AGE seconds (default 600) -- long past
#      any plausible in-flight run of the test that spawns it.
# Every kill is logged with pid and age. A reap that cannot run for any reason
# is silent and non-fatal: this must never be able to refuse a push.
PREPUSH_SPIN_ORPHAN_MIN_AGE="${PREPUSH_SPIN_ORPHAN_MIN_AGE:-600}"

# Interpreter-free on purpose, exactly like _PREPUSH_LOAD_PROBE_SH above: the
# OMN-14953 pinned-interpreter gate requires every python invocation under
# scripts/hooks/ to route through `uv run`, and `.201` has no `uv` at all. Also
# POSIX and single-quote-free, because it is handed to ssh(1) and executed by
# whatever login shell the remote user has. Prints "<pid> <age_seconds>" per
# reaped process on stdout; nothing else may go to stdout.
# shellcheck disable=SC2016  # intentionally unexpanded: evaluated by the local
# `sh -c` / the remote login shell, not by this script.
_PREPUSH_SPIN_ORPHAN_REAPER_SH='min=${PREPUSH_SPIN_ORPHAN_MIN_AGE:-600}
ps -ww -Ao pid=,ppid=,etime=,args= 2>/dev/null | while read -r pid ppid etime rest; do
  [ "$ppid" = "1" ] || continue
  [ "$rest" = "sh -c while :; do :; done" ] || continue
  d=0
  case "$etime" in *-*) d=${etime%%-*}; etime=${etime#*-};; esac
  h=0
  case "$etime" in *:*:*) h=${etime%%:*}; etime=${etime#*:};; esac
  m=${etime%%:*}
  s=${etime##*:}
  d=${d#0}; h=${h#0}; m=${m#0}; s=${s#0}
  age=$(( (${d:-0} * 24 + ${h:-0}) * 3600 + ${m:-0} * 60 + ${s:-0} ))
  [ "$age" -ge "$min" ] || continue
  kill -9 "$pid" 2>/dev/null || continue
  printf "%s %s\n" "$pid" "$age"
done'

# reap_spin_loop_orphans TARGET -- TARGET empty for this host, or an ssh(1)
# target. At most one reap per target per hook run. Always returns 0.
reap_spin_loop_orphans() {
  local target="${1:-}" out line pid age timeout_cmd key
  case "${PREPUSH_REAP_SPIN_ORPHANS:-on}" in
    0 | off | no) return 0 ;;
  esac
  key="|${target:-@local}|"
  case "${_PREPUSH_SPIN_REAPED:-}" in
    *"$key"*) return 0 ;;
  esac
  _PREPUSH_SPIN_REAPED="${_PREPUSH_SPIN_REAPED:-}${key}"

  if [ -z "$target" ]; then
    # A deterministic load override means a test harness, not a real host.
    [ -z "${PREPUSH_LOAD_OVERRIDE_LOCAL:-}" ] || return 0
    out="$(PREPUSH_SPIN_ORPHAN_MIN_AGE="$PREPUSH_SPIN_ORPHAN_MIN_AGE" \
      sh -c "$_PREPUSH_SPIN_ORPHAN_REAPER_SH" 2> /dev/null || true)"
  else
    [ -z "${PREPUSH_LOAD_OVERRIDE_REMOTE:-}" ] || return 0
    timeout_cmd="$(_prepush_timeout_cmd)"
    # `ssh -n` is load-bearing here for the same reason it is on the load
    # probe: this runs inside the picker's row loop, whose stdin is the row
    # list, and an ssh that reads it swallows every remaining host.
    if [ -n "$timeout_cmd" ]; then
      out="$("$timeout_cmd" 10 ssh -n -o ConnectTimeout=3 -o BatchMode=yes -o StrictHostKeyChecking=accept-new \
        "$target" "PREPUSH_SPIN_ORPHAN_MIN_AGE=${PREPUSH_SPIN_ORPHAN_MIN_AGE}; $_PREPUSH_SPIN_ORPHAN_REAPER_SH" 2> /dev/null || true)"
    else
      out="$(ssh -n -o ConnectTimeout=3 -o BatchMode=yes -o StrictHostKeyChecking=accept-new \
        "$target" "PREPUSH_SPIN_ORPHAN_MIN_AGE=${PREPUSH_SPIN_ORPHAN_MIN_AGE}; $_PREPUSH_SPIN_ORPHAN_REAPER_SH" 2> /dev/null || true)"
    fi
  fi

  [ -n "$out" ] || return 0
  while IFS=" " read -r pid age; do
    [ -n "$pid" ] || continue
    log "REAPED orphaned no-op spin loop (OMN-16995) on '${target:-this host}': pid=${pid} age=${age}s argv='sh -c while :; do :; done' ppid=1 -- it was consuming a full core and no process was waiting on it"
  done <<EOF
$out
EOF
  return 0
}

# prepush_probe_ratio LABEL TARGET -- prints the load ratio or returns 1.
prepush_probe_ratio() {
  local v
  if [ -n "${PREPUSH_LOAD_OVERRIDE_MAP:-}" ]; then
    v="$(prepush_map_lookup "$PREPUSH_LOAD_OVERRIDE_MAP" "$1")"
    [ -n "$v" ] || return 1
    printf '%s' "$v"
    return 0
  fi
  host_load_ratio "$2" | awk '{print $3}'
}

# prepush_probe_slot LABEL TARGET WORKROOT SELF [SLOT_INDEX] -- 0 free /
# 2 unknown / 3 busy. LABEL is the slot-suffixed candidate label ("h105" for
# slot 1, "h105.2" for slot 2, ...), which is also the override-map key, so a
# test can drive each slot of a multi-slot row independently.
prepush_probe_slot() {
  local v
  if [ -n "${PREPUSH_SLOT_OVERRIDE_MAP:-}" ]; then
    v="$(prepush_map_lookup "$PREPUSH_SLOT_OVERRIDE_MAP" "$1")"
    case "$v" in
      free) PREPUSH_SLOT_DETAIL="override=free"; return 0 ;;
      busy) PREPUSH_SLOT_DETAIL="override=busy"; return 3 ;;
      *) PREPUSH_SLOT_DETAIL="override=unknown"; return 2 ;;
    esac
  fi
  prepush_slot_state "$2" "$3" "$4" "$5"
}

# prepush_probe_uv LABEL TARGET UV FLOOR -- 0 ok / 1 below floor / 2 unreadable.
prepush_probe_uv() {
  local v
  if [ -n "${PREPUSH_UV_OVERRIDE_MAP:-}" ]; then
    v="$(prepush_map_lookup "$PREPUSH_UV_OVERRIDE_MAP" "$1")"
    [ -n "$v" ] || return 2
    PREPUSH_UV_VERSION_SEEN="$v"
    PREPUSH_UV_VERSION_OVERRIDE="uv $v" prepush_uv_version_ok "" "$3" "$4"
    return $?
  fi
  prepush_uv_version_ok "$2" "$3" "$4"
}

# -----------------------------------------------------------------------------
# Placement
# -----------------------------------------------------------------------------
# prepush_load_rows -- materialize every data row into PREPUSH_TABLE_ROWS.
#
# WHY AN ARRAY AND NOT `while IFS= read -r row; ... done <<EOF` (OMN-16991
# verify finding 1, reproduced live): the picker's loop body invokes ssh(1)
# three times per row, and ssh reads its parent's stdin unless told not to.
# With the row list fed in as the loop's stdin, the FIRST probe consumed every
# remaining row and the loop ended after one host -- the real picker on the
# real network emitted `PROBE=[h200=fit(0.9,authorizing)] PICK=[h200]` and never
# evaluated h201/h101/h105, so a lab with three idle hosts refused the push.
# Rows are now read BEFORE any probe runs, and every ssh in this file also
# carries `-n`; either fix alone would close it, and both are kept because the
# defect is silent (a truncated scan looks exactly like a small lab).
#
# The identity helpers above keep their here-doc loops on purpose: their bodies
# execute no subprocess that reads stdin, so they cannot be truncated.
prepush_load_rows() {
  local row
  PREPUSH_TABLE_ROWS=()
  while IFS= read -r row; do
    [ -n "$row" ] || continue
    PREPUSH_TABLE_ROWS[${#PREPUSH_TABLE_ROWS[@]}]="$row"
  done <<EOF
$(prepush_table_rows)
EOF
  [ "${#PREPUSH_TABLE_ROWS[@]}" -gt 0 ]
}

# prepush_candidate_count -- how many fit hosts the last pick ranked.
prepush_candidate_count() {
  if [ -z "${PREPUSH_FIT_RECORDS:-}" ]; then
    printf '0'
    return 0
  fi
  printf '%s\n' "$PREPUSH_FIT_RECORDS" | grep -c . || true
}

# prepush_select_candidate N -- 1-based; loads the Nth ranked fit host into the
# PREPUSH_PICK_* variables. Placement is a RANKED LIST rather than a single
# winner (OMN-16991 verify finding 3) so a candidate that fails to produce a
# verdict -- unreachable on arrival, slot taken between the probe and the run,
# transfer failure -- costs the next-best host, not the whole escalation. The
# previous shape returned one host and refused outright when it did not answer,
# after paying bundle + scp + `uv sync` for nothing.
prepush_select_candidate() {
  local rec
  rec="$(printf '%s\n' "${PREPUSH_FIT_RECORDS:-}" | sed -n "${1}p")"
  [ -n "$rec" ] || return 1
  PREPUSH_PICK_RATIO="$(printf '%s' "$rec" | cut -d'|' -f1)"
  PREPUSH_PICK_LABEL="$(printf '%s' "$rec" | cut -d'|' -f2)"
  PREPUSH_PICK_HOSTNAME="$(printf '%s' "$rec" | cut -d'|' -f3)"
  PREPUSH_PICK_SSH="$(printf '%s' "$rec" | cut -d'|' -f4)"
  PREPUSH_PICK_UV="$(printf '%s' "$rec" | cut -d'|' -f5)"
  PREPUSH_PICK_WORKROOT="$(printf '%s' "$rec" | cut -d'|' -f6)"
  PREPUSH_PICK_SLOTMODE="$(printf '%s' "$rec" | cut -d'|' -f7)"
  PREPUSH_PICK_MODE="$(printf '%s' "$rec" | cut -d'|' -f8)"
  PREPUSH_PICK_SLOT="$(printf '%s' "$rec" | cut -d'|' -f9)"
  [ -n "$PREPUSH_PICK_SLOT" ] || PREPUSH_PICK_SLOT=1
  # OMN-17603: the TARGET host's nominal core count, carried so the remote leg
  # can size its own parallelism from the host that will actually run the
  # suite. INDEX DIVERGENCE, deliberate and documented: omnibase_infra reads
  # this at f11 because its record carries a tier_rank at f10
  # (OMN-17392/OMN-17485). This repo has no placement_tier, so its record is
  # nine fields and `cores` appends at f10. The NAME is what the remote leg
  # couples to and the name is identical; whoever ports the tier ladder here
  # moves this one index and this one comment.
  PREPUSH_PICK_CORES="$(printf '%s' "$rec" | cut -d'|' -f10)"
  return 0
}

# pick_capacity_host LC_HOST REPO [REQUIRE_MODE] -- ranks every host that has
# PROVEN a free slot, cheapest load first, into PREPUSH_FIT_RECORDS, and loads
# the best one into PREPUSH_PICK_*. Returns 1 when nothing is fit. Always sets
# PREPUSH_PROBE_LOG (a "label=verdict" trail for the receipt and the refusal
# message -- every considered host is on the record, so a refusal can be
# audited rather than believed).
#
# REQUIRE_MODE defaults to `authorizing` and is the mode a row must carry to be
# a placement candidate AT ALL. That default is the fix for OMN-16991 verify
# finding 3: ranking on load alone let a `shadow` row outrank both authorizing
# hosts (h200=0.90 h201=0.30 h105=0.20(shadow) -> PICK=h105), and a shadow host
# by definition cannot satisfy the escalation, so the run was dispatched,
# executed, and then discarded -- an escalation that .200 or .201 could have
# answered got refused instead, minutes later. A non-eligible row is now
# skipped BEFORE it is probed: it can never win, so probing it only spends ssh
# round trips on the pre-push critical path.
#
# Order of elimination is deliberate: cheap local facts first (disabled, mode,
# repo denial), then the slot (the scarce resource), then load, then the
# toolchain. load1 ranks only among hosts already proven to hold a free slot --
# it is a tiebreaker, not the placement key.
pick_capacity_host() {
  local lc_host repo want_mode row label role name ssh_t uv floor workroot slotmode denied mode
  local self ratio rc recs="" slots k slot_label cores
  lc_host="$1"; repo="$2"; want_mode="${3:-authorizing}"
  PREPUSH_PROBE_LOG=""
  PREPUSH_PICK_LABEL=""
  PREPUSH_FIT_RECORDS=""
  if ! prepush_load_rows; then
    PREPUSH_PROBE_LOG="host-table-unreadable"
    return 1
  fi
  for row in ${PREPUSH_TABLE_ROWS[@]+"${PREPUSH_TABLE_ROWS[@]}"}; do
    [ -n "$row" ] || continue
    label="$(prepush_field "$row" 1)"
    role="$(prepush_field "$row" 2)"
    mode="$(prepush_field "$row" 12)"
    [ "$role" = "capacity" ] || continue
    if [ "$mode" = "disabled" ]; then
      PREPUSH_PROBE_LOG="${PREPUSH_PROBE_LOG}${label}=disabled "
      continue
    fi
    if [ "$mode" != "$want_mode" ]; then
      PREPUSH_PROBE_LOG="${PREPUSH_PROBE_LOG}${label}=mode-${mode}-not-eligible "
      continue
    fi
    denied="$(prepush_field "$row" 11)"
    case ",${denied}," in
      *",${repo},"*)
        PREPUSH_PROBE_LOG="${PREPUSH_PROBE_LOG}${label}=repo-denied "
        continue
        ;;
    esac
    name="$(prepush_row_hostname "$row")"
    ssh_t="$(prepush_field "$row" 4)"
    # OMN-17603: documentation column, and now also the input the remote leg
    # sizes `-n` from. A row whose value is absent or non-numeric degrades to
    # one worker in prepush_remote_xdist_workers -- it is never assumed ample.
    cores="$(prepush_field "$row" 5)"
    uv="$(prepush_field "$row" 6)"
    floor="$(prepush_field "$row" 7)"
    workroot="$(prepush_field "$row" 8)"
    slotmode="$(prepush_field "$row" 9)"
    slots="$(prepush_field "$row" 10)"
    case "$slots" in '' | *[!0-9]*) slots=1 ;; esac
    [ "$slots" -ge 1 ] 2> /dev/null || slots=1
    self=0
    if [ "$name" = "$lc_host" ]; then
      # This host: probe it directly, and expect to see OUR OWN hook process.
      ssh_t=""
      self=1
    fi

    # SLOT-AWARE (OMN-17269): a row with slots=N is N independently placeable
    # candidates. Slot 1 keeps the bare LABEL (byte-identical placement to
    # every pre-OMN-17269 row, all of which have slots=1); slot k>=2 is
    # LABEL.k, its own override-map key and its own PROBE_LOG entry. Each
    # slot is probed and load-checked FRESH -- a second slot is never assumed
    # fit merely because the row has capacity on paper; it must clear the
    # same live busy/load/uv checks slot 1 does, GIVEN whatever slots on this
    # row are already held.
    k=1
    while [ "$k" -le "$slots" ]; do
      slot_label="$label"
      [ "$k" = "1" ] || slot_label="${label}.${k}"

      rc=0
      prepush_probe_slot "$slot_label" "$ssh_t" "$workroot" "$self" "$k" || rc=$?
      case "$rc" in
        3)
          PREPUSH_PROBE_LOG="${PREPUSH_PROBE_LOG}${slot_label}=busy(${PREPUSH_SLOT_DETAIL:-}) "
          k=$((k + 1))
          continue
          ;;
        2)
          PREPUSH_PROBE_LOG="${PREPUSH_PROBE_LOG}${slot_label}=slot-unknown "
          k=$((k + 1))
          continue
          ;;
      esac

      ratio="$(prepush_probe_ratio "$slot_label" "$ssh_t")" || ratio=""
      if [ -z "$ratio" ]; then
        PREPUSH_PROBE_LOG="${PREPUSH_PROBE_LOG}${slot_label}=unreachable "
        k=$((k + 1))
        continue
      fi
      if ! awk -v r="$ratio" -v thr="$PREPUSH_LOAD_THRESHOLD" 'BEGIN { exit !(r <= thr + 0) }'; then
        PREPUSH_PROBE_LOG="${PREPUSH_PROBE_LOG}${slot_label}=over(${ratio}) "
        k=$((k + 1))
        continue
      fi

      rc=0
      prepush_probe_uv "$slot_label" "$ssh_t" "$uv" "$floor" || rc=$?
      if [ "$rc" -ne 0 ]; then
        PREPUSH_PROBE_LOG="${PREPUSH_PROBE_LOG}${slot_label}=uv-unfit(${PREPUSH_UV_VERSION_SEEN:-unreadable}<${floor}) "
        k=$((k + 1))
        continue
      fi

      PREPUSH_PROBE_LOG="${PREPUSH_PROBE_LOG}${slot_label}=fit(${ratio},${mode}) "
      recs="${recs}${ratio}|${slot_label}|${name}|${ssh_t}|${uv}|${workroot}|${slotmode}|${mode}|${k}|${cores}
"
      k=$((k + 1))
    done
  done
  PREPUSH_PROBE_LOG="${PREPUSH_PROBE_LOG% }"
  [ -n "$recs" ] || return 1
  # Ascending by load ratio: the cheapest host is tried first and the rest stay
  # available as fallbacks.
  PREPUSH_FIT_RECORDS="$(printf '%s' "$recs" | sed '/^[[:space:]]*$/d' | sort -t'|' -k1,1g)"
  prepush_select_candidate 1
}

# prepush_local_workroot LC_HOST -- the workroot of the capacity row that IS
# this host, or empty. The heavy-suite slot is a property of the HOST, not of a
# repo: two different repos pushing from the same machine must contend for the
# same lock, so the lock lives under the host's workroot rather than inside any
# one checkout.
prepush_local_workroot() {
  local lc_host row
  lc_host="$1"
  while IFS= read -r row; do
    [ -n "$row" ] || continue
    [ "$(prepush_field "$row" 2)" = "capacity" ] || continue
    if [ "$(prepush_row_hostname "$row")" = "$lc_host" ]; then
      prepush_field "$row" 8
      return 0
    fi
  done <<EOF
$(prepush_table_rows)
EOF
  return 1
}

# -----------------------------------------------------------------------------
# Exclusive slot
# -----------------------------------------------------------------------------
# mkdir(2) is the lock primitive on every host, deliberately, rather than
# flock(1): flock is ABSENT on both Macs (probed live -- .101 and .105 have no
# flock and no gtimeout), and its fd-holding idiom needs `exec {fd}<>` which
# macOS system bash 3.2 cannot parse. mkdir is atomic on every POSIX
# filesystem and works in bash 3.2, so the fleet gets ONE lock implementation
# instead of a Linux path and a Mac path that can drift.
#
# What mkdir lacks versus flock is automatic release when the holder dies, so
# the holder's pid is recorded and a lock whose holder is gone is reclaimed --
# without that, one killed run (OMN-16713: the selector gets SIGTERMed from
# outside) would wedge a host permanently.
PREPUSH_HELD_LOCK=""

# Returns 0 acquired, 1 CONTENDED (someone holds it), 2 INFRASTRUCTURAL (the
# workroot itself is unusable). Callers must not conflate them: contention is a
# real "this host is busy" signal that should send the work elsewhere, while an
# unusable workroot says nothing about capacity and must not start refusing
# pushes that passed before this lock existed.
prepush_lock_acquire() {
  local workroot lockdir holder
  workroot="$1"
  lockdir="${workroot}/LOCK"
  mkdir -p "$workroot" 2> /dev/null || return 2
  if mkdir "$lockdir" 2> /dev/null; then
    printf '%s %s %s\n' "$$" "$(hostname -s 2> /dev/null || echo unknown)" "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" \
      > "${lockdir}/holder" 2> /dev/null || true
    PREPUSH_HELD_LOCK="$lockdir"
    return 0
  fi
  # OMN-17280: a failed mkdir(2) is not automatically contention. When the
  # WORKROOT itself is not writable by this process the lockdir can never be
  # created no matter who is or is not running -- EACCES, not EEXIST. Reading
  # that as "someone holds the slot" made the caller print "this host is fit
  # but its heavy-suite slot is already held", which is measurably false and
  # sends the reader hunting for a lock that does not exist. Measured against a
  # mode-555 workroot before this line existed: rc=1 (CONTENDED). It is an
  # INFRASTRUCTURAL failure, which the callers already know how to degrade
  # through, and it is the exact shape any actor who does not own the row's
  # workroot hits on every single push.
  if [ ! -w "$workroot" ]; then
    return 2
  fi
  # Occupied. Reclaim only if the recorded holder is provably gone AND it was
  # this same machine (a pid from another host says nothing about ours).
  holder="$(cut -d' ' -f1 "${lockdir}/holder" 2> /dev/null || true)"
  if [ -n "$holder" ] && [ "$(cut -d' ' -f2 "${lockdir}/holder" 2> /dev/null || true)" = "$(hostname -s 2> /dev/null || echo unknown)" ] \
    && ! kill -0 "$holder" 2> /dev/null; then
    rm -rf "$lockdir" 2> /dev/null || true
    if mkdir "$lockdir" 2> /dev/null; then
      printf '%s %s %s\n' "$$" "$(hostname -s 2> /dev/null || echo unknown)" "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" \
        > "${lockdir}/holder" 2> /dev/null || true
      PREPUSH_HELD_LOCK="$lockdir"
      return 0
    fi
  fi
  return 1
}

prepush_lock_release() {
  [ -n "$PREPUSH_HELD_LOCK" ] || return 0
  rm -rf "$PREPUSH_HELD_LOCK" 2> /dev/null || true
  PREPUSH_HELD_LOCK=""
}

# -----------------------------------------------------------------------------
# Receipts
# -----------------------------------------------------------------------------
prepush_emit_receipt() {
  local dir
  dir="${REPO_ROOT}/.onex_state/prepush_distribution"
  mkdir -p "$dir" 2> /dev/null || return 0
  printf '%s\n' "$1" >> "${dir}/receipts.jsonl" 2> /dev/null || true
}

prepush_json_escape() {
  printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' | tr -d '\n'
}

# -----------------------------------------------------------------------------
# Actor reachability and the same-host route (OMN-17280)
# -----------------------------------------------------------------------------
# THE DEFECT THIS CLOSES, reproduced 2026-09-01 BEFORE any of it was written.
# Every `ssh_target` in the table used to carry a hardcoded `jonah@` login, so
# for any OTHER actor -- a collaborator holding his own account on `.201` --
# every remote row answered `Permission denied (publickey,password)` in under a
# second and probed `slot-unknown`. His OWN host still probed `fit`, but
# `dispatch_to_lab_host` SKIPS a self candidate (it carries no ssh target), so
# the ranked walk executed nothing, returned "no evidence", and the refusal
# ladder fell through to `die()`. A push refused on REACHABILITY while the host
# it was standing on had just been measured fit and free. Recorded verbatim
# from the reproduction driver:
#   PROBE_LOG=h200=slot-unknown h201=fit(0.10,authorizing,40000MiB,tier=last_resort)
#   WALK idx=1 label=h201 -> SKIPPED (self candidate, no ssh target)
#   CANDIDATE_COUNT=1  REMOTE_LEG_EXECUTED=0
#
# Two things close it, and neither widens the gate:
#   1. The table carries a HOST, never a login (see prepush_hosts.tsv). ssh(1)
#      resolves the user from ~/.ssh/config or the invoking account, so each
#      actor uses their OWN identity. For the owner this is a no-op -- their
#      local account name is exactly the one the table used to hardcode.
#   2. When NO capacity row is reachable BY THIS ACTOR, running the identical
#      governed suite on this host is a first-class route rather than a
#      refusal. It is reached only AFTER the lab has been asked and answered
#      nothing, so the OMN-17392 / OMN-17485 off-box preference is untouched
#      for anyone who can reach the lab: ONE reachable remote target closes
#      this route completely.
#
# What it is NOT: it is not a narrowing. The identical escalation argv runs,
# on a host the COMMITTED table designates as authorizing, with the same
# exclusive-slot serialization every other path takes. No `PREPUSH_*` override
# opens it, nothing about it can turn a red suite green, and a machine absent
# from the table is exactly as unable to authorize a heavy run as it was
# before.

# Deliberately a CONSTANT, on the same reasoning as the OMN-17392 off-box
# budget: an env indirection here would be a one-word way to force every remote
# row to read "unreachable" and so to force the local route open.
PREPUSH_REACH_CONNECT_TIMEOUT=4

# prepush_remote_reachability LC_HOST REPO -- how many capacity rows THIS ACTOR
# can actually open an ssh session to, excluding this host itself. Sets
# PREPUSH_REACHABLE_COUNT and PREPUSH_REACHABILITY_LOG (a "label=up/down" trail
# for the receipt, so a same-host run can be audited rather than believed).
#
# It is a SEPARATE probe rather than a re-reading of PREPUSH_PROBE_LOG, and
# that distinction is the point: `slot-unknown` conflates "cannot log in at
# all" with "logged in fine but could not read the workroot", and only the
# first is a statement about the actor's identity. `ssh ... true` answers
# exactly the question being asked. It runs only on the refusal path, after the
# ranked walk has already produced no verdict, so it costs nothing on a push
# that placed normally -- and against an unreachable login it is fast: measured
# 2026-09-01 against all four lab rows with a non-owner login, every one
# returned rc=255 in under a second.
prepush_remote_reachability() {
  local lc_host repo row label role mode denied name ssh_t v rc n=0 trail="" tcmd
  lc_host="$1"
  repo="$2"
  PREPUSH_REACHABLE_COUNT=0
  PREPUSH_REACHABILITY_LOG=""
  if ! prepush_load_rows; then
    PREPUSH_REACHABILITY_LOG="host-table-unreadable"
    return 1
  fi
  tcmd="$(_prepush_timeout_cmd)"
  for row in ${PREPUSH_TABLE_ROWS[@]+"${PREPUSH_TABLE_ROWS[@]}"}; do
    [ -n "$row" ] || continue
    label="$(prepush_field "$row" 1)"
    role="$(prepush_field "$row" 2)"
    mode="$(prepush_field "$row" 12)"
    [ "$role" = "capacity" ] || continue
    [ "$mode" != "disabled" ] || continue
    denied="$(prepush_field "$row" 11)"
    case ",${denied}," in
      *",${repo},"*) continue ;;
    esac
    name="$(prepush_row_hostname "$row")"
    if [ "$name" = "$lc_host" ]; then
      trail="${trail}${label}=self "
      continue
    fi
    ssh_t="$(prepush_field "$row" 4)"
    if [ -z "$ssh_t" ] || [ "$ssh_t" = "-" ]; then
      trail="${trail}${label}=no-target "
      continue
    fi
    if [ -n "${PREPUSH_REACH_OVERRIDE_MAP:-}" ]; then
      v="$(prepush_map_lookup "$PREPUSH_REACH_OVERRIDE_MAP" "$label")"
      # A `default=` key applies to every label the map does not name. The test
      # isolation fragment uses it (tests/.../_prepush_lab_isolation.py) so a
      # hook-subprocess test stays network-free on this probe even after a row
      # is ADDED to the table -- a per-label map silently stops covering the
      # new row, and the failure mode of that gap is a unit test opening a real
      # ssh connection to a lab host.
      [ -n "$v" ] || v="$(prepush_map_lookup "$PREPUSH_REACH_OVERRIDE_MAP" "default")"
      case "$v" in
        up)
          trail="${trail}${label}=up "
          n=$((n + 1))
          ;;
        *) trail="${trail}${label}=down " ;;
      esac
      continue
    fi
    # `-n` for the same reason every other ssh in this file carries it: this
    # loop's stdin is not the row list any more, but a probe that reads stdin
    # is a defect waiting for the next caller who pipes rows in.
    rc=0
    if [ -n "$tcmd" ]; then
      "$tcmd" 10 ssh -n -o ConnectTimeout="$PREPUSH_REACH_CONNECT_TIMEOUT" -o BatchMode=yes \
        -o StrictHostKeyChecking=accept-new "$ssh_t" true > /dev/null 2>&1 || rc=$?
    else
      ssh -n -o ConnectTimeout="$PREPUSH_REACH_CONNECT_TIMEOUT" -o BatchMode=yes \
        -o StrictHostKeyChecking=accept-new "$ssh_t" true > /dev/null 2>&1 || rc=$?
    fi
    if [ "$rc" -eq 0 ]; then
      trail="${trail}${label}=up "
      n=$((n + 1))
    else
      trail="${trail}${label}=down(ssh-rc-${rc}) "
    fi
  done
  PREPUSH_REACHABLE_COUNT="$n"
  PREPUSH_REACHABILITY_LOG="${trail% }"
  return 0
}

# prepush_local_actor_route HEAVY_WHAT LABEL -- 0 when the escalation may run on
# THIS host because no capacity row is reachable by THIS ACTOR, 1 otherwise.
#
# Callers place it AFTER dispatch_to_lab_host and BEFORE the override grant.
# That ordering is evidence-strength ordering, not convenience: this route
# produces a real, full, unmodified suite run on a designated authorizing host,
# which is strictly stronger than a receipted degraded-capacity grant AND does
# not consume one.
#
# It deliberately does NOT re-impose the load threshold. Load is a PLACEMENT
# preference -- it decides which of several hosts should take the work. When
# the actor has no other host at all, refusing on load produces no evidence
# whatsoever and leaves no governed route, which is precisely the pressure that
# sends people to the forbidden `PREPUSH_*` overrides. The measured load and
# memory are still read and printed, in the banner and in the receipt, so the
# degradation is visible rather than silent.
prepush_local_actor_route() {
  local heavy_what label repo lw fallback_lw lock_rc=0 measured actor head_sha ts ser rcpt
  local reading ratio memmb
  heavy_what="$1"
  label="$2"
  # Identity is still enforced. This route exists only for a host the COMMITTED
  # table designates as authorizing; a machine absent from the table is exactly
  # as unable to authorize a heavy run as it was before OMN-17280.
  [ -n "$label" ] || return 1
  repo="$(basename "$REPO_ROOT")"

  prepush_remote_reachability "$PREPUSH_LC_HOST" "$repo" || true
  if [ "${PREPUSH_REACHABLE_COUNT:-0}" -gt 0 ]; then
    # At least one lab host answers for this actor, so the refusal above was
    # about CAPACITY, not reachability, and the off-box preference stands
    # untouched. This is the branch every one of the owner's own pushes takes.
    return 1
  fi

  # Read the local measurement from host_load_ratio DIRECTLY, not through
  # prepush_probe_ratio. That wrapper has two shapes across the repos that
  # vendor this library -- one PRINTS the ratio, the OMN-17392 one sets globals
  # from a single reading -- and capturing it in a command substitution would
  # run the second shape in a SUBSHELL, discard its globals, and leave the
  # PREVIOUS candidate's numbers standing in the receipt. That is the exact
  # defect prepush_probe_ratio's own header warns about, and a receipt is the
  # worst place to reproduce it: a wrong number there reads as evidence.
  # host_load_ratio has one shape everywhere, returns everything on stdout, and
  # holds no state to lose.
  measured="unmeasured"
  reading="$(host_load_ratio "" 2> /dev/null || true)"
  ratio="$(printf '%s' "$reading" | awk '{print $3}')"
  memmb="$(printf '%s' "$reading" | awk '{print $4}')"
  if [ -n "$ratio" ]; then
    measured="load ${ratio}x"
    # The mem field is absent on the pre-OMN-17392 probe and -1 when it could
    # not be read; neither is reported as a number.
    if [ -n "$memmb" ] && [ "$memmb" != "-1" ]; then
      measured="${measured}, mem ${memmb}MiB"
    fi
  fi

  # Serialize where we can (OMN-16174). The row's workroot belongs to whoever
  # provisioned the host, so an actor without write access to it gets a
  # per-actor workroot under $HOME instead of an unserialized run -- strictly
  # better than the pre-existing rc=2 behavior, which only warned and ran.
  lw="$(prepush_local_workroot "$PREPUSH_LC_HOST" || true)"
  [ -n "$lw" ] || lw="${REPO_ROOT}/.onex_state/prepush_distribution"
  ser="serialized at ${lw}/LOCK"
  lock_rc=0
  prepush_lock_acquire "$lw" || lock_rc=$?
  if [ "$lock_rc" -eq 2 ]; then
    fallback_lw="${HOME:-/tmp}/.onex-prepush"
    lock_rc=0
    prepush_lock_acquire "$fallback_lw" || lock_rc=$?
    case "$lock_rc" in
      0) ser="serialized at ${fallback_lw}/LOCK -- the row's workroot '${lw}' is not writable by this actor" ;;
      2)
        ser="UNSERIALIZED -- neither '${lw}' nor '${fallback_lw}' is usable by this actor"
        lock_rc=0
        ;;
    esac
  fi
  if [ "$lock_rc" -ne 0 ]; then
    # A slot GENUINELY held by another run on this host is contention, not a
    # reachability problem. OMN-16174's serialization wins: decline, and let the
    # caller's existing ladder answer.
    log "SAME-HOST ROUTE declined (OMN-17280): no capacity row is reachable for this actor, but this host's heavy-suite slot ('${lw}') is genuinely held by another run. Serialization wins over convenience -- wait for that run to finish and re-push."
    return 1
  fi

  actor="$(id -un 2> /dev/null || whoami 2> /dev/null || echo unknown)"
  head_sha="$(git -C "$REPO_ROOT" rev-parse HEAD 2> /dev/null || echo unknown)"
  ts="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  log "=============================================================================="
  log "SAME-HOST ROUTE IN EFFECT (OMN-17280) -- ${heavy_what} runs ON THIS HOST."
  log "  RECEIPT route=local_actor_fallback reason=no_remote_target_reachable_for_actor"
  log "  actor='${actor}' host='${PREPUSH_LC_HOST}' row='${label}' repo='${repo}'"
  log "  reachability: ${PREPUSH_REACHABILITY_LOG:-none}"
  log "  last placement probe: ${PREPUSH_PROBE_LOG:-none}"
  log "  local measurement: ${measured}"
  log "  ${ser}"
  log "  This is NOT a bypass and NOT a narrowing: the identical governed suite"
  log "  runs here, unmodified, on a host this table designates as authorizing."
  log "  Every capacity row is unreachable for this account, so refusing would"
  log "  produce no evidence at all and leave no governed route to push through."
  log "  If you expected off-box placement, your account needs ssh access to a"
  log "  capacity row in ${PREPUSH_HOST_TABLE_REL}."
  log "=============================================================================="
  rcpt="{\"ts\":\"${ts}\",\"ticket\":\"OMN-17280\""
  rcpt="${rcpt},\"route\":\"local_actor_fallback\""
  rcpt="${rcpt},\"reason\":\"no_remote_target_reachable_for_actor\""
  rcpt="${rcpt},\"actor\":\"$(prepush_json_escape "$actor")\""
  rcpt="${rcpt},\"host\":\"$(prepush_json_escape "$PREPUSH_LC_HOST")\""
  rcpt="${rcpt},\"row\":\"$(prepush_json_escape "$label")\""
  rcpt="${rcpt},\"repo\":\"$(prepush_json_escape "$repo")\""
  rcpt="${rcpt},\"head_sha\":\"$(prepush_json_escape "$head_sha")\""
  rcpt="${rcpt},\"heavy_what\":\"$(prepush_json_escape "$heavy_what")\""
  rcpt="${rcpt},\"measured\":\"$(prepush_json_escape "$measured")\""
  rcpt="${rcpt},\"serialization\":\"$(prepush_json_escape "$ser")\""
  rcpt="${rcpt},\"reachability\":\"$(prepush_json_escape "${PREPUSH_REACHABILITY_LOG:-none}")\"}"
  prepush_emit_receipt "$rcpt"
  return 0
}

# -----------------------------------------------------------------------------
# Remote execution leg
# -----------------------------------------------------------------------------
# git bundle transplant -> scp -> clone -> uv sync -> the IDENTICAL pytest argv
# -> completion marker read back. This is the leg the hook has never had; until
# now the "other host" was probed and the answer interpolated into a refusal
# string (the old L427-433), so `.201` was reachable only by a human reading
# the die() text and hand-driving a recipe.
#
# Bundle transplant is not new machinery here: ~/push-lanes on .201 is already
# full of *.bundle files from exactly this recipe. What is new is that the HOOK
# drives it instead of a person.
#
# WHY A COMPLETION MARKER AND NOT THE SSH EXIT CODE: ssh returns 255 for a
# transport failure, which is indistinguishable from a test failure, and any
# backgrounding/nohup/tee wrapper returns 0 with nothing having run -- a
# fail-OPEN shape. The verdict is therefore a marker file written on the remote
# host carrying {head_sha, argv_sha, exit, collected, log_sha256}; absence or
# mismatch is NO EVIDENCE and falls through to refusal, never to a pass.
_prepush_sha256_sh='if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | cut -d" " -f1; else shasum -a 256 "$1" | cut -d" " -f1; fi'

prepush_sha256_file() {
  sh -c "$_prepush_sha256_sh" _ "$1" 2> /dev/null
}

# prepush_remote_gc TARGET RUNDIR WORKROOT -- reclaim the transplanted tree and
# prune stale run directories. A clone plus `uv sync --all-extras` is ~0.5 GB
# per run and nothing pruned it: two dispatches left 1.0 GB on omnibook, the
# host the picker prefers, which fills a laptop disk in a few hundred pushes and
# then starts failing runs for a reason that looks nothing like its cause. The
# small artifacts (MARKER, suite.log, sync.log) are deliberately KEPT -- they
# are the audit trail behind the receipt -- and aged out after 3 days.
prepush_remote_gc() {
  ssh -n -o ConnectTimeout=6 -o BatchMode=yes "$1" \
    "rm -rf '${2}/tree' 2>/dev/null; find '${3}/runs' -mindepth 1 -maxdepth 1 -type d -mtime +3 -exec rm -rf {} + 2>/dev/null" \
    > /dev/null 2>&1 || true
}

# -----------------------------------------------------------------------------
# The remote leg's EXECUTION POLICY (OMN-17603, ported from omnibase_infra's
# OMN-17564 abc144fe6 -- kept diffable against it: same constant names, same
# fit-record field, same min(row cores, cap) rule)
# -----------------------------------------------------------------------------
# THE DEFECT THIS CLOSES, measured live on h105 at 2026-09-02T19:24Z. The seam
# shipped the SELECTION across and dropped the EXECUTION POLICY:
# `prepush_remote_argv` emitted only test PATHS and the wrapper below ran
# `"$UV" run pytest "${ARGV[@]}" --ignore=tests/integration --tb=short` -- no
# `-n`, no `--dist`, no `--timeout`.
#
# THE NAIVE READING IS WRONG IN THIS REPO, so state the real mechanism. This is
# NOT "the parallelism config was never written": `pyproject.toml`'s
# `[tool.pytest.ini_options] addopts` ALREADY declares
# `-n4 --dist=loadgroup --timeout=60 --timeout-method=signal`. That block is
# simply NEVER READ. `tests/pytest.ini` is a real committed file whose own
# addopts is `-v --tb=short --strict-markers --disable-warnings --color=yes`,
# and both legs invoke pytest with `tests/` as the argument -- so pytest's
# rootdir/inifile discovery starts in `tests/`, finds `pytest.ini`, and STOPS.
# `pytest.ini` outranks `pyproject.toml` outright; the two do not merge. That
# is the same shadowing OMN-14967 documents, and the LOCAL leg is immune only
# because prepush_smart_tests.sh passes `PREPUSH_TIMEOUT_FLAGS` EXPLICITLY on
# the command line, where no ini file can shadow it. This leg's pytest
# invocation lives in the heredoc below rather than in that script, so
# OMN-14967's guard never covered it.
#
# MEASURED, read-only, on a live dispatched run (h105, 2026-09-02T19:24Z):
# `ps -Ao pid,ppid,pcpu,rss,etime,command` showed ONE python beneath the
# wrapper -- no execnet/gw* workers at all -- at 759,888 KB RSS and 1h49m
# elapsed, and that run's own suite.log header read
# `rootdir: .../tree/tests` / `configfile: pytest.ini` / `collected 44720
# items`. The xdist and pytest-timeout plugins were loaded and available; only
# the FLAGS were missing.
#
# The cost is not the wall clock -- it is SLOT OCCUPANCY. Every capacity row
# holds an EXCLUSIVE heavy-suite slot for the whole duration of the run, so a
# 4-5x slower run holds the scarce resource 4-5x longer. A single-threaded core
# heavy lane measured ~4h35m; the same tree under `-n4` locally runs at roughly
# 5x the tests/s. With four capacity rows in the table, that arithmetic is the
# difference between the lab being slot-starved and being merely busy.
#
# `--timeout-method=signal` is carried for the same reason OMN-15977 chose it
# locally: a thread-based watchdog cannot kill a CPU-bound pure-Python loop
# holding the GIL, so before this the OMN-15977 runaway protection covered only
# local runs and every remote leg ran unwatched.
#
# CONSTANTS, not `${VAR:-...}`. An env indirection here would be a one-word
# bypass of the policy (workers=1 restores the defect silently), and the hook
# treats a PREPUSH_* override in the environment as a HARD REFUSAL (OMN-16480).
PREPUSH_REMOTE_POLICY_FLAGS="--dist=loadgroup --timeout=60 --timeout-method=signal"

# The worker CAP. This is PARITY with the local leg, not a new parallelism
# policy: it is the worker count this repo's local heavy leg already runs
# (`PREPUSH_TIMEOUT_FLAGS="-n4 --dist=loadgroup --timeout=60
# --timeout-method=signal"` in prepush_smart_tests.sh) and the same value the
# shadowed `pyproject.toml` addopts declares. Raising it is a separate change
# and needs its own measurement -- `-n4` is also what that pyproject's own
# comment block pins as the OOM-safe ceiling ("Limited to 4 workers to prevent
# OOM").
PREPUSH_REMOTE_XDIST_WORKER_CAP=4

# LIVENESS BOUND for the execution ssh. `ConnectTimeout` governs the HANDSHAKE
# only: a leg that has already connected and then stops hearing anything (zero
# bytes, no WRAPPER_EXIT, no MARKER) holds its lane forever. Keepalives bound
# transport silence; the timeout(1) wrapper bounds the whole run, which is the
# pattern every PROBE ssh in this file already uses.
#
# 30s x 10 = 300s of unanswered keepalives before ssh gives up. The run budget
# is sized off the measured worst case for the heaviest lane in the fleet --
# the seven most recent completed heavy lanes on h201 ran 2h43m-3h06m (see that
# row's note in prepush_hosts.tsv), the
# longest recorded is 3h48m55s, and the single-threaded run this change exists
# to end was ~4h35m -- with headroom, so it only ever fires for a run that has
# already exceeded every suite this fleet has recorded.
PREPUSH_REMOTE_SSH_ALIVE_INTERVAL_SECONDS=30
PREPUSH_REMOTE_SSH_ALIVE_COUNT_MAX=10
PREPUSH_REMOTE_EXEC_TIMEOUT_SECONDS=21600

# prepush_remote_xdist_workers -- how many xdist workers the SELECTED host gets:
# min(that row's `cores`, PREPUSH_REMOTE_XDIST_WORKER_CAP).
#
# Resolved from the TARGET, never from the pushing host and never hardcoded: a
# fixed `-n4` oversubscribes a 2-core row, and the fleet spread is 10..32 cores
# today. An absent or non-numeric `cores` degrades to ONE worker -- i.e.
# exactly the behavior that shipped before this change -- rather than guessing
# headroom on a host we cannot size. That is the same fail-closed posture the
# load, slot and uv probes already carry: unreadable is never "assume ample".
prepush_remote_xdist_workers() {
  local cores="${PREPUSH_PICK_CORES:-}"
  case "$cores" in '' | *[!0-9]*) printf '1'; return 0 ;; esac
  [ "$cores" -ge 1 ] 2> /dev/null || { printf '1'; return 0; }
  if [ "$cores" -lt "$PREPUSH_REMOTE_XDIST_WORKER_CAP" ]; then
    printf '%s' "$cores"
  else
    printf '%s' "$PREPUSH_REMOTE_XDIST_WORKER_CAP"
  fi
  return 0
}

# prepush_remote_pytest_flags -- the execution policy, one item per line, in the
# same shape prepush_remote_argv writes so the two concatenate into one argv
# file. Deliberately SEPARATE from prepush_remote_argv: that function is the
# SELECTION and the receipt records its output verbatim under
# `selection_paths`, so folding flags into it would make an audit of "what did
# that host actually run" read execution flags as coverage.
prepush_remote_pytest_flags() {
  printf '%s\n' "-n$(prepush_remote_xdist_workers)"
  # shellcheck disable=SC2086
  printf '%s\n' $PREPUSH_REMOTE_POLICY_FLAGS
}

# prepush_remote_argv -- the SELECTION this call site would have run locally,
# one path per line. Execution POLICY (parallelism, the per-test watchdog) is
# emitted separately by prepush_remote_pytest_flags above and appended to the
# same argv file; keeping them apart is what lets the receipt record coverage
# and policy as two distinct facts.
#
# The two local call sites carry DIFFERENT selections and
# conflating them would be a silent coverage downgrade: the heavy site runs
# $FULL_SUITE_TARGET **plus** ${RUNNABLE_INTEGRATION_PATHS[@]} to satisfy
# OMN-16825's "an escalation must never run FEWER of the impacted tests than
# the narrowing it replaces" invariant, while the whole-suite-equivalent narrow
# site runs ${PATHS[@]}. Shipping only tests/unit/ would silently drop
# tests/integration/chains/, a required Event Chain Gate surface, with no test
# firing.
prepush_remote_argv() {
  if [ "${IS_FULL:-}" = "True" ] || [ "${IS_FULL:-}" = "true" ]; then
    printf '%s\n' "$FULL_SUITE_TARGET"
    if [ "${#RUNNABLE_INTEGRATION_PATHS[@]}" -gt 0 ]; then
      printf '%s\n' "${RUNNABLE_INTEGRATION_PATHS[@]}"
    fi
  else
    if [ "${#PATHS[@]}" -gt 0 ]; then
      printf '%s\n' "${PATHS[@]}"
    fi
  fi
}

# -----------------------------------------------------------------------------
# Tree transport -- the bundle MUST carry the TAG STATE (OMN-17240)
# -----------------------------------------------------------------------------
# This leg used to build its transplant with `git bundle create "$bundle" HEAD`,
# which packs only the commits reachable from HEAD and NO ref under refs/tags/.
# Every remote clone, on every host, on every push, therefore had ZERO tags --
# and scripts/check_release_identity.py derives "the latest published version"
# from `git tag --list`. With no tags it silently took its "no published tag
# yet" branch, so three tests that assert the version-ahead message went red on
# the remote host while passing locally at the identical SHA (first seen on h101
# at OMN-17139's 47d7da183: 3 failed / 25618 passed remotely, 9 passed in 16.65s
# locally).
#
# Appending `--tags` alone is NOT the fix, and on a SHALLOW source it is worse
# than the defect. Measured on the canonical omnibase_infra clone before this
# change (97 tags, 576-commit graft): `git bundle create f HEAD --tags` exits 0
# and writes a bundle whose header lists all 97 tag refs, but cloning it dies --
#   error: Could not read 52222775d8563c036b7f9e15737573c95aa2ce18
#   fatal: remote did not send all necessary objects
# -- because the tags' ancestry lies beyond the graft. That converts a false red
# into a hard transport failure on every push, after paying the transfer.
#
# So the transport proves each step instead of assuming it: the source must be
# able to bundle tag ancestry at all (unshallow once when it cannot -- additive,
# ~8 s, and it is the object store the worktrees share), the bundle is written
# with HEAD *and* the tags, and the WRITTEN bundle is then read back and proven
# to carry tag refs before it is shipped. Anything unprovable returns 1 -- "no
# evidence" -- which sends the caller back to its existing precedence. No path
# here can make the gate accept less work, and none of the tag state comes from
# a caller-written file or env var: it is read from git refs the remote leg
# re-derives for itself after the clone.
#
# Wire cost, measured on omnibase_infra 2026-08-30:
#   shallow HEAD-only  (the broken transport)  18,599,149 B
#   unshallowed HEAD-only                      33,657,408 B
#   unshallowed HEAD --tags  (shipped)         33,966,130 B
# The tag refs themselves cost 308,722 B (+0.9%); the one-time unshallow is the
# rest (+15.1 MB on the wire, 65.9 -> 101.8 MiB packed on disk).
prepush_bundle_tree() {
  local repo_root bundle src_tags bundle_tags
  repo_root="$1"
  bundle="$2"

  src_tags="$(git -C "$repo_root" tag --list 2> /dev/null | wc -l | tr -d ' ')"
  [ -n "$src_tags" ] || src_tags=0

  if [ "$(git -C "$repo_root" rev-parse --is-shallow-repository 2> /dev/null)" = "true" ]; then
    log "remote leg: source clone is SHALLOW -- unshallowing once so tag ancestry can be bundled (OMN-17240)"
    if ! git -C "$repo_root" fetch --unshallow --tags > /dev/null 2>&1; then
      log "remote leg: refusing -- cannot unshallow ${repo_root}, and a shallow source cannot bundle its tags. Shipping a tag-less tree would make the release-identity gate fail OPEN on the remote host (OMN-17240)."
      rm -f "$bundle" 2> /dev/null || true
      return 1
    fi
    src_tags="$(git -C "$repo_root" tag --list 2> /dev/null | wc -l | tr -d ' ')"
    [ -n "$src_tags" ] || src_tags=0
  fi

  if ! git -C "$repo_root" bundle create "$bundle" HEAD --tags > /dev/null 2>&1; then
    rm -f "$bundle" 2> /dev/null || true
    return 1
  fi

  # Read the written bundle back. `git bundle create` reports success for a
  # bundle it could not fully populate, so "it exited 0" is not evidence that
  # the tags travelled.
  if [ "$src_tags" -gt 0 ]; then
    bundle_tags="$(git -C "$repo_root" bundle list-heads "$bundle" 2> /dev/null | grep -c 'refs/tags/')"
    [ -n "$bundle_tags" ] || bundle_tags=0
    if [ "$bundle_tags" -eq 0 ]; then
      log "remote leg: refusing -- the bundle carries 0 of ${src_tags} tag refs, so the remote tree would evaluate release identity against an empty tag set (OMN-17240)"
      rm -f "$bundle" 2> /dev/null || true
      return 1
    fi
    log "remote leg: bundle carries ${bundle_tags} of ${src_tags} tag refs"
  fi
  return 0
}

# prepush_remote_run -- executes the suite on the picked host.
# Returns 0 = GREEN (verdict may be used), 1 = NO EVIDENCE (fall through),
# 3 = RED (the suite genuinely failed on a designated host; the caller MUST
# refuse the push rather than fall through to an override grant -- a remote red
# falling through to a grant would be a bypass wearing the word "fallback"),
# 4 = the target's heavy-suite SLOT was taken on arrival (no suite ran; the
# caller should try the next ranked host rather than refuse).
prepush_remote_run() {
  local heavy_what repo head_sha runid workroot ssh_t uv label rundir
  local bundle argvfile runner localdir marker rc=0 argv_sha log_sha
  local m_exit m_head m_argv m_log m_collected started ended dur
  local readback wrapper_exit base_ref base_sha slot_idx remote_cmd tcmd
  heavy_what="$1"
  # Resolved by the hook before it ever reaches here; empty in a driver that
  # exercises the library alone, which the wrapper handles as "skip".
  base_ref="${BASE_REF:-}"
  base_sha="${BASE_SHA:-}"
  repo="$(basename "$REPO_ROOT")"
  head_sha="$(git -C "$REPO_ROOT" rev-parse HEAD 2> /dev/null || true)"
  [ -n "$head_sha" ] || return 1
  label="$PREPUSH_PICK_LABEL"
  ssh_t="$PREPUSH_PICK_SSH"
  uv="$PREPUSH_PICK_UV"
  workroot="$PREPUSH_PICK_WORKROOT"
  slot_idx="${PREPUSH_PICK_SLOT:-1}"
  [ -n "$ssh_t" ] || return 1
  runid="${repo}-$(printf '%s' "$head_sha" | cut -c1-12)-$$"
  rundir="${workroot}/runs/${runid}"

  localdir="$(mktemp -d 2> /dev/null)" || return 1
  bundle="${localdir}/tree.bundle"
  argvfile="${localdir}/argv.txt"
  runner="${localdir}/prepush_smart_tests.sh"

  if ! prepush_bundle_tree "$REPO_ROOT" "$bundle"; then
    log "remote leg: could not create a tag-carrying git bundle for ${head_sha}"
    rm -rf "$localdir"
    return 1
  fi
  prepush_remote_argv > "$argvfile"
  # The "nothing selected" refusal is decided on PATHS ALONE, before any flag is
  # written (OMN-17603). Appending the policy first would make an empty
  # selection look runnable: pytest handed nothing but flags falls back to the
  # transplanted tree's own `testpaths` (tests/pytest.ini declares
  # `testpaths = unit integration`), silently running a suite nobody selected
  # and reporting it as this push's evidence.
  if [ ! -s "$argvfile" ]; then
    rm -rf "$localdir"
    return 1
  fi
  # The execution policy travels WITH the selection, in the same file, so it is
  # covered by argv_sha -- the marker binds the verdict to the flags the suite
  # actually ran under, not just to the paths. A host that answered under a
  # different policy therefore cannot satisfy this dispatch.
  prepush_remote_pytest_flags >> "$argvfile"
  argv_sha="$(prepush_sha256_file "$argvfile")"

  # The remote wrapper is NAMED prepush_smart_tests.sh on purpose. .201's queue
  # runner gates every lane on `ps ax | grep prepush_smart_tests.sh` ("no other
  # heavy prepush running host-wide, covers foreign runs not launched through
  # this queue"). Matching that name makes THIS run visible to the queue's own
  # existing enforcement surface, so the queue and this leg share one mutex
  # instead of the leg becoming another foreign detached run -- the exact
  # defect class OMN-16968 is open against. It also makes the run visible to
  # prepush_slot_state above, so a second dispatcher sees the host as busy.
  cat > "$runner" <<'REMOTE'
#!/usr/bin/env bash
set -uo pipefail
RUNDIR="$1"; UV="$2"; HEAD_SHA="$3"; ARGV_SHA="$4"; ORIGIN="$5"; WORKROOT="$6"
BASE_REF="${7:-}"; BASE_SHA="${8:-}"; SLOT_INDEX="${9:-1}"
# The repo this bundle carries, so the registry root below can name it. Passed
# rather than derived: RUNDIR's basename is `<repo>-<sha12>-<pid>` and repo
# names contain both separators, so splitting it back apart is guesswork.
REPO_NAME="${10:-}"
cd "$RUNDIR" || exit 90
# Re-arm BOTH guards explicitly. ssh forwards neither, so without this the
# remote repo's own suite -- which subprocesses this very hook from
# tests/ci/test_prepush_hook_host_identity_guard.py and siblings -- would take
# FIRST-entry behavior on the remote host, resolve the selector, pick a host
# and ship another bundle: an unbounded DISTRIBUTED variant of the
# OMN-16425/OMN-16489 F-01 recursion (~9h03m, 44,064 tests) the sentinel exists
# to stop.
for v in $(env | sed -n 's/^\(PREPUSH_[A-Za-z0-9_]*\)=.*/\1/p'); do unset "$v" || true; done
unset ENABLE_SMART_TESTS || true
export ONEX_PREPUSH_HOOK_ACTIVE="remote-leg:${ORIGIN}"

# PATH PARITY WITH A DEVELOPER SHELL. A non-interactive ssh session gets a
# minimal PATH -- on omnibook literally `/usr/bin:/bin:/usr/sbin:/sbin`, with
# neither the Homebrew prefix nor ~/.local/bin on it. The suite shells out to
# tools by BARE NAME (`uv` in tests/unit/infra/test_catalog_cli.py, `shellcheck`
# in the shell-hygiene gate tests), so without this a transplanted run fails in
# ways the same tree never fails locally: the first full-suite dispatch to
# omnibook returned 8 reds, every one a FileNotFoundError for a tool that WAS
# installed on that host, just not on the ssh PATH. A false red here HARD-BLOCKS
# a push, so this is part of the verdict meaning anything -- not a convenience.
#
# The list below was macOS-only by construction (OMN-16989): `/opt/homebrew/bin`
# has no meaning on a Linux row, and the fleet's only Linux capacity row is
# h201. Measured there non-interactively 2026-08-30, `ssh jonah@192.168.86.201
# 'echo $PATH'` prints
# `/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games:/snap/bin`
# -- `~/.local/bin` is absent, and BOTH `uv` and `shellcheck` live there, so the
# `$(dirname "$UV")` and `~/.local/bin` entries already covered that host (a
# full tests/unit/ dispatch to it returned zero tool-missing reds). The Linux
# analogues of the Homebrew prefix are appended AFTER every measured entry, so
# they can only add resolution and never shadow a tool that already resolves.
PATH="$(dirname "$UV"):/opt/homebrew/bin:/usr/local/bin:${HOME:-}/.local/bin:/home/linuxbrew/.linuxbrew/bin:/snap/bin:${HOME:-}/.cargo/bin:${PATH}"
export PATH

ARGV=()
while IFS= read -r line; do [ -n "$line" ] && ARGV+=("$line"); done < "$RUNDIR/argv.txt"
[ "${#ARGV[@]}" -gt 0 ] || exit 91

# THE TARGET HOST'S EXCLUSIVE HEAVY-SUITE SLOT (OMN-16991 verify finding 2).
# The dispatcher's pre-flight probe can only observe the slot; between that
# observation and this point another dispatcher -- or a local push on this very
# machine -- can take it. The lock is therefore acquired HERE, on the target, by
# the process that is about to burn the host's cores, and released when that
# process exits. Before this the remote leg took no lock at all: a local heavy
# push on .200/.201 could start while a transplanted suite was mid-run there,
# which is the OMN-16174 overlap reopened across the local/remote boundary.
#
# Same primitive and same reclaim rule as prepush_lock_acquire in
# prepush_dispatch.sh: mkdir(2) (flock(1) is absent on both Macs and its fd
# idiom needs `exec {fd}<>`, unparseable by bash 3.2), plus dead-holder reclaim
# so one externally-SIGTERMed run cannot wedge the host forever. The holder pid
# is written by THIS process on THIS host, so `kill -0` is a meaningful
# liveness check here -- the machine name is still recorded and compared, so a
# holder record from anywhere else is never reaped.
#
# SLOT-AWARE (OMN-17269): SLOT_INDEX names WHICH of the row's declared slots
# this dispatch was ranked into. Slot 1 keeps the pre-existing bare LOCK path
# (byte-identical for every host that only ever has slot 1), so this is a
# no-op for every pre-OMN-17269 dispatch; slot k>=2 gets its own LOCK.<k>,
# letting a second concurrent lane hold its own exclusive lock on the same
# host without contending slot 1's.
LOCKDIR="$WORKROOT/LOCK"
[ "$SLOT_INDEX" = "1" ] || LOCKDIR="$WORKROOT/LOCK.$SLOT_INDEX"
SELF_HOST="$(hostname -s 2> /dev/null || echo unknown)"
mkdir -p "$WORKROOT" 2> /dev/null || true
_lock_acquire() {
  if mkdir "$LOCKDIR" 2> /dev/null; then return 0; fi
  local hpid hhost
  hpid="$(cut -d' ' -f1 "$LOCKDIR/holder" 2> /dev/null || true)"
  hhost="$(cut -d' ' -f2 "$LOCKDIR/holder" 2> /dev/null || true)"
  if [ -n "$hpid" ] && [ "$hhost" = "$SELF_HOST" ] && ! kill -0 "$hpid" 2> /dev/null; then
    rm -rf "$LOCKDIR" 2> /dev/null || true
    if mkdir "$LOCKDIR" 2> /dev/null; then return 0; fi
  fi
  return 1
}
if ! _lock_acquire; then
  echo "REMOTE_LOCK_CONTENDED holder=$(cat "$LOCKDIR/holder" 2> /dev/null || echo unknown)" >&2
  exit 94
fi
printf '%s %s %s\n' "$$" "$SELF_HOST" "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" \
  > "$LOCKDIR/holder" 2> /dev/null || true
trap 'rm -rf "$LOCKDIR" 2> /dev/null || true' EXIT

# Materialize the transplanted tree INSIDE the lock: the clone and `uv sync`
# are themselves heavy (~0.5 GB and minutes of I/O), so doing them outside it
# would leave the very contention this lock exists to prevent.
rm -rf "$RUNDIR/tree" 2> /dev/null || true
git clone -q "$RUNDIR/tree.bundle" "$RUNDIR/tree" > /dev/null 2>&1 || exit 95
cd "$RUNDIR/tree" || exit 92
git checkout -q "$HEAD_SHA" 2> /dev/null || true

# THE TRANSPLANTED TREE MUST RESOLVE THE SAME BASE REF THE SOURCE TREE DID
# (OMN-16989). `git bundle create <b> HEAD` carries HEAD's objects and exactly
# one ref, so the clone has no `origin/dev` -- OMN-17240 added `--tags`, so
# `refs/tags/*` now travels too, but remote-tracking BRANCH refs still do not,
# and this update-ref is still required. This suite contains tests
# that SUBPROCESS this very hook, which resolves `${PREPUSH_BASE_REF:-origin/dev}`
# before it does anything else. Measured on h201: the whole
# tests/ci/test_prepush_hook_host_identity_guard.py behavioral proof reduced to
# `ERROR: base ref 'origin/dev' could not be resolved`, a red that says nothing
# about the tree under test and everything about the transplant. That is the
# same false-red class as the PATH gap above: the verdict has to mean the code
# failed, not that the host is not a developer checkout.
#
# BASE_SHA is `git merge-base ${BASE_REF} HEAD` on the origin side, so it is an
# ancestor of HEAD and its objects are already in the bundle -- only the REF is
# missing, and creating it is a local, network-free `update-ref`. Absent or
# unresolvable, this is skipped silently: it may only add resolution, never
# refuse a run.
if [ -n "$BASE_REF" ] && [ -n "$BASE_SHA" ] && git rev-parse --verify --quiet "${BASE_SHA}^{commit}" > /dev/null 2>&1; then
  git update-ref "refs/remotes/origin/${BASE_REF#origin/}" "$BASE_SHA" 2> /dev/null || true
fi
# THE TRANSPLANTED TREE NEEDS A REGISTRY ROOT (OMN-17741).
# `ssh` forwards no environment, so without this the suite runs with OMNI_HOME
# UNSET on every target host. Code that resolves a workspace then either fails,
# or -- the case actually measured -- falls back to a home-relative default
# that EXISTS on the lab Macs and is TCC-denied to `sshd`. OMN-17459 recorded
# that shape: a real full suite on h101, 17,883 tests in 13m58s, 12 failures,
# ALL 12 green locally, one root cause. Same standing as the PATH block above
# -- a false red here HARD-BLOCKS a push, so this is part of the verdict
# meaning anything, not a convenience.
#
# The value is CONSTRUCTED HERE, never forwarded. Exporting the launcher's
# `$OMNI_HOME` would be strictly worse than leaving it unset: that path exists
# on every lab Mac and is TCC-denied, so forwarding converts a fail-fast into a
# PermissionError deep inside a test. What is true of a transplant is that it
# contains exactly ONE repo, so a one-entry registry naming that repo is an
# honest workspace root and a lie about nothing. It is the same shape a
# vendoring repo's own aislop-sweep smoke test already builds for itself (a
# tmpdir plus a symlink to the repo under its own name).
#
# It lives under $RUNDIR, so `prepush_remote_gc` already sweeps it and this
# adds no new class of stranded state. Failure to build it exits 98 -- an
# unhandled wrapper exit produces no MARKER, which the dispatcher classifies as
# "NO EVIDENCE" and walks past to the next fit host. That is the correct
# classification: a workspace that could not be created on the TARGET says
# nothing about the tree under test.
[ -n "$REPO_NAME" ] || { echo "NO_REPO_NAME_FOR_REGISTRY_ROOT" >&2; exit 98; }
rm -rf "$RUNDIR/omni_home" 2> /dev/null || true
mkdir -p "$RUNDIR/omni_home" || { echo "REGISTRY_ROOT_MKDIR_FAILED" >&2; exit 98; }
ln -s "$RUNDIR/tree" "$RUNDIR/omni_home/$REPO_NAME" || { echo "REGISTRY_ROOT_LINK_FAILED" >&2; exit 98; }
OMNI_HOME="$RUNDIR/omni_home"
export OMNI_HOME

"$UV" sync --all-extras > "$RUNDIR/sync.log" 2>&1 || { echo "UV_SYNC_FAILED" >&2; exit 93; }
# THE COLLECTED COUNT IS READ FROM A MACHINE-READABLE REPORT (OMN-17787).
# `--junitxml` is asked for HERE, next to the invocation, because the count it
# yields is the only number in the whole dispatch that separates "this host ran
# the selection green" from "this host ran NOTHING and exited 0".
#
# THE DEFECT THIS CLOSES, measured 2026-09-04 by reading this repo's own run
# dirs on h101 and h105 (/Users/Shared/onex-prepush/runs/) read-only. EVERY run
# dir present for this repo on either host recorded `collected=0` -- serial and
# parallel alike, over suites of ~44,700 passing tests:
#
#   <repo>-378075e85050-2669   SERIAL, 3:57:27
#     suite.log:9  ESC[1mcollecting ... ESC[0mcollected 44730 items / 4 skipped
#     MARKER       exit=0  collected=0
#   <repo>-d839c27cb88a-83571  -n4 --dist=loadgroup, 1:34:58, 44683 passed
#     suite.log:13 4 workers [44741 items]
#     MARKER       exit=0  collected=0
#
# TWO INDEPENDENT CAUSES, and the upstream copy of this file has only the first:
#
#   1. `pytest-xdist` 3.8.0 REPLACES the collector banner with the worker
#      banner, so `^collected N items` matches nothing. Since OMN-17603 made
#      `-n<k> --dist=loadgroup` the remote policy here, that is every parallel
#      dispatch.
#   2. The SERIAL banner does not match either, and never has. `tests/pytest.ini`
#      addopts carries `--color=yes` and this leg's rootdir resolves into
#      `tests/`, so the banner arrives as
#      `ESC[1mcollecting ... ESC[0mcollected 44730 items / 4 skipped`. That line
#      does not BEGIN with `collected`, so the `^` anchor fails. Upstream ships
#      no `tests/pytest.ini`, so its banner is uncolored and its fallback works.
#
# A banner is a HUMAN-READABLE artifact whose shape is decided by whichever
# plugins are loaded and whether color is on; the JUnit document is not, and it
# is identical serial, parallel and colorized. The two banner forms are kept as
# ordered fallbacks -- now read through a normalizer, so cause 2 cannot make
# them inert -- so a host that somehow cannot write the report degrades to
# banner accuracy rather than to a zero. And a zero is now NO EVIDENCE at the
# acceptance branch, so every path here fails CLOSED.
#
# The report lands in $RUNDIR beside MARKER/suite.log, so `prepush_remote_gc`
# already sweeps it on the same 3-day rule and this strands no new state.
"$UV" run pytest "${ARGV[@]}" --ignore=tests/integration --tb=short \
  --junitxml="$RUNDIR/junit.xml" > "$RUNDIR/suite.log" 2>&1
rc=$?
if command -v sha256sum > /dev/null 2>&1; then
  LOGSHA=$(sha256sum "$RUNDIR/suite.log" | cut -d" " -f1)
else
  LOGSHA=$(shasum -a 256 "$RUNDIR/suite.log" | cut -d" " -f1)
fi
# Normalize BEFORE any banner is read: strip SGR colour codes and turn CR
# progress writes into newlines, so every `^` below anchors on a real start of
# line. Without this the colorized collector banner (cause 2 above) is
# unreachable by any anchored expression. The ESC byte is materialized with
# printf rather than written as `\x1b`, which BSD sed does not understand.
ESC_SGR=$(printf '\033')
prepush_banner_stream() {
  tr '\r' '\n' < "$RUNDIR/suite.log" | sed "s/${ESC_SGR}\[[0-9;]*[a-zA-Z]//g"
}
COLLECTED=""
if [ -s "$RUNDIR/junit.xml" ]; then
  COLLECTED=$(sed -n 's/.*<testsuite [^>]*tests="\([0-9][0-9]*\)".*/\1/p' "$RUNDIR/junit.xml" | head -1)
fi
[ -n "$COLLECTED" ] || COLLECTED=$(prepush_banner_stream |
  sed -n 's/^[0-9][0-9]* workers \[\([0-9][0-9]*\) item.*/\1/p' | tail -1)
# Both serial forms in one pass, each anchored: the bare banner, and the
# `collecting ... collected N items` form the status line leaves behind once the
# colour codes are stripped. `collecting [^A-Za-z]*collected` is deliberately
# tight -- only the dots and spaces pytest writes may sit between the two words
# -- so a test id such as `...::test_absent-not_collected` cannot be read as a
# count.
[ -n "$COLLECTED" ] || COLLECTED=$(prepush_banner_stream |
  sed -n -e 's/^collected \([0-9][0-9]*\) item.*/\1/p' \
         -e 's/^collecting [^A-Za-z]*collected \([0-9][0-9]*\) item.*/\1/p' | tail -1)
[ -n "$COLLECTED" ] || COLLECTED=0
{
  echo "head_sha=$HEAD_SHA"
  echo "argv_sha=$ARGV_SHA"
  echo "exit=$rc"
  echo "collected=$COLLECTED"
  echo "log_sha256=$LOGSHA"
  echo "host=$(hostname)"
} > "$RUNDIR/MARKER"
exit "$rc"
REMOTE

  log "remote leg: dispatching ${heavy_what} to ${label} (${PREPUSH_PICK_HOSTNAME}, ratio ${PREPUSH_PICK_RATIO}, mode ${PREPUSH_PICK_MODE})"
  log "remote leg: probed -> ${PREPUSH_PROBE_LOG}"
  # OMN-17603: the execution policy is on the record, not implied. A run that is
  # slower than the fleet's measured norm can now be read back to the exact
  # worker count it was given instead of being guessed at from wall clock.
  log "remote leg: pytest policy -> $(prepush_remote_pytest_flags | tr '\n' ' ')(${PREPUSH_PICK_CORES:-unknown} cores declared, cap ${PREPUSH_REMOTE_XDIST_WORKER_CAP})"
  started="$(date -u '+%s')"

  if ! ssh -n -o ConnectTimeout=6 -o BatchMode=yes -o StrictHostKeyChecking=accept-new "$ssh_t" \
    "mkdir -p '${rundir}'" > /dev/null 2>&1; then
    log "remote leg: could not create ${rundir} on ${label}"
    rm -rf "$localdir"
    return 1
  fi
  if ! scp -q -o ConnectTimeout=6 -o BatchMode=yes "$bundle" "$argvfile" "$runner" "${ssh_t}:${rundir}/" > /dev/null 2>&1; then
    log "remote leg: transfer to ${label} failed"
    rm -rf "$localdir"
    return 1
  fi

  # Stream the remote suite back as it runs, prefixed, so a distributed run is
  # no less observable than a local one. The wrapper's own exit code is written
  # to a file rather than inferred from this pipeline: the pipeline's status is
  # sed's, and the pipe is what makes the run observable, so the two cannot be
  # the same value.
  #
  # NO `set -e` in the remote command, deliberately: under it a failing (or
  # slot-contended, exit 94) wrapper aborts the remote shell BEFORE `rc=$?`
  # runs, so the one fact this leg needs -- WHY the wrapper stopped -- would be
  # the fact that never gets written. Each step is checked explicitly instead.
  #
  # LIVENESS (OMN-17603). This was the ONLY ssh in this file with no bound but
  # ConnectTimeout, which governs the handshake alone -- so a host that wedged
  # AFTER connecting held the lane forever (zero bytes, no WRAPPER_EXIT, no
  # MARKER, and the lane never recovered because the parent chain was alive and
  # nothing would ever time it out). Keepalives bound transport silence and the
  # timeout(1) wrapper bounds the run, the same pattern the probe legs above
  # already use.
  #
  # Expiry introduces NO new classification: the pipeline just returns, the
  # readback below finds no MARKER, and the leg is already classified
  # "NO completion marker ... NO EVIDENCE (not a pass, not a failure)", which
  # dispatch_to_lab_host treats as a placement miss and walks past. Fail-closed
  # posture is unchanged -- a genuine remote RED still carries a marker and
  # still refuses the push.
  remote_cmd="cd '${rundir}' || exit 96; chmod +x prepush_smart_tests.sh || exit 97; ./prepush_smart_tests.sh '${rundir}' '${uv}' '${head_sha}' '${argv_sha}' '$(hostname -s 2> /dev/null || echo unknown):$$' '${workroot}' '${base_ref}' '${base_sha}' '${slot_idx}' '${repo}'; rc=\$?; echo REMOTE_WRAPPER_EXIT=\$rc; echo \$rc > '${rundir}/WRAPPER_EXIT'; exit 0"
  tcmd="$(_prepush_timeout_cmd)"
  if [ -n "$tcmd" ]; then
    "$tcmd" "$PREPUSH_REMOTE_EXEC_TIMEOUT_SECONDS" \
      ssh -n -o ConnectTimeout=6 \
      -o "ServerAliveInterval=${PREPUSH_REMOTE_SSH_ALIVE_INTERVAL_SECONDS}" \
      -o "ServerAliveCountMax=${PREPUSH_REMOTE_SSH_ALIVE_COUNT_MAX}" \
      -o BatchMode=yes -o StrictHostKeyChecking=accept-new "$ssh_t" \
      "$remote_cmd" 2>&1 |
      sed "s/^/[${label}] /" >&2 || true
  else
    # timeout(1) ships on neither Mac in this fleet by default (see
    # _prepush_timeout_cmd). Its absence degrades to the keepalive bound alone,
    # which still closes the wedged-host case, rather than refusing to dispatch.
    ssh -n -o ConnectTimeout=6 \
      -o "ServerAliveInterval=${PREPUSH_REMOTE_SSH_ALIVE_INTERVAL_SECONDS}" \
      -o "ServerAliveCountMax=${PREPUSH_REMOTE_SSH_ALIVE_COUNT_MAX}" \
      -o BatchMode=yes -o StrictHostKeyChecking=accept-new "$ssh_t" \
      "$remote_cmd" 2>&1 |
      sed "s/^/[${label}] /" >&2 || true
  fi

  readback="$(ssh -n -o ConnectTimeout=6 -o BatchMode=yes "$ssh_t" \
    "echo \"wrapper_exit=\$(cat '${rundir}/WRAPPER_EXIT' 2>/dev/null)\"; cat '${rundir}/MARKER' 2>/dev/null" 2> /dev/null || true)"
  ended="$(date -u '+%s')"
  dur=$((ended - started))
  rm -rf "$localdir"

  wrapper_exit="$(printf '%s\n' "$readback" | sed -n 's/^wrapper_exit=//p' | head -1)"
  marker="$(printf '%s\n' "$readback" | sed -e '/^wrapper_exit=/d')"

  # Exit 94 is the wrapper reporting that the target's heavy-suite slot was
  # already held when it arrived. NO suite ran, so this is not evidence of
  # anything about the tree -- it is a placement miss, and the caller should
  # try the next ranked host instead of refusing the push.
  if [ "${wrapper_exit:-}" = "94" ]; then
    log "remote leg: ${label}'s heavy-suite slot was taken on arrival -- no suite ran there"
    prepush_remote_gc "$ssh_t" "$rundir" "$workroot"
    return 4
  fi

  if [ -z "$marker" ]; then
    log "remote leg: NO completion marker from ${label} (wrapper exit ${wrapper_exit:-unknown}) -- treating as NO EVIDENCE (not a pass, not a failure)"
    prepush_remote_gc "$ssh_t" "$rundir" "$workroot"
    return 1
  fi
  m_head="$(printf '%s\n' "$marker" | sed -n 's/^head_sha=//p')"
  m_argv="$(printf '%s\n' "$marker" | sed -n 's/^argv_sha=//p')"
  m_exit="$(printf '%s\n' "$marker" | sed -n 's/^exit=//p')"
  m_collected="$(printf '%s\n' "$marker" | sed -n 's/^collected=//p')"
  # OMN-17787: the marker is REMOTE input, so the count is normalized to a
  # number BEFORE it is compared or interpolated. `[ "$m_collected" -eq 0 ]` on
  # a non-numeric value is a bash ERROR whose status is 2 -- which reads as
  # "not zero" and falls straight through into the PASS branch -- and the same
  # value is interpolated unquoted into the receipt's JSON below, where garbage
  # produces a receipt that will not parse.
  case "$m_collected" in
    '' | *[!0-9]*) m_collected=0 ;;
  esac
  m_log="$(printf '%s\n' "$marker" | sed -n 's/^log_sha256=//p')"
  if [ "$m_head" != "$head_sha" ] || [ "$m_argv" != "$argv_sha" ] || [ -z "$m_exit" ] || [ -z "$m_log" ]; then
    log "remote leg: marker from ${label} does not bind to this tree/argv -- NO EVIDENCE"
    prepush_remote_gc "$ssh_t" "$rundir" "$workroot"
    return 1
  fi
  log_sha="$m_log"

  prepush_emit_receipt "{\"ts\":\"$(date -u '+%Y-%m-%dT%H:%M:%SZ')\",\"repo\":\"$(prepush_json_escape "$repo")\",\"head_sha\":\"${head_sha}\",\"chosen_host\":\"$(prepush_json_escape "$PREPUSH_PICK_HOSTNAME")\",\"chosen_label\":\"${label}\",\"chosen_slot\":${slot_idx},\"host_mode\":\"${PREPUSH_PICK_MODE}\",\"host_load_ratio\":\"${PREPUSH_PICK_RATIO}\",\"all_probed_ratios\":\"$(prepush_json_escape "$PREPUSH_PROBE_LOG")\",\"selection_paths\":\"$(prepush_json_escape "$(prepush_remote_argv | tr '\n' ' ')")\",\"pytest_policy\":\"$(prepush_json_escape "$(prepush_remote_pytest_flags | tr '\n' ' ')")\",\"pytest_exit\":${m_exit},\"collected\":${m_collected:-0},\"duration_s\":${dur},\"suite_log_sha256\":\"${log_sha}\"}"

  # A COUNT OF ZERO IS NO EVIDENCE, NOT A PASS (OMN-17787).
  #
  # Acceptance used to be exit-code-only: `m_collected` was logged, written into
  # the durable receipt, and never compared to anything. A remote run that
  # collected genuinely ZERO tests and exited 0 was therefore accepted as a
  # PASS and satisfied the escalation -- and the sentence it printed,
  # "${label} ran 0 tests green", is byte-identical to the one the banner
  # parsing defect produced for a run of 44,683 real tests. The gate could not
  # tell the two apart, so it treated both as evidence. In this repo that was
  # not an occasional confusion: the count was zero on every remote run.
  #
  # NO EVIDENCE (rc 1), deliberately, and NOT a refusal (rc 3): an empty
  # selection says nothing about the tree. `dispatch_to_lab_host` walks to the
  # next fit host on rc 1 and, if none answers, falls through to the
  # local/same-host/grant ladder that ends in die() -- so this is fail-CLOSED
  # without turning a placement miss into a red gate.
  #
  # pytest exit 5 is EXIT_NOTESTSCOLLECTED and is folded in here for the same
  # reason: it means nothing ran, which is the same statement about the tree as
  # a missing marker. It used to return 3 and die() the push. Every OTHER
  # non-zero exit stays a RED -- a collection ERROR is exit 2, not 5, and must
  # still refuse.
  if [ "$m_collected" -eq 0 ] && { [ "$m_exit" -eq 0 ] || [ "$m_exit" -eq 5 ]; }; then
    log "remote leg: ${label} recorded ZERO collected tests (pytest exit ${m_exit}) on ${head_sha} -- NO EVIDENCE (not a pass, not a failure). A green exit over an empty run cannot be told apart from a green exit over ${heavy_what}, so it does not satisfy it; trying the next fit host."
    prepush_remote_gc "$ssh_t" "$rundir" "$workroot"
    return 1
  fi

  if [ "$m_exit" -ne 0 ]; then
    # The refusal below tells the developer to read the failing output. The
    # wrapper redirects pytest into $RUNDIR/suite.log on the REMOTE host, so
    # without fetching it there is nothing to read and a remote RED -- which
    # hard-blocks the push -- is undiagnosable without a manual ssh.
    log "remote leg: last 200 lines of ${label}:${rundir}/suite.log follow"
    ssh -n -o ConnectTimeout=6 -o BatchMode=yes "$ssh_t" \
      "tail -n 200 '${rundir}/suite.log' 2>/dev/null" 2> /dev/null |
      sed "s/^/[${label}] /" >&2 || true
  fi
  prepush_remote_gc "$ssh_t" "$rundir" "$workroot"

  if [ "$PREPUSH_PICK_MODE" = "shadow" ]; then
    log "remote leg: ${label} is in SHADOW -- ran ${m_collected} tests, exit ${m_exit}, but a shadow host NEVER authorizes. Receipt written; falling through to the normal precedence."
    return 1
  fi
  if [ "$m_exit" -eq 0 ]; then
    log "REMOTE LAB RUN PASS accepted in place of ${heavy_what}: ${label} ran ${m_collected} tests green on ${head_sha} (suite log sha256 ${log_sha}, ${dur}s)"
    return 0
  fi
  log "remote leg: ${label} ran ${m_collected} tests and FAILED (pytest exit ${m_exit}) on ${head_sha}"
  return 3
}
