# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-07-04T02:00:00.000000'
# description: Introspection publishing mixin for event-driven nodes
# entrypoint: python://mixin_introspection_publisher
# lifecycle: active
# meta_type: mixin
# metadata_version: 0.1.0
# name: mixin_introspection_publisher.py
# namespace: python://omnibase.mixin.mixin_introspection_publisher
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# version: 1.0.0
# === /OmniNode:Metadata ===

"""
Introspection Publisher Mixin.

This mixin handles:
- Gathering node introspection data from various sources
- Publishing NODE_INTROSPECTION_EVENT for service discovery
- Extracting actions, protocols, metadata from nodes
- Retry logic for failed publishes
"""

import re
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError

from omnibase_core.core.core_structured_logging import emit_log_event_sync
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.models.core.model_log_context import ModelLogContext
from omnibase_core.models.core.model_semver import ModelSemVer
from omnibase_core.models.discovery.model_node_introspection_event import (
    ModelNodeCapabilities,
    ModelNodeIntrospectionEvent,
)

# Component identifier for logging
_COMPONENT_NAME = Path(__file__).stem

# Constants
DEFAULT_AUTHOR = "ONEX"


class ModelNodeIntrospectionData(BaseModel):
    """
    Strongly typed container for node introspection data.

    This replaces the loose Dict[str, str | ModelSemVer | List[str] | ...] with
    proper type safety and clear field definitions. Uses the canonical
    ModelNodeCapabilities structure for capabilities data.
    """

    node_name: str = Field(..., description="Node name identifier")
    version: ModelSemVer = Field(..., description="Semantic version of the node")
    capabilities: ModelNodeCapabilities = Field(..., description="Node capabilities")
    tags: list[str] = Field(default_factory=list, description="Discovery tags")
    health_endpoint: str | None = Field(None, description="Health check endpoint")


class MixinIntrospectionPublisher:
    """
    Mixin for introspection publishing capabilities.

    Provides methods to gather node information and publish introspection events
    for automatic service discovery. Uses getattr() for all host class attribute access.
    """

    def _publish_introspection_event(self) -> None:
        """
        Publish NODE_INTROSPECTION_EVENT for automatic service discovery.

        This enables other services to discover this node's capabilities without
        requiring manual registration or hardcoded node lists.
        """
        event_bus = getattr(self, "event_bus", None)
        if not event_bus:
            return

        node_id = getattr(self, "_node_id", "unknown")

        try:
            # Gather introspection data (now strongly typed)
            introspection_data = self._gather_introspection_data()

            # Generate correlation ID for introspection
            from uuid import uuid4

            correlation_id = uuid4()

            # Create and publish introspection event
            introspection_event = ModelNodeIntrospectionEvent.create_from_node_info(
                node_id=node_id,
                node_name=introspection_data.node_name,
                version=introspection_data.version,
                actions=introspection_data.capabilities.actions,
                protocols=introspection_data.capabilities.protocols,
                metadata=introspection_data.capabilities.metadata,
                tags=introspection_data.tags,
                health_endpoint=introspection_data.health_endpoint,
                correlation_id=correlation_id,
            )

            # Publish with retry logic
            self._publish_with_retry(introspection_event)

            context = ModelLogContext(
                calling_module=_COMPONENT_NAME,
                calling_function="_publish_introspection_event",
                calling_line=71,
                timestamp=datetime.now().isoformat(),
                node_id=node_id,
            )
            emit_log_event_sync(
                LogLevel.INFO,
                f"Published introspection event for node {node_id}",
                context=context,
            )

        except (ValueError, ValidationError) as e:
            # FAIL-FAST: Re-raise validation errors immediately to crash the service
            context = ModelLogContext(
                calling_module=_COMPONENT_NAME,
                calling_function="_publish_introspection_event",
                calling_line=95,
                timestamp=datetime.now().isoformat(),
                node_id=node_id,
            )
            emit_log_event_sync(
                LogLevel.ERROR,
                f"💥 FAIL-FAST: Introspection validation failed: {e}",
                context=context,
            )
            raise  # Re-raise to crash the service
        except Exception as e:
            # FAIL-FAST: Critical errors during startup should crash the service
            context = ModelLogContext(
                calling_module=_COMPONENT_NAME,
                calling_function="_publish_introspection_event",
                calling_line=95,
                timestamp=datetime.now().isoformat(),
                node_id=node_id,
            )
            emit_log_event_sync(
                LogLevel.ERROR,
                f"💥 FAIL-FAST: Failed to publish introspection event: {e}",
                context=context,
            )
            raise  # Re-raise to crash the service

    def _gather_introspection_data(self) -> ModelNodeIntrospectionData:
        """
        Gather introspection data for this node from various sources.

        Returns:
            ModelNodeIntrospectionData: Strongly typed introspection data
        """
        try:
            # Extract node information
            node_name = self._extract_node_name()
            version = self._extract_node_version()
            capabilities = self._extract_node_capabilities()
            tags = self._generate_discovery_tags()
            health_endpoint = self._detect_health_endpoint()

            return ModelNodeIntrospectionData(
                node_name=node_name,
                version=version,
                capabilities=capabilities,
                tags=tags,
                health_endpoint=health_endpoint,
            )

        except Exception as e:
            # Fallback to basic introspection
            node_id = getattr(self, "_node_id", "unknown")
            context = ModelLogContext(
                calling_module=_COMPONENT_NAME,
                calling_function="_gather_introspection_data",
                calling_line=127,
                timestamp=datetime.now().isoformat(),
                node_id=node_id,
            )
            emit_log_event_sync(
                LogLevel.WARNING,
                f"Failed to gather full introspection data, using fallback: {e}",
                context=context,
            )

            return ModelNodeIntrospectionData(
                node_name=self.__class__.__name__.lower(),
                version=ModelSemVer(major=1, minor=0, patch=0),
                capabilities=ModelNodeCapabilities(
                    actions=["health_check"],
                    protocols=["event_bus"],
                    metadata={
                        "description": "Event-driven ONEX node",
                        "author": DEFAULT_AUTHOR,
                    },
                ),
                tags=["event_driven"],
                health_endpoint=None,
            )

    def _extract_node_name(self) -> str:
        """Extract node name from class name or metadata."""
        try:
            metadata_loader = getattr(self, "metadata_loader", None)
            if metadata_loader and hasattr(metadata_loader, "metadata"):
                metadata = getattr(metadata_loader, "metadata", None)
                if (
                    metadata
                    and hasattr(metadata, "name")
                    and getattr(metadata, "name", None)
                ):
                    return str(metadata.name)
                if (
                    metadata
                    and hasattr(metadata, "namespace")
                    and getattr(metadata, "namespace", None)
                ):
                    # Extract from namespace like "omnibase.nodes.node_cli"
                    parts = str(metadata.namespace).split(".")
                    if len(parts) >= 3 and parts[-1].startswith("node_"):
                        return parts[-1]
        except Exception:
            pass

        # Fallback to class name
        class_name = self.__class__.__name__
        if class_name.startswith("Node"):
            # Convert "NodeCli" -> "node_cli"
            return re.sub(r"(?<!^)(?=[A-Z])", "_", class_name).lower()

        return class_name.lower()

    def _extract_node_version(self) -> ModelSemVer:
        """Extract node version from metadata."""
        try:
            metadata_loader = getattr(self, "metadata_loader", None)
            if metadata_loader and hasattr(metadata_loader, "metadata"):
                metadata = getattr(metadata_loader, "metadata", None)
                if (
                    metadata
                    and hasattr(metadata, "version")
                    and getattr(metadata, "version", None)
                ):
                    version_str = str(metadata.version)
                    # Use basic parsing instead of from_string to avoid method access issues
                    # Expect format like "1.0.0"
                    parts = version_str.split(".")
                    if len(parts) >= 3:
                        return ModelSemVer(
                            major=int(parts[0]),
                            minor=int(parts[1]),
                            patch=int(parts[2]),
                        )
        except Exception:
            pass

        # Fallback to default version
        return ModelSemVer(major=1, minor=0, patch=0)

    def _extract_node_capabilities(self) -> ModelNodeCapabilities:
        """Extract capabilities from the node."""
        capabilities = ModelNodeCapabilities(
            actions=self._extract_node_actions(),
            protocols=self._detect_supported_protocols(),
            metadata={
                "description": "Event-driven ONEX node",
                "author": DEFAULT_AUTHOR,
            },
        )

        try:
            metadata_loader = getattr(self, "metadata_loader", None)
            if metadata_loader and hasattr(metadata_loader, "metadata"):
                loader_metadata = getattr(metadata_loader, "metadata", None)
                if loader_metadata:
                    if hasattr(loader_metadata, "description") and getattr(
                        loader_metadata,
                        "description",
                        None,
                    ):
                        capabilities.metadata["description"] = str(
                            loader_metadata.description,
                        )
                    if hasattr(loader_metadata, "author") and getattr(
                        loader_metadata,
                        "author",
                        None,
                    ):
                        capabilities.metadata["author"] = str(loader_metadata.author)
                    if hasattr(loader_metadata, "copyright") and getattr(
                        loader_metadata,
                        "copyright",
                        None,
                    ):
                        capabilities.metadata["copyright"] = str(
                            loader_metadata.copyright,
                        )
        except Exception:
            pass

        return capabilities

    def _extract_node_actions(self) -> list[str]:
        """Extract actions from node's contract or state models."""
        actions = []

        try:
            # Try to extract from input state model annotations
            for attr_name in dir(self):
                attr = getattr(self, attr_name, None)
                if attr and hasattr(attr, "__annotations__"):
                    annotations = getattr(attr, "__annotations__", {})
                    if "action" in annotations:
                        action_type = annotations["action"]

                        # Handle Enum types
                        if hasattr(action_type, "__members__"):
                            actions.extend(list(action_type.__members__.keys()))
                        # Handle Literal types
                        elif hasattr(action_type, "__args__"):
                            actions.extend(list(action_type.__args__))
                        break

            # Fallback to method introspection
            if not actions:
                for method_name in dir(self):
                    if method_name.startswith("action_") or method_name.endswith(
                        "_action",
                    ):
                        action_name = method_name.replace("action_", "").replace(
                            "_action",
                            "",
                        )
                        actions.append(action_name)
                    elif method_name in [
                        "health_check",
                        "validate",
                        "process",
                        "configure",
                    ]:
                        actions.append(method_name)

        except Exception:
            pass

        # Ensure we always have at least health_check
        if not actions:
            actions = ["health_check"]
        elif "health_check" not in actions:
            actions.append("health_check")

        return actions

    def _detect_supported_protocols(self) -> list[str]:
        """Detect what protocols this node supports."""
        protocols = ["event_bus"]  # All event-driven nodes support event_bus

        try:
            # Check for MCP support
            if hasattr(self, "mcp_server") or hasattr(self, "supports_mcp"):
                protocols.append("mcp")
            # Check for GraphQL support
            if hasattr(self, "graphql_schema") or hasattr(self, "supports_graphql"):
                protocols.append("graphql")
            # Check for HTTP/REST support
            if hasattr(self, "http_server") or hasattr(self, "supports_http"):
                protocols.append("http")
        except Exception:
            pass

        return protocols

    def _generate_discovery_tags(self) -> list[str]:
        """Generate tags for service discovery."""
        tags = ["event_driven"]

        try:
            # Add class-based tags
            class_name = self.__class__.__name__.lower()
            if "node" in class_name:
                tags.append("node")
            if "cli" in class_name:
                tags.append("cli")
            if "registry" in class_name:
                tags.append("registry")
            if "manager" in class_name:
                tags.append("manager")
            if "generator" in class_name:
                tags.append("generator")
            if "logger" in class_name:
                tags.append("logger")

            # Add protocol-based tags
            if hasattr(self, "supports_mcp") and getattr(self, "supports_mcp", False):
                tags.append("mcp")
            if hasattr(self, "supports_graphql") and getattr(
                self,
                "supports_graphql",
                False,
            ):
                tags.append("graphql")
        except Exception:
            pass

        return list(set(tags))  # Remove duplicates

    def _detect_health_endpoint(self) -> str | None:
        """Detect if this node has a health endpoint."""
        try:
            if hasattr(self, "health_check"):
                node_id = getattr(self, "_node_id", "unknown")
                return f"/health/{node_id}"
        except Exception:
            pass

        return None

    def _publish_with_retry(self, event, max_retries: int = 3) -> None:
        """Publish event with retry logic."""
        event_bus = getattr(self, "event_bus", None)
        if not event_bus:
            return

        node_id = getattr(self, "_node_id", "unknown")

        # Create envelope for the event
        from omnibase_core.models.core.model_event_envelope import ModelEventEnvelope

        envelope = ModelEventEnvelope.create_broadcast(
            payload=event,
            source_node_id=node_id,
            correlation_id=event.correlation_id,
        )

        for attempt in range(max_retries):
            try:
                event_bus.publish(envelope)
                return
            except Exception as e:
                if attempt == max_retries - 1:
                    # Last attempt failed
                    context = ModelLogContext(
                        calling_module=_COMPONENT_NAME,
                        calling_function="_publish_with_retry",
                        calling_line=350,
                        timestamp=datetime.now().isoformat(),
                        node_id=node_id,
                    )
                    emit_log_event_sync(
                        LogLevel.ERROR,
                        f"Failed to publish event after {max_retries} attempts: {e}",
                        context=context,
                    )
                    raise
                # Retry without logging to keep it simple
