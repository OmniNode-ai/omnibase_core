#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
#
# Pre-commit wrapper around scripts/validate_deterministic_skill_routing.py
# (OMN-8765). The deterministic-skill routing gate lives in this repo but
# scans SKILL.md files that are owned by ``omniclaude``. In CI the
# check-deterministic-skills job clones omniclaude into ``_external/``; for
# local pre-commit runs we look for the sibling clone at
# ``../omniclaude/plugins/onex/skills`` (standard omni_home layout). When the
# sibling is absent the hook succeeds silently so contributors who have not
# cloned the full omni_home registry are not blocked.

set -euo pipefail

SKILL_ROOT=""
if [ -n "${DETERMINISTIC_SKILL_ROOT:-}" ]; then
  SKILL_ROOT="${DETERMINISTIC_SKILL_ROOT}"
elif [ -d "../omniclaude/plugins/onex/skills" ]; then
  SKILL_ROOT="../omniclaude/plugins/onex/skills"
elif [ -n "${OMNI_HOME:-}" ] && [ -d "${OMNI_HOME}/omniclaude/plugins/onex/skills" ]; then
  SKILL_ROOT="${OMNI_HOME}/omniclaude/plugins/onex/skills"
fi

if [ -z "${SKILL_ROOT}" ]; then
  echo "Skipping OMN-8765 deterministic-skill gate (omniclaude sibling not found)"
  exit 0
fi

exec uv run python scripts/validate_deterministic_skill_routing.py \
  --skills-root "${SKILL_ROOT}"
