#!/bin/bash
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

# Validate no omnibase_spi imports exist in omnibase_core
# Enforces architectural boundary: Core should not depend on SPI

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CORE_SRC="$PROJECT_ROOT/src/omnibase_core"

echo "Checking for omnibase_spi imports in omnibase_core..."

# Files to exclude (migration tooling that legitimately references SPI)
EXCLUDE_PATTERN="services/service_protocol_migrator.py|services/service_protocol_auditor.py"

# Find violations
VIOLATIONS=$(grep -RnE "^(from|import) omnibase_spi" "$CORE_SRC" --include="*.py" 2>/dev/null | grep -vE "$EXCLUDE_PATTERN" || true)

if [ -n "$VIOLATIONS" ]; then
    echo "ERROR: Found omnibase_spi imports in omnibase_core!"
    echo ""
    echo "Violations:"
    echo "$VIOLATIONS"
    echo ""
    echo "Use Core-native protocols from omnibase_core.protocols instead."
    exit 1
fi

echo "✓ No omnibase_spi imports found in omnibase_core"
exit 0
