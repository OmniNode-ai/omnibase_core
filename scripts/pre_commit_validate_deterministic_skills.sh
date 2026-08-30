#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
#
# Pre-commit wrapper around scripts/validate_deterministic_skill_routing.py
# (OMN-8765). The deterministic-skill routing gate lives in this repo but
# scans SKILL.md files that are owned by ``omniclaude``. In CI the
# check-deterministic-skills job clones omniclaude into ``_external/`` and the
# gate ALWAYS runs; for local pre-commit runs we resolve the sibling clone from
# (in priority order) DETERMINISTIC_SKILL_ROOT, the CI ``_external`` layout, the
# standard omni_home sibling ``../omniclaude/...``, or ``$OMNI_HOME/omniclaude``.
#
# WS7 fail-loud parity (OMN-14671 / OMN-14655): this hook used to ``exit 0``
# when no sibling resolved -- green locally while the same gate was RED on CI (a
# skipped gate byte-indistinguishable from a passing one, DRIFT-2). A gate that
# cannot run must FAIL LOUD, not silently pass. It now exits non-zero with an
# actionable message. In the canonical omni_home layout OMNI_HOME is set and the
# sibling exists, so this resolves; a contributor without the registry sets
# DETERMINISTIC_SKILL_ROOT or clones the omniclaude sibling.
#
# OMN-17167: the fail-loud message used to be generic -- it never printed the
# ``$OMNI_HOME``-derived path it actually probed, so a STALE OMNI_HOME (set, but
# pointing at the wrong directory) was byte-indistinguishable from an UNSET one.
# The shared preflight below distinguishes the two and names the variable and
# the full missing path in both. Doctrine: omni_home CLAUDE.md rule 8 (fail fast
# on missing env, never a silent default) and rule 6 (no absolute paths -- the
# remediation is an ``export`` line, not a machine path).

set -euo pipefail

# --- OMN-17167 shared preflight ------------------------------------------------
# Deliberately duplicated verbatim in omnimarket/scripts/validation/run_topic_lint.sh
# and omnimarket/scripts/ci/check_subscriber_dispatcher_resolution.sh rather than
# factored into a cross-repo shim library: a hook whose job is to diagnose a broken
# sibling layout must not itself be loaded from that sibling layout. Repo-local,
# identical wording.
#
#   $1     human list of the sibling clones THIS hook needs
#   $2...  the full $OMNI_HOME-derived paths this hook needed and did not find
omni_home_preflight_fail() {
  local siblings="$1"
  shift
  if [ -z "${OMNI_HOME:-}" ]; then
    echo "OMNI_HOME is not set. It must be the directory containing the sibling clones (${siblings}). Example: export OMNI_HOME=\$HOME/omninode" >&2
  else
    echo "OMNI_HOME is set to ${OMNI_HOME}, but the sibling clones this hook needs (${siblings}) are not there. Missing:" >&2
    for missing_path in "$@"; do
      echo "  ${missing_path}" >&2
    done
    echo "OMNI_HOME must be the directory containing the sibling clones (${siblings}). Example: export OMNI_HOME=\$HOME/omninode" >&2
  fi
  exit 2
}
# --- end shared preflight ------------------------------------------------------

SKILL_ROOT=""
if [ -n "${DETERMINISTIC_SKILL_ROOT:-}" ]; then
  SKILL_ROOT="${DETERMINISTIC_SKILL_ROOT}"
elif [ -d "_external/omniclaude/plugins/onex/skills" ]; then
  SKILL_ROOT="_external/omniclaude/plugins/onex/skills"
elif [ -d "../omniclaude/plugins/onex/skills" ]; then
  SKILL_ROOT="../omniclaude/plugins/onex/skills"
elif [ -n "${OMNI_HOME:-}" ] && [ -d "${OMNI_HOME}/omniclaude/plugins/onex/skills" ]; then
  SKILL_ROOT="${OMNI_HOME}/omniclaude/plugins/onex/skills"
fi

if [ -z "${SKILL_ROOT}" ]; then
  echo "ERROR: OMN-8765 deterministic-skill gate cannot run: omniclaude skills root not found." >&2
  echo "  This gate runs unconditionally in CI; a silent local skip is a false-green (WS7/OMN-14671)." >&2
  echo "  Override with: export DETERMINISTIC_SKILL_ROOT=<path to omniclaude/plugins/onex/skills>" >&2
  omni_home_preflight_fail "omniclaude" "${OMNI_HOME:-}/omniclaude/plugins/onex/skills"
fi

exec uv run python scripts/validate_deterministic_skill_routing.py \
  --skills-root "${SKILL_ROOT}"
