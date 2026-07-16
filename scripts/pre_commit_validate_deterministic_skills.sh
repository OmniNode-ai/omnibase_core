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
# cannot run must FAIL LOUD, not silently pass. It now exits 1 with an
# actionable message. In the canonical omni_home layout OMNI_HOME is set and the
# sibling exists, so this resolves; a contributor without the registry sets
# DETERMINISTIC_SKILL_ROOT or clones the omniclaude sibling.

set -euo pipefail

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
  echo "  Resolve by one of:" >&2
  echo "    - export OMNI_HOME=<omni_home root> (so \$OMNI_HOME/omniclaude/plugins/onex/skills resolves), or" >&2
  echo "    - export DETERMINISTIC_SKILL_ROOT=<path to omniclaude/plugins/onex/skills>, or" >&2
  echo "    - clone the omniclaude sibling next to this repo (../omniclaude)." >&2
  exit 1
fi

exec uv run python scripts/validate_deterministic_skill_routing.py \
  --skills-root "${SKILL_ROOT}"
