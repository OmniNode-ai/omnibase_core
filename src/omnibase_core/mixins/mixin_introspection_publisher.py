from typing import Any, Dict, List
from uuid import UUID

from pydantic import Field

from omnibase_core.constants.event_types import NODE_INTROSPECTION_EVENT
from omnibase_core.models.discovery.model_nodeintrospectionevent import (
    ModelNodeIntrospectionEvent,
)
from omnibase_core.primitives.model_semver import ModelSemVer

"\nIntrospection Publisher Mixin.\n\nThis mixin handles:\n- Gathering node introspection data from various sources\n- Publishing NODE_INTROSPECTION_EVENT for service discovery\n- Extracting actions, protocols, metadata from nodes\n- Retry logic for failed publishes\n"
import re
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ValidationError

from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.logging.structured import emit_log_event_sync
from omnibase_core.mixins.mixin_node_introspection_data import (
    MixinNodeIntrospectionData,
)
from omnibase_core.models.core.model_log_context import ModelLogContext
from omnibase_core.models.discovery.model_node_introspection_event import (
    ModelNodeCapabilities,
)

_COMPONENT_NAME = Path(__file__).stem
DEFAULT_AUTHOR = "ONEX"


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
        requiring manual registration or hardcoded node list[Any]s.
        """
        event_bus = getattr(self, "event_bus", None)
        if not event_bus:
            return
        node_id = getattr(self, "_node_id", "unknown")
        try:
            introspection_data = self._gather_introspection_data()
            from uuid import UUID, uuid4

            correlation_id = uuid4()
            introspection_event = ModelNodeIntrospectionEvent.create_from_node_info(
                node_id=UUID(node_id) if isinstance(node_id, str) else node_id,
                node_name=introspection_data.node_name,
                version=introspection_data.version,
                actions=introspection_data.capabilities.actions,
                protocols=introspection_data.capabilities.protocols,
                metadata=introspection_data.capabilities.metadata,
                tags=introspection_data.tags,
                health_endpoint=introspection_data.health_endpoint,
                correlation_id=correlation_id,
            )
            self._publish_with_retry(introspection_event)
            context = ModelLogContext(
                calling_module=_COMPONENT_NAME,
                calling_function="_publish_introspection_event",
                calling_line=71,
                timestamp=datetime.now().isoformat(),
                node_id=UUID(node_id) if isinstance(node_id, str) else node_id,
            )
            emit_log_event_sync(
                LogLevel.INFO,
                f"Published introspection event for node {node_id}",
                context=context,
            )
        except (ValueError, ValidationError) as e:
            context = ModelLogContext(
                calling_module=_COMPONENT_NAME,
                calling_function="_publish_introspection_event",
                calling_line=95,
                timestamp=datetime.now().isoformat(),
                node_id=UUID(node_id) if isinstance(node_id, str) else node_id,
            )
            emit_log_event_sync(
                LogLevel.ERROR,
                f"💥 FAIL-FAST: Introspection validation failed: {e}",
                context=context,
            )
            raise
        except Exception as e:
            context = ModelLogContext(
                calling_module=_COMPONENT_NAME,
                calling_function="_publish_introspection_event",
                calling_line=95,
                timestamp=datetime.now().isoformat(),
                node_id=UUID(node_id) if isinstance(node_id, str) else node_id,
            )
            emit_log_event_sync(
                LogLevel.ERROR,
                f"💥 FAIL-FAST: Failed to publish introspection event: {e}",
                context=context,
            )
            raise

    def _gather_introspection_data(self) -> MixinNodeIntrospectionData:
        """
        Gather introspection data for this node from various sources.

        Returns:
            MixinNodeIntrospectionData: Strongly typed introspection data
        """
        try:
            node_name = self._extract_node_name()
            version = self._extract_node_version()
            capabilities = self._extract_node_capabilities()
            tags = self._generate_discovery_tags()
            health_endpoint = self._detect_health_endpoint()
            return MixinNodeIntrospectionData(
                node_name=node_name,
                version=version,
                capabilities=capabilities,
                tags=tags,
                health_endpoint=health_endpoint,
            )
        except Exception as e:
            # fallback-ok: Introspection failures use fallback data with logging
            node_id = getattr(self, "_node_id", "unknown")
            context = ModelLogContext(
                calling_module=_COMPONENT_NAME,
                calling_function="_gather_introspection_data",
                calling_line=127,
                timestamp=datetime.now().isoformat(),
                node_id=UUID(node_id) if isinstance(node_id, str) else node_id,
            )
            emit_log_event_sync(
                LogLevel.WARNING,
                f"Failed to gather full introspection data, using fallback: {e}",
                context=context,
            )
            return MixinNodeIntrospectionData(
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
                    parts = str(metadata.namespace).split(".")
                    if len(parts) >= 3 and parts[-1].startswith("node_"):
                        return parts[-1]
        except Exception:
            pass
        class_name = self.__class__.__name__
        if class_name.startswith("Node"):
            return re.sub("(?<!^)(?=[A-Z])", "_", class_name).lower()
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
                    parts = version_str.split(".")
                    if len(parts) >= 3:
                        return ModelSemVer(
                            major=int(parts[0]),
                            minor=int(parts[1]),
                            patch=int(parts[2]),
                        )
        except Exception:
            pass
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
                        loader_metadata, "description", None
                    ):
                        capabilities.metadata["description"] = str(
                            loader_metadata.description
                        )
                    if hasattr(loader_metadata, "author") and getattr(
                        loader_metadata, "author", None
                    ):
                        capabilities.metadata["author"] = str(loader_metadata.author)
                    if hasattr(loader_metadata, "copyright") and getattr(
                        loader_metadata, "copyright", None
                    ):
                        capabilities.metadata["copyright"] = str(
                            loader_metadata.copyright
                        )
        except Exception:
            pass
        return capabilities

    def _extract_node_actions(self) -> list[str]:
        """Extract actions from node's contract or state models."""
        actions = []
        try:
            for attr_name in dir(self):
                attr = getattr(self, attr_name, None)
                if attr and hasattr(attr, "__annotations__"):
                    annotations = getattr(attr, "__annotations__", {})
                    if "action" in annotations:
                        action_type = annotations["action"]
                        if hasattr(action_type, "__members__"):
                            actions.extend(list[Any](action_type.__members__.keys()))
                        elif hasattr(action_type, "__args__"):
                            actions.extend(list[Any](action_type.__args__))
                        break
            if not actions:
                for method_name in dir(self):
                    if method_name.startswith("action_") or method_name.endswith(
                        "_action"
                    ):
                        action_name = method_name.replace("action_", "").replace(
                            "_action", ""
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
        if not actions:
            actions = ["health_check"]
        elif "health_check" not in actions:
            actions.append("health_check")
        return actions

    def _detect_supported_protocols(self) -> list[str]:
        """Detect what protocols this node supports."""
        protocols = ["event_bus"]
        try:
            if hasattr(self, "mcp_server") or hasattr(self, "supports_mcp"):
                protocols.append("mcp")
            if hasattr(self, "graphql_schema") or hasattr(self, "supports_graphql"):
                protocols.append("graphql")
            if hasattr(self, "http_server") or hasattr(self, "supports_http"):
                protocols.append("http")
        except Exception:
            pass
        return protocols

    def _generate_discovery_tags(self) -> list[str]:
        """Generate tags for service discovery."""
        tags = ["event_driven"]
        try:
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
            if hasattr(self, "supports_mcp") and getattr(self, "supports_mcp", False):
                tags.append("mcp")
            if hasattr(self, "supports_graphql") and getattr(
                self, "supports_graphql", False
            ):
                tags.append("graphql")
        except Exception:
            pass
        return list(set(tags))

    def _detect_health_endpoint(self) -> str | None:
        """Detect if this node has a health endpoint."""
        try:
            if hasattr(self, "health_check"):
                node_id = getattr(self, "_node_id", "unknown")
                return f"/health/{node_id}"
        except Exception:
            pass
        return None

    def _publish_with_retry(self, event: Any, max_retries: int = 3) -> None:
        """Publish event with retry logic."""
        event_bus = getattr(self, "event_bus", None)
        if not event_bus:
            return
        node_id = getattr(self, "_node_id", "unknown")
        from omnibase_core.models.core.model_event_envelope import ModelEventEnvelope

        source_node_id_str: str
        if isinstance(node_id, str):
            source_node_id_str = node_id
        elif isinstance(node_id, UUID):
            source_node_id_str = str(node_id)
        else:
            source_node_id_str = "unknown"
        envelope = ModelEventEnvelope.create_broadcast(
            payload=event,
            source_node_id=source_node_id_str,
            correlation_id=event.correlation_id,
        )
        for attempt in range(max_retries):
            try:
                event_bus.publish(envelope)
                return
            except Exception as e:
                if attempt == max_retries - 1:
                    context = ModelLogContext(
                        calling_module=_COMPONENT_NAME,
                        calling_function="_publish_with_retry",
                        calling_line=350,
                        timestamp=datetime.now().isoformat(),
                        node_id=UUID(node_id) if isinstance(node_id, str) else node_id,
                    )
                    emit_log_event_sync(
                        LogLevel.ERROR,
                        f"Failed to publish event after {max_retries} attempts: {e}",
                        context=context,
                    )
                    raise
