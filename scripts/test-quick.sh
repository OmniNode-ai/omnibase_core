#!/bin/bash
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

# Quick feedback - only affected tests (5-30s)
# Uses pytest-testmon to run only tests affected by code changes
set -e

echo "🚀 Running affected tests with pytest-testmon..."
uv run pytest \
  --testmon \
  --testmon-noselect \
  -n auto \
  --maxfail=5 \
  -x \
  --tb=short \
  "$@"
