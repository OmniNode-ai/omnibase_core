"""
Metadata constants for ONEX Core Framework.
"""

# Version keys for metadata
METADATA_VERSION_KEY = "metadata_version"
PROTOCOL_VERSION_KEY = "protocol_version"
SCHEMA_VERSION_KEY = "schema_version"

# Namespace constants
NAMESPACE_KEY = "namespace"

# Project metadata keys
COPYRIGHT_KEY = "copyright"
ENTRYPOINT_KEY = "entrypoint"
TOOLS_KEY = "tools"

# Configuration file names
PROJECT_ONEX_YAML_FILENAME = "project.onex.yaml"


def get_namespace_prefix() -> str:
    """
    Get the default namespace prefix for ONEX Core.

    Returns:
        str: The namespace prefix "omnibase_core"
    """
    return "omnibase_core"
