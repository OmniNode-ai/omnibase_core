# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Metadata constants for ONEX Core Framework.
"""

# env-var-ok: constant definitions for metadata keys, not environment variables

# Version keys for metadata
METADATA_VERSION_KEY = "metadata_version"  # env-var-ok: metadata key
PROTOCOL_VERSION_KEY = "protocol_version"  # env-var-ok: metadata key
SCHEMA_VERSION_KEY = "schema_version"  # env-var-ok: metadata key

# Namespace constants
NAMESPACE_KEY = "namespace"  # env-var-ok: metadata key

# Project metadata keys
COPYRIGHT_KEY = "copyright"  # env-var-ok: metadata key
ENTRYPOINT_KEY = "entrypoint"  # env-var-ok: metadata key
TOOLS_KEY = "tools"  # env-var-ok: metadata key

# State contract keys
CONTRACT_VERSION_KEY = "contract_version"  # env-var-ok: metadata key
CONTRACT_SCHEMA_VERSION_KEY = "contract_schema_version"  # env-var-ok: metadata key
NODE_VERSION_KEY = "node_version"  # env-var-ok: metadata key

# CLI service keys
VERSION_KEY = "version"  # env-var-ok: metadata key
TOOL_METADATA_KEY = "tool_metadata"  # env-var-ok: metadata key
METADATA_ERROR_KEY = "metadata_error"  # env-var-ok: metadata key

# Configuration file names
PROJECT_ONEX_YAML_FILENAME = "project.onex.yaml"

# Markdown metadata delimiters
MD_META_OPEN = "<!--"
MD_META_CLOSE = "-->"


def get_namespace_prefix() -> str:
    """
    Get the default namespace prefix for ONEX Core.

    Returns:
        str: The namespace prefix "omnibase_core"
    """
    return "omnibase_core"
