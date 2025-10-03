# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T13:24:08.257653'
# description: Stamped by ToolPython
# entrypoint: python://utils_uri_parser
# hash: 93e5007ba344a2eb922e1163b93290a8d23ab4aa70bc990dd787084b7a98cf10
# last_modified_at: '2025-05-29T14:14:00.989431+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: utils_uri_parser.py
# namespace: python://omnibase.utils.utils_uri_parser
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: {}
# uuid: 249f5d3d-20f0-4932-9b2f-43406aedee32
# version: 1.0.0
# === /OmniNode:Metadata ===


"""
Canonical ONEX URI parser utility.
See docs/nodes/node_contracts.md and docs/nodes/structural_conventions.md for URI format and usage.
# MILESTONE M1+ ENHANCEMENTS:
#
# URI Dereferencing:
# - Resolve URIs to actual resource locations
# - Support for remote URI resolution
# - Caching layer for resolved URIs
# - Error handling for unreachable resources
#
# Registry Integration:
# - Integration with ONEX service registry
# - Dynamic service discovery via URIs
# - Load balancing for multiple service instances
# - Health checking of resolved services
#
# Version Resolution:
# - Semantic version range resolution (^1.2.0, ~1.2.0)
# - Compatibility checking between versions
# - Automatic version negotiation
# - Deprecation warnings for outdated versions
#
# Advanced Features:
# - URI templating and parameterization
# - Schema validation for resolved resources
# - Security policies for URI access
# - Audit logging for URI resolution
"""

import re
from pathlib import Path

from omnibase_core.core.errors.core_errors import CoreErrorCode, OnexError
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.enums.enum_metadata import UriTypeEnum
from omnibase_core.logging.structured import emit_log_event_sync
from omnibase_core.models.core.model_uri import ModelOnexUri
from omnibase_core.protocol.protocol_event_bus import ProtocolEventBus
from omnibase_core.protocol.protocol_uri_parser import ProtocolUriParser

# Component identifier for logging
_COMPONENT_NAME = Path(__file__).stem

# Build the allowed types pattern from the Enum
ALLOWED_TYPES = [e.value for e in UriTypeEnum if e != UriTypeEnum.UNKNOWN]
URI_PATTERN = re.compile(rf"^({'|'.join(ALLOWED_TYPES)})://([^@]+)@(.+)$")


class CanonicalUriParser(ProtocolUriParser):
    """
    Canonical implementation of ProtocolUriParser for ONEX URIs.
    Instantiate and inject this class; do not use as a singleton or global.
    """

    async def parse(
        self,
        uri_string: str,
        event_bus: ProtocolEventBus = None,
    ) -> ModelOnexUri:
        """
        Parse a canonical ONEX URI of the form <type>://<namespace>@<version_spec>.
        Raises OmniBaseError if the format is invalid.
        Returns an ModelOnexUri.
        """
        if event_bus is not None:
            emit_log_event_sync(
                LogLevel.DEBUG,
                f"Parsing ONEX URI: {uri_string}",
                node_id=_COMPONENT_NAME,
                event_bus=event_bus,
            )
        match = URI_PATTERN.match(uri_string)
        if not match:
            raise OnexError(
                CoreErrorCode.SCHEMA_VALIDATION_FAILED,
                f"URI parsing failed: Invalid format for {uri_string}",
            )
        uri_type, namespace, version_spec = match.groups()
        if event_bus is not None:
            emit_log_event_sync(
                LogLevel.DEBUG,
                f"Parsed: Type={uri_type}, Namespace={namespace}, Version={version_spec}",
                node_id=_COMPONENT_NAME,
                event_bus=event_bus,
            )
        return ModelOnexUri(
            type=UriTypeEnum(uri_type),
            namespace=namespace,
            version_spec=version_spec,
            original=uri_string,
        )
