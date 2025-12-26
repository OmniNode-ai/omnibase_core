#!/bin/bash
# Validate no direct transport/I/O library imports exist in omnibase_core
# Enforces architectural boundary: Core should be pure, infrastructure owns all I/O
#
# Forbidden imports:
#   HTTP clients: aiohttp, httpx, requests, urllib3
#   Kafka clients: kafka-python, aiokafka, confluent-kafka
#   Redis clients: redis, aioredis
#   Database clients: asyncpg, psycopg2, psycopg, aiomysql
#   Message queues: pika, aio-pika, kombu, celery
#   gRPC: grpc (import name; PyPI package is grpcio)
#   WebSocket: websockets, wsproto

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CORE_SRC="$PROJECT_ROOT/src/omnibase_core"

echo "Checking for transport/I/O library imports in omnibase_core..."

# Build regex pattern for forbidden imports
# Note: We check for both 'import X' and 'from X import' patterns
# Packages are matched at word boundaries to avoid false positives
FORBIDDEN_PACKAGES=(
    # HTTP clients
    "aiohttp"
    "httpx"
    "requests"
    "urllib3"
    # Kafka clients
    "kafka"
    "aiokafka"
    "confluent_kafka"
    # Redis clients
    "redis"
    "aioredis"
    # Database clients
    "asyncpg"
    "psycopg2"
    "psycopg"
    "aiomysql"
    # Message queues
    "pika"
    "aio_pika"
    "kombu"
    "celery"
    # gRPC (import name is "grpc", not "grpcio" which is the PyPI package name)
    "grpc"
    # WebSocket
    "websockets"
    "wsproto"
)

# Build alternation pattern for grep
# Word boundary behavior is enforced by the IMPORT_PATTERN regex structure below:
#   - For 'from X import': requires whitespace or '.' after package name via (\.|[[:space:]])
#   - For 'import X': requires whitespace, '.', ',', or end-of-line via (\.|[[:space:]]|,|$)
# This prevents false positives like 'aiohttp_helper' matching 'aiohttp'
PATTERN=""
for pkg in "${FORBIDDEN_PACKAGES[@]}"; do
    if [ -n "$PATTERN" ]; then
        PATTERN="$PATTERN|"
    fi
    PATTERN="$PATTERN$pkg"
done

# Match import statements: 'import X' or 'from X import'
# - Anchored to start of line (after optional whitespace)
# - Uses word boundaries (\b) around package names
# - Allows for submodule imports like 'import aiohttp.client' or 'from aiohttp.web import X'
IMPORT_PATTERN="^[[:space:]]*(from[[:space:]]+($PATTERN)(\\.|[[:space:]])|import[[:space:]]+($PATTERN)(\\.|[[:space:]]|,|$))"

# Files/patterns to exclude:
# - Protocol definition files with documentation examples showing adapter usage
# - __pycache__ and compiled files
EXCLUDE_PATTERN="protocols/http/__init__.py|protocols/http/protocol_http_client.py|__pycache__|\.pyc$"

# Find violations - actual import statements only
# We use -P for Perl regex to get proper word boundaries
VIOLATIONS=$(grep -RnP "$IMPORT_PATTERN" "$CORE_SRC" --include="*.py" 2>/dev/null | grep -vE "$EXCLUDE_PATTERN" || true)

# Filter out obvious false positives (comments, docstrings)
#
# ============================================================================
# LIMITATION: TYPE_CHECKING block detection
# ============================================================================
# This script cannot detect imports inside TYPE_CHECKING blocks because:
#   - TYPE_CHECKING blocks span multiple lines (if TYPE_CHECKING: ... import ...)
#   - Proper detection requires Python AST parsing, impractical in a shell script
#   - See ADR-005 for architectural context on why TYPE_CHECKING imports are allowed
#
# TYPE_CHECKING imports are ALLOWED per ADR-005 because they:
#   - Only execute during static type analysis (mypy, pyright)
#   - Create NO runtime dependencies
#   - Are guarded by: if TYPE_CHECKING: ... from aiohttp import ClientSession
#
# If this script flags an import that is inside a TYPE_CHECKING block:
#   1. VERIFY: Open the file and confirm the import is inside 'if TYPE_CHECKING:'
#   2. CONFIRM: The import is for type annotations only (not runtime usage)
#   3. EXCLUDE: Add the file path to EXCLUDE_PATTERN above (line ~75)
#      Example: EXCLUDE_PATTERN="...|path/to/file.py"
#   4. DOCUMENT: Add a comment in the file explaining the TYPE_CHECKING usage
#
# To manually check a flagged file:
#   grep -B5 "from aiohttp" path/to/file.py  # Look for TYPE_CHECKING guard
# ============================================================================
#
REAL_VIOLATIONS=""
while IFS= read -r line; do
    [ -z "$line" ] && continue

    # Skip lines that are clearly comments
    if echo "$line" | grep -qE "^[^:]+:[0-9]+:[[:space:]]*#"; then
        continue
    fi

    # Skip lines containing "Example:" (documentation examples)
    if echo "$line" | grep -qE "Example:|example:"; then
        continue
    fi

    REAL_VIOLATIONS="$REAL_VIOLATIONS$line"$'\n'
done <<< "$VIOLATIONS"

# Trim trailing newline
REAL_VIOLATIONS="${REAL_VIOLATIONS%$'\n'}"

if [ -n "$REAL_VIOLATIONS" ]; then
    echo "ERROR: Found transport/I/O library imports in omnibase_core!"
    echo ""
    echo "Violations:"
    echo "$REAL_VIOLATIONS"
    echo ""
    echo "Architectural Invariant: omnibase_core must be pure (no I/O dependencies)."
    echo "Transport and I/O libraries belong in infrastructure layers."
    echo ""
    echo "Solutions:"
    echo "  1. Define a protocol in omnibase_core for the capability you need"
    echo "  2. Implement the protocol in an infrastructure package"
    echo "  3. If this import is inside a TYPE_CHECKING block (allowed per ADR-005):"
    echo "     a. VERIFY: Confirm the import is inside 'if TYPE_CHECKING:'"
    echo "     b. CONFIRM: The import is for type annotations only (not runtime)"
    echo "     c. EXCLUDE: Add the file path to EXCLUDE_PATTERN in this script"
    echo "     d. DOCUMENT: Add a comment in the file explaining the usage"
    echo "     See the LIMITATION comment in this script for details."
    exit 1
fi

echo "No transport/I/O library imports found in omnibase_core"
exit 0
