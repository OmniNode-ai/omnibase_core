"""Mixin for publishing node contracts on startup for dynamic discovery.

This mixin provides contract registration capability for ONEX nodes.
On startup, nodes publish their contracts to Kafka for dynamic discovery
by other services (e.g., contract registries, dashboards).

Architecture:
    Node startup → publish_contract() → Kafka (contract topic)
        → ContractRegistry → Updates contract catalog

Usage:
    class MyNode(MixinContractPublisher):
        def __init__(self, container):
            super().__init__(container)
            self._init_contract_publisher(container)

        async def on_start(self):
            await self.publish_contract(Path("contract.yaml"))
            await self.start_heartbeat(interval_seconds=30)

        async def on_stop(self):
            await self.stop_heartbeat()
            await self.publish_deregistration(reason=EnumDeregistrationReason.SHUTDOWN)

Part of omnibase_core framework - enables dynamic contract discovery (OMN-1655).
"""

from __future__ import annotations

import asyncio
import hashlib
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import UUID

import yaml

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.events.enum_deregistration_reason import (
    EnumDeregistrationReason,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.events.contract_registration import (
    CONTRACT_DEREGISTERED_EVENT,
    CONTRACT_REGISTERED_EVENT,
    NODE_HEARTBEAT_EVENT,
    ModelContractDeregisteredEvent,
    ModelContractRegisteredEvent,
    ModelNodeHeartbeatEvent,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.protocols.event_bus.protocol_event_bus_publisher import (
    ProtocolEventBusPublisher,
)

if TYPE_CHECKING:
    from omnibase_core.models.container.model_onex_container import ModelONEXContainer


class MixinContractPublisher:
    """Mixin for nodes to publish their contracts on startup.

    Provides methods to:
    - Publish contract registration events with full YAML for replay capability
    - Publish deregistration events for graceful shutdown
    - Run background heartbeat tasks for liveness monitoring

    Thread Safety:
        This mixin is async-safe. Multiple concurrent calls are supported.
        The heartbeat task runs in the background and can be safely cancelled.
    """

    _contract_publisher: ProtocolEventBusPublisher
    _heartbeat_task: asyncio.Task[None] | None
    _heartbeat_sequence: int
    _startup_time: datetime
    _current_contract_hash: str | None
    _current_node_name: str | None
    _current_node_version: ModelSemVer | None
    _current_source_node_id: UUID | None

    def _init_contract_publisher(
        self,
        container: ModelONEXContainer,
        publisher: ProtocolEventBusPublisher | None = None,
    ) -> None:
        """Initialize contract publishing capability.

        Must be called in node's __init__ after super().__init__().

        Args:
            container: ONEX container with services.
            publisher: Optional publisher instance. If not provided,
                resolves "ProtocolEventBusPublisher" from container.

        Raises:
            ModelOnexError: If publisher service is not available.
        """
        if publisher is not None:
            self._contract_publisher = publisher
        else:
            # NOTE(OMN-1655): get_service returns object by Protocol definition. Safe because
            # we verify resolved is not None before assignment.
            resolved: object | None = container.get_service("ProtocolEventBusPublisher")  # type: ignore[arg-type]
            if resolved is None:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.SERVICE_UNAVAILABLE,
                    message=(
                        "MixinContractPublisher requires 'ProtocolEventBusPublisher' "
                        "service in container. Ensure event bus publisher is registered "
                        "before initializing nodes."
                    ),
                )
            # NOTE(OMN-1655): Assignment safe - we verify resolved is ProtocolEventBusPublisher
            # via the container registration, and checked for None above.
            self._contract_publisher = resolved  # type: ignore[assignment]

        self._heartbeat_task = None
        self._heartbeat_sequence = 0
        self._startup_time = datetime.now(UTC)
        self._current_contract_hash = None
        self._current_node_name = None
        self._current_node_version = None
        self._current_source_node_id = None

    async def publish_contract(
        self,
        contract_path: Path,
        source_node_id: UUID | None = None,
        correlation_id: UUID | None = None,
    ) -> ModelContractRegisteredEvent:
        """Read contract YAML, compute hash, and publish registration event.

        Args:
            contract_path: Path to the contract.yaml file.
            source_node_id: Optional node ID for event attribution.
            correlation_id: Optional correlation ID for request tracing.

        Returns:
            The published ModelContractRegisteredEvent.

        Raises:
            ModelOnexError: If contract file cannot be read or parsed.
        """
        # Read contract file
        try:
            contract_yaml = contract_path.read_text(encoding="utf-8")
        except FileNotFoundError as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.FILE_NOT_FOUND,
                message=f"Contract file not found: {contract_path}",
                context={"path": str(contract_path)},
            ) from e
        except OSError as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.FILE_READ_ERROR,
                message=f"Failed to read contract file: {e}",
                context={"path": str(contract_path)},
            ) from e

        # Compute SHA256 hash
        contract_hash = hashlib.sha256(contract_yaml.encode("utf-8")).hexdigest()

        # Parse YAML to extract node_name and version
        try:
            contract_data = yaml.safe_load(
                contract_yaml
            )  # yaml-ok: Extracting name/version from raw contract
        except yaml.YAMLError as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.CONFIGURATION_PARSE_ERROR,
                message=f"Failed to parse contract YAML: {e}",
                context={"path": str(contract_path)},
            ) from e

        if not isinstance(contract_data, dict):
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR,
                message="Contract YAML must be a mapping (dict)",
                context={
                    "path": str(contract_path),
                    "type": type(contract_data).__name__,
                },
            )

        node_name = contract_data.get("name")
        if not node_name:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR,
                message="Contract must have a 'name' field",
                context={"path": str(contract_path)},
            )

        version_str = contract_data.get("version", "0.0.0")
        node_version = ModelSemVer.parse(version_str)

        # Store for heartbeats and deregistration
        self._current_contract_hash = contract_hash
        self._current_node_name = node_name
        self._current_node_version = node_version
        self._current_source_node_id = source_node_id

        # Create registration event
        event = ModelContractRegisteredEvent(
            node_name=node_name,
            node_version=node_version,
            contract_hash=contract_hash,
            contract_yaml=contract_yaml,
            source_node_id=source_node_id,
            correlation_id=correlation_id,
        )

        # Publish to Kafka
        await self._contract_publisher.publish(
            topic=CONTRACT_REGISTERED_EVENT,
            key=node_name.encode("utf-8"),
            value=event.model_dump_json().encode("utf-8"),
        )

        return event

    async def publish_deregistration(
        self,
        reason: EnumDeregistrationReason = EnumDeregistrationReason.SHUTDOWN,
        correlation_id: UUID | None = None,
    ) -> ModelContractDeregisteredEvent | None:
        """Publish contract deregistration event for graceful shutdown.

        Args:
            reason: Reason for deregistration.
            correlation_id: Optional correlation ID for request tracing.

        Returns:
            The published event, or None if no contract was registered.
        """
        if self._current_node_name is None or self._current_node_version is None:
            return None

        event = ModelContractDeregisteredEvent(
            node_name=self._current_node_name,
            node_version=self._current_node_version,
            reason=reason,
            source_node_id=self._current_source_node_id,
            correlation_id=correlation_id,
        )

        await self._contract_publisher.publish(
            topic=CONTRACT_DEREGISTERED_EVENT,
            key=self._current_node_name.encode("utf-8"),
            value=event.model_dump_json().encode("utf-8"),
        )

        return event

    async def start_heartbeat(self, interval_seconds: int = 30) -> None:
        """Start background task to emit heartbeat events.

        Args:
            interval_seconds: Interval between heartbeats in seconds.

        Raises:
            ModelOnexError: If interval is less than 1 second.
        """
        if interval_seconds < 1:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Heartbeat interval must be at least 1 second, got: {interval_seconds}",
                context={"interval_seconds": interval_seconds},
            )

        if self._heartbeat_task is not None and not self._heartbeat_task.done():
            return  # Already running

        self._heartbeat_task = asyncio.create_task(
            self._heartbeat_loop(interval_seconds),
            name=f"heartbeat-{self._current_node_name or 'unknown'}",
        )

    async def stop_heartbeat(self) -> None:
        """Stop the background heartbeat task."""
        if self._heartbeat_task is not None and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass  # Expected
            self._heartbeat_task = None

    async def _heartbeat_loop(self, interval_seconds: int) -> None:
        """Internal heartbeat loop - runs until cancelled."""
        while True:
            try:
                await self._emit_heartbeat()
                await asyncio.sleep(interval_seconds)
            except asyncio.CancelledError:
                raise  # Propagate cancellation
            except Exception:
                # Swallow error and continue heartbeating - transient errors shouldn't
                # stop liveness signals. Consumers can detect issues via heartbeat gaps.
                await asyncio.sleep(interval_seconds)

    async def _emit_heartbeat(self) -> None:
        """Emit a single heartbeat event."""
        if self._current_node_name is None or self._current_node_version is None:
            return

        self._heartbeat_sequence += 1
        uptime = (datetime.now(UTC) - self._startup_time).total_seconds()

        event = ModelNodeHeartbeatEvent(
            node_name=self._current_node_name,
            node_version=self._current_node_version,
            sequence_number=self._heartbeat_sequence,
            uptime_seconds=uptime,
            contract_hash=self._current_contract_hash,
            source_node_id=self._current_source_node_id,
        )

        await self._contract_publisher.publish(
            topic=NODE_HEARTBEAT_EVENT,
            key=self._current_node_name.encode("utf-8"),
            value=event.model_dump_json().encode("utf-8"),
        )


__all__ = ["MixinContractPublisher"]
