#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2025 OmniNode AI <https://omninode.ai>
# SPDX-License-Identifier: Apache-2.0
#
# validate-class-naming.sh - ONEX Class Naming Convention Validation
#
# Validates that class names match their expected prefixes based on ONEX naming
# conventions and file/directory structure.
#
# ONEX Naming Conventions:
#   Model*     - Pydantic data models (in models/, model_*.py)
#   Service*   - Service classes (in services/, service_*.py)
#   Util*      - Utility classes (in utils/, util_*.py)
#   Protocol*  - Abstract protocol definitions (in protocols/, protocol_*.py)
#   Enum*      - Enumeration types (in enums/, enum_*.py)
#   *Error     - Exception classes (in errors/, exception_*.py)
#   Node*      - ONEX node implementations (in nodes/, node_*.py)
#   Mixin*     - Mixin classes (in mixins/, mixin_*.py)
#
# Usage:
#   ./scripts/validate-class-naming.sh           # Basic validation
#   ./scripts/validate-class-naming.sh -v        # Verbose output
#   ./scripts/validate-class-naming.sh --json    # JSON output for CI
#
# Exit Codes:
#   0 - All class names conform to conventions
#   1 - Violations found
#   2 - Script error (could not run validation)
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

# Pass all arguments to the Python script
exec uv run python scripts/validate_class_naming.py "$@"
