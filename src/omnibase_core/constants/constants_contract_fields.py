"""
Constants for contract field names used across ONEX.

Single source of truth for contract field names to avoid magic strings.
"""

# env-var-ok: constant definitions for contract fields, not environment variables

# Core contract fields
CONTRACT_VERSION = "contract_version"
NODE_NAME = "node_name"
NODE_VERSION = "node_version"
DESCRIPTION = "description"
TOOL_TYPE = "tool_type"
NAMESPACE = "namespace"
LIFECYCLE = "lifecycle"

# Execution mode fields
EXECUTION_MODES = "execution_modes"
EXECUTION_MODE_DIRECT = "direct"
EXECUTION_MODE_WORKFLOW = "workflow"
EXECUTION_MODE_ORCHESTRATED = "orchestrated"
EXECUTION_MODE_AUTO = "auto"

# Workflow configuration
WORKFLOW_CONFIG = "workflow_config"
WORKFLOW_ENABLED = "enabled"
WORKFLOW_TIMEOUT_SECONDS = "timeout_seconds"
WORKFLOW_SUPPORTS_STREAMING = "supports_streaming"
WORKFLOW_CHECKPOINT_ENABLED = "checkpoint_enabled"

# State definitions
INPUT_STATE = "input_state"
OUTPUT_STATE = "output_state"
DEFINITIONS = "definitions"

# Common state properties
TYPE = "type"
PROPERTIES = "properties"
REQUIRED = "required"
ENUM = "enum"
DEFAULT = "default"
REF = "$ref"

# Version fields
MAJOR = "major"
MINOR = "minor"
PATCH = "patch"

# Node.onex.yaml fields
METADATA_VERSION = "metadata_version"
PROTOCOL_VERSION = "protocol_version"
OWNER = "owner"
COPYRIGHT = "copyright"
SCHEMA_VERSION = "schema_version"
NAME = "name"
VERSION = "version"
UUID = "uuid"
AUTHOR = "author"
CREATED_AT = "created_at"
LAST_MODIFIED_AT = "last_modified_at"
STATE_CONTRACT = "state_contract"
HASH = "hash"
ENTRYPOINT = "entrypoint"
RUNTIME_LANGUAGE_HINT = "runtime_language_hint"
META_TYPE = "meta_type"

# Output field processing keys
BACKEND_KEY = "backend"
CUSTOM_KEY = "custom"
DEFAULT_PROCESSED_VALUE = "default_processed"
INTEGRATION_KEY = "integration"
PROCESSED_KEY = "processed"
