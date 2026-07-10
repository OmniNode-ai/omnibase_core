#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
#
# Bound + harden the OCC (onex_change_control) contract checkout used by the
# deploy-gate reusable workflow [OMN-12564].
#
# Why this exists:
#   Deploy Gate stalled inside the OCC partial-clone checkout
#   (`git -C _occ checkout --force FETCH_HEAD`) on #1786 (runner-24) and #1788
#   (runner-40). The hang was inside git itself — a filtered partial clone
#   (`--filter=blob:none`) can lazily fetch missing blobs during checkout, and
#   the previous inline workflow step only wrapped the *fetch* in `timeout`,
#   not the checkout. A wedged checkout therefore spun until the 25-minute job
#   timeout with no diagnostics.
#
# What this fixes:
#   1. Hard timeout around BOTH the fetch AND the checkout (git-level via
#      `timeout`, step-level via the caller's `timeout-minutes`).
#   2. Deterministic full-ref checkout: drops `--filter=blob:none` so checkout
#      never re-enters a lazy fetch / index-pack loop. We still shallow-fetch
#      (`--depth=1`) and sparse-checkout `contracts/`, but all blobs for that
#      single ref arrive in the one bounded fetch.
#   3. On failure, emits a full diagnostic block (OCC ref, exact fetch command,
#      elapsed time, last git subprocess, and a process/subprocess tree of the
#      hung git PID) so future hangs are diagnosable from the job log alone.
#
# Tunable env (defaults are production values; tests override them):
#   OCC_REF                  ref to fetch (default: dev)
#   OCC_REPO_URL             OCC clone URL (default: GitHub OmniNode-ai/onex_change_control)
#   OCC_CHECKOUT_DIR         working dir (default: _occ)
#   OCC_SPARSE_PATH          sparse path to materialize (default: contracts)
#   OCC_FETCH_TIMEOUT_SECS   per-fetch hard timeout (default: 90)
#   OCC_CHECKOUT_TIMEOUT_SECS per-checkout hard timeout (default: 60)
#   OCC_MAX_ATTEMPTS         attempts before giving up (default: 5)
#   OCC_RETRY_BACKOFF_SECS   comma list of backoff delays (default: 0,10,20,30,45)
#   GH_TOKEN                 token for the https extraheader (optional)
set -uo pipefail

OCC_REF="${OCC_REF:-dev}"
OCC_REPO_URL="${OCC_REPO_URL:-https://github.com/OmniNode-ai/onex_change_control.git}"
OCC_CHECKOUT_DIR="${OCC_CHECKOUT_DIR:-_occ}"
OCC_SPARSE_PATH="${OCC_SPARSE_PATH:-contracts}"
OCC_FETCH_TIMEOUT_SECS="${OCC_FETCH_TIMEOUT_SECS:-90}"
OCC_CHECKOUT_TIMEOUT_SECS="${OCC_CHECKOUT_TIMEOUT_SECS:-60}"
OCC_MAX_ATTEMPTS="${OCC_MAX_ATTEMPTS:-5}"
OCC_RETRY_BACKOFF_SECS="${OCC_RETRY_BACKOFF_SECS:-0,10,20,30,45}"
GH_TOKEN="${GH_TOKEN:-}"

# Resolve a `timeout` binary. On macOS (local/dev) it is `gtimeout` from
# coreutils; on Linux CI runners it is `timeout`. We require one — without it
# we cannot bound git, which is the whole point.
TIMEOUT_BIN=""
if command -v timeout >/dev/null 2>&1; then
  TIMEOUT_BIN="timeout"
elif command -v gtimeout >/dev/null 2>&1; then
  TIMEOUT_BIN="gtimeout"
else
  echo "::error::checkout-occ-contracts: no 'timeout'/'gtimeout' binary available — cannot bound git" >&2
  exit 3
fi

# -k <kill-after>: if the SIGTERM is ignored (e.g. git stuck in a syscall),
# escalate to SIGKILL after a short grace window. Belt-and-suspenders against
# a process that swallows TERM.
TIMEOUT_KILL_AFTER="${OCC_TIMEOUT_KILL_AFTER_SECS:-10}"

# Build the HTTPS extraheader. We use the `x-access-token` basic scheme (works
# for both GITHUB_TOKEN and a CROSS_REPO_PAT) — matching the deploy-gate
# workflow. The header is kept out of the diagnostic block (token redaction).
git_auth_header=""
if [ -n "$GH_TOKEN" ]; then
  git_auth_header="AUTHORIZATION: basic $(printf 'x-access-token:%s' "$GH_TOKEN" | base64 | tr -d '\n')"
fi

# State captured for the diagnostic block.
LAST_GIT_CMD=""
LAST_GIT_PID=""

# ---------------------------------------------------------------------------
# emit_process_tree <root_pid>
#   Best-effort process/subprocess tree. Prefer pstree; fall back to a
#   `ps`-derived forest that always works on Linux + macOS CI images.
# ---------------------------------------------------------------------------
emit_process_tree() {
  local root_pid="${1:-}"
  echo "  Process tree (root pid: ${root_pid:-unknown}):"
  if command -v pstree >/dev/null 2>&1 && [ -n "$root_pid" ]; then
    pstree -p "$root_pid" 2>/dev/null | sed 's/^/    /' && return 0
  fi
  # Portable fallback: a bounded ps snapshot scoped to the wedged git's own
  # process group / ancestry plus any git/timeout/sleep processes — enough to
  # reconstruct the parent/child relationship of the hung git without dumping
  # the entire host process table into the CI log.
  echo "    (pstree unavailable — scoped ps snapshot:)"
  # Match on the command basename (field 6) being exactly git/timeout/sleep, or
  # the row being the wedged git itself, its child, or sharing its process
  # group — never a substring match against full command lines (which pulls in
  # unrelated host processes).
  ps -eo pid,ppid,pgid,etime,stat,comm 2>/dev/null \
    | awk -v root="${root_pid:-0}" '
        NR==1 { print; next }
        { n=split($6, p, "/"); base=p[n] }
        $1==root || $2==root || $3==root \
          || base=="git" || base=="timeout" || base=="gtimeout" || base=="sleep"' \
    | head -n 60 \
    | sed 's/^/    /' \
    || ps -ef 2>/dev/null | head -n 60 | sed 's/^/    /' \
    || echo "    (ps unavailable)"
}

# ---------------------------------------------------------------------------
# emit_diagnostics <elapsed_secs> <phase> <root_pid>
#   The full diagnostic block required by OMN-12564 acceptance criteria.
# ---------------------------------------------------------------------------
emit_diagnostics() {
  local elapsed="${1:-?}" phase="${2:-unknown}" root_pid="${3:-}"
  {
    echo "::group::OCC checkout diagnostics (phase: ${phase})"
    echo "OCC checkout diagnostics"
    echo "  OCC ref:          ${OCC_REF}"
    echo "  OCC repo:         ${OCC_REPO_URL}"
    echo "  Checkout dir:     ${OCC_CHECKOUT_DIR}"
    echo "  Sparse path:      ${OCC_SPARSE_PATH}"
    echo "  Fetch command:    ${FETCH_CMD_DISPLAY:-<not yet built>}"
    echo "  Elapsed:          ${elapsed}s"
    echo "  Fetch timeout:    ${OCC_FETCH_TIMEOUT_SECS}s"
    echo "  Checkout timeout: ${OCC_CHECKOUT_TIMEOUT_SECS}s"
    echo "  Last git subprocess: ${LAST_GIT_CMD:-<none>}"
    echo "  Last git pid:        ${LAST_GIT_PID:-<none>}"
    emit_process_tree "${root_pid:-$LAST_GIT_PID}"
    echo "::endgroup::"
  } >&2
}

# Display-only fetch command (no token), built once OCC_REF is known.
FETCH_CMD_DISPLAY="git -C ${OCC_CHECKOUT_DIR} -c http.version=HTTP/1.1 fetch --depth=1 origin ${OCC_REF}"

# ---------------------------------------------------------------------------
# run_git_bounded <timeout_secs> <git args...>
#   Runs git under a hard timeout, recording the command + pid for diagnostics
#   and distinguishing a timeout (exit 124/137) from an ordinary failure.
#   Returns the git/timeout exit code.
# ---------------------------------------------------------------------------
run_git_bounded() {
  local tmo="$1"
  shift
  LAST_GIT_CMD="git $*"
  # Launch under timeout; capture the child pid so we can dump its tree if it
  # hangs. `timeout` forwards signals to the child group.
  "$TIMEOUT_BIN" -k "$TIMEOUT_KILL_AFTER" "$tmo" git "$@" &
  LAST_GIT_PID=$!
  wait "$LAST_GIT_PID"
  return $?
}

# Parse backoff list into an array.
IFS=',' read -r -a BACKOFFS <<<"$OCC_RETRY_BACKOFF_SECS"

attempt=1
while [ "$attempt" -le "$OCC_MAX_ATTEMPTS" ]; do
  # Backoff (skip on first attempt; clamp to last value if list is short).
  if [ "$attempt" -gt 1 ]; then
    idx=$((attempt - 1))
    delay="${BACKOFFS[$idx]:-${BACKOFFS[${#BACKOFFS[@]}-1]}}"
    if [ "${delay:-0}" -gt 0 ] 2>/dev/null; then
      echo "::notice::Retrying OCC contracts checkout in ${delay}s (attempt ${attempt}/${OCC_MAX_ATTEMPTS})"
      sleep "$delay"
    fi
  fi

  attempt_start="$(date +%s)"

  rm -rf "$OCC_CHECKOUT_DIR"
  git init "$OCC_CHECKOUT_DIR" >/dev/null
  git -C "$OCC_CHECKOUT_DIR" remote add origin "$OCC_REPO_URL"
  git -C "$OCC_CHECKOUT_DIR" sparse-checkout init --cone >/dev/null
  git -C "$OCC_CHECKOUT_DIR" sparse-checkout set "$OCC_SPARSE_PATH" >/dev/null

  # --- Bounded, deterministic fetch -------------------------------------
  # NOTE: no `--filter=blob:none`. A blobless partial clone defers blob
  # download to checkout time, which is exactly where #1786/#1788 wedged.
  # A shallow (`--depth=1`) sparse fetch of one ref pulls every blob we need
  # up front, so the subsequent checkout is a pure local index write.
  fetch_args=(-C "$OCC_CHECKOUT_DIR" -c http.version=HTTP/1.1)
  if [ -n "$git_auth_header" ]; then
    fetch_args+=(-c "http.https://github.com/.extraheader=${git_auth_header}")
  fi
  fetch_args+=(fetch --depth=1 origin "$OCC_REF")

  run_git_bounded "$OCC_FETCH_TIMEOUT_SECS" "${fetch_args[@]}"
  fetch_rc=$?

  if [ "$fetch_rc" -eq 124 ] || [ "$fetch_rc" -eq 137 ]; then
    elapsed=$(($(date +%s) - attempt_start))
    echo "::warning::OCC fetch timed out after ${OCC_FETCH_TIMEOUT_SECS}s (attempt ${attempt}/${OCC_MAX_ATTEMPTS})"
    emit_diagnostics "$elapsed" "fetch-timeout" "$LAST_GIT_PID"
    attempt=$((attempt + 1))
    continue
  fi
  if [ "$fetch_rc" -ne 0 ]; then
    echo "::warning::OCC fetch failed (rc=${fetch_rc}, attempt ${attempt}/${OCC_MAX_ATTEMPTS})"
    attempt=$((attempt + 1))
    continue
  fi

  # --- Bounded checkout -------------------------------------------------
  run_git_bounded "$OCC_CHECKOUT_TIMEOUT_SECS" -C "$OCC_CHECKOUT_DIR" checkout --force FETCH_HEAD
  checkout_rc=$?

  if [ "$checkout_rc" -eq 124 ] || [ "$checkout_rc" -eq 137 ]; then
    elapsed=$(($(date +%s) - attempt_start))
    echo "::warning::OCC checkout timed out after ${OCC_CHECKOUT_TIMEOUT_SECS}s (attempt ${attempt}/${OCC_MAX_ATTEMPTS})"
    emit_diagnostics "$elapsed" "checkout-timeout" "$LAST_GIT_PID"
    attempt=$((attempt + 1))
    continue
  fi
  if [ "$checkout_rc" -ne 0 ]; then
    echo "::warning::OCC checkout failed (rc=${checkout_rc}, attempt ${attempt}/${OCC_MAX_ATTEMPTS})"
    attempt=$((attempt + 1))
    continue
  fi

  if [ -d "${OCC_CHECKOUT_DIR}/${OCC_SPARSE_PATH}" ]; then
    echo "::notice::OCC contracts checkout succeeded on attempt ${attempt}"
    exit 0
  fi

  echo "::warning::OCC checkout completed but ${OCC_CHECKOUT_DIR}/${OCC_SPARSE_PATH} is missing (attempt ${attempt}/${OCC_MAX_ATTEMPTS})"
  attempt=$((attempt + 1))
done

elapsed=$(($(date +%s) - ${attempt_start:-$(date +%s)}))
echo "::error::OCC contracts checkout failed after ${OCC_MAX_ATTEMPTS} attempts"
emit_diagnostics "$elapsed" "exhausted" "$LAST_GIT_PID"
exit 1
