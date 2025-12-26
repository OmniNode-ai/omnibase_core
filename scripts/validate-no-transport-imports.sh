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
# Word boundary behavior is enforced by the IMPORT_PATTERN regex structure below,
# not by wrapping individual packages in \b...\b
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
# LIMITATION: TYPE_CHECKING block detection
# This script does NOT detect imports inside TYPE_CHECKING blocks, which would be
# acceptable since they don't create runtime dependencies. Proper detection would
# require parsing Python AST, which is impractical in a shell script.
#
# If this script flags an import that is inside a TYPE_CHECKING block:
#   1. The import is likely acceptable (type-only, no runtime dependency)
#   2. Manual review is required to confirm
#   3. Consider adding the file to EXCLUDE_PATTERN if it's a legitimate type-only import
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
    echo "  3. If this import is inside a TYPE_CHECKING block (type-only, no runtime dep):"
    echo "     - Verify the import is guarded by 'if TYPE_CHECKING:'"
    echo "     - Add the file to EXCLUDE_PATTERN in this script"
    exit 1
fi

echo "No transport/I/O library imports found in omnibase_core"
exit 0
