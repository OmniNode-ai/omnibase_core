# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Document reference type classification for doc freshness scanning."""

from __future__ import annotations

from enum import StrEnum, unique


@unique
class EnumDocReferenceType(StrEnum):
    """Type of reference extracted from a documentation file.

    FILE_PATH     - e.g., src/omnibase_infra/nodes/node_foo/node.py
    FUNCTION_NAME - e.g., classify_node()
    CLASS_NAME    - e.g., ModelBaselinesSnapshotEvent
    COMMAND       - e.g., uv run pytest tests/unit/
    URL           - e.g., http://localhost:8080
    ENV_VAR       - e.g., KAFKA_BOOTSTRAP_SERVERS
    """

    FILE_PATH = "FILE_PATH"
    FUNCTION_NAME = "FUNCTION_NAME"
    CLASS_NAME = "CLASS_NAME"
    COMMAND = "COMMAND"
    URL = "URL"
    ENV_VAR = "ENV_VAR"
