#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
#
# OMN-14863 (fan-out from OMN-14854 omniclaude canary): Required-Check
# Skip-Vector Guard — local (pre-commit) run. Vendored from omniclaude
# (canonical source: OmniNode-ai/omniclaude/.pre-commit-hooks/
# reject-required-check-skip-vector.sh) unmodified except this header.
#
# Dual-run pattern (mirrors check-daemon-venv-skew.sh -> check_daemon_venv_skew.py):
# this thin wrapper and the CI reusable workflow
# (required-check-skip-guard-reusable.yml) both invoke the SAME Python
# validator, so local and CI verdicts can never diverge.
#
# Fails closed on any of the four skip vectors described in
# validate_no_required_check_skip_vectors.py's module docstring.

set -euo pipefail

if REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" && [[ -n "$REPO_ROOT" ]]; then
    :
else
    REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fi

PY="${PYTHON_BIN:-python3}"
if ! command -v "$PY" >/dev/null 2>&1; then
    echo "ERROR: python3 not found on PATH for required-check-skip-guard" >&2
    exit 1
fi

exec "$PY" "${REPO_ROOT}/.github/actions/required-check-skip-guard/validate_no_required_check_skip_vectors.py" \
    --manifest "${REPO_ROOT}/.github/required-checks.yaml" \
    --workflows-dir "${REPO_ROOT}/.github/workflows"
