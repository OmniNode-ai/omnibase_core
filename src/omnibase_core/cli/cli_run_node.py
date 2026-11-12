# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""``onex run-node`` — dispatch a packaged node on the bus its contract overlay declares (OMN-22362)."""

from __future__ import annotations

import importlib
import json
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import NoReturn
from uuid import UUID

import click

from omnibase_core.cli.cli_node import _resolve_packaged_contract
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.event_bus.util_consumer_group import derive_service_group_id
from omnibase_core.models.core.model_generic_yaml import ModelGenericYaml
from omnibase_core.models.event_bus.model_consumer_group_scope import (
    ModelConsumerGroupScope,
)
from omnibase_core.models.event_bus.model_node_broker_binding import (
    ModelNodeBrokerBinding,
)
from omnibase_core.models.event_bus.model_node_broker_resolution_error import (
    ModelNodeBrokerResolutionError,
)
from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
from omnibase_core.utils.util_safe_yaml_loader import load_and_validate_yaml_model

# Service and node tokens for the one-shot consumer this CLI creates.
RUN_NODE_SERVICE = "omnibase_core"
RUN_NODE_NAME = "cli_run_node"


def derive_run_node_group_id(correlation_id: UUID) -> str:
    """Derive the ephemeral consumer group ID for one ``onex run-node`` invocation.

    This consumer is genuinely one-shot — a single request/response round trip — so it
    needs a unique group per invocation. Before OMN-15639 the uniqueness was expressed
    as the literal ``f"onex-run-node-{correlation_id}"``, which no MSK IAM pattern
    authorized. The correlation ID is now carried as a declared scope discriminator
    instead, so the environment token still leads and the name stays authorized while
    remaining unique per run.

    Args:
        correlation_id: The invocation's correlation UUID.

    Returns:
        An environment-qualified, per-invocation consumer group ID.
    """
    return derive_service_group_id(
        RUN_NODE_NAME,
        service=RUN_NODE_SERVICE,
        scope=ModelConsumerGroupScope(correlation_id=correlation_id),
    )


def load_workflow_contract(path: Path) -> dict[str, object]:
    """Load and validate packaged workflow contract metadata for Kafka dispatch."""
    raw_model = load_and_validate_yaml_model(path, ModelGenericYaml)
    return raw_model.model_dump(mode="json", exclude_none=True)


def _emit_error(node_id: str, message: str, **extra: str | int) -> NoReturn:
    """Emit a SkillRoutingError JSON envelope and exit non-zero."""
    envelope: dict[str, str | int] = {
        "error_type": "SkillRoutingError",
        "message": message,
        "node_id": node_id,
        **extra,
    }
    click.echo(json.dumps(envelope, indent=2))
    sys.exit(1)


def _resolve_binding(node_id: str) -> ModelNodeBrokerBinding:
    """The broker ``node_id`` is reached on, from its contract overlay alone (OMN-22362).

    No environment variable, flag or default selects it; a refusal names the overlay path.
    """
    try:
        return ModelNodeBrokerBinding.for_node(node_id)
    except ModelNodeBrokerResolutionError as exc:
        extra: dict[str, str | int] = {"cause": "ModelNodeBrokerResolutionError"}
        if exc.overlay_path is not None:
            extra["overlay_path"] = exc.overlay_path
        _emit_error(node_id, exc.message, **extra)


def run_node_in_process(
    node_id: str, contract_path: Path, payload: dict[str, object], timeout: int
) -> dict[str, object]:
    """Host the node here on the in-memory bus (overlay ``type: inmemory``, OMN-22362)."""
    # The overlay declared an in-memory runtime, so the run declares event_bus=inmemory: with one
    # forwarder installed its recorded events reach the hosted bus, with none it says so (OMN-24000).
    from pydantic import BaseModel

    from omnibase_core.enums.enum_workflow_result import EnumWorkflowResult
    from omnibase_core.runtime.runtime_local import RuntimeLocal

    with tempfile.TemporaryDirectory(prefix="onex-run-node-") as scratch:
        input_path = Path(scratch) / "input.json"
        input_path.write_text(json.dumps(payload), encoding="utf-8")
        runtime = RuntimeLocal(
            workflow_path=contract_path,
            state_root=Path(scratch) / "state",
            input_path=input_path,
            timeout=timeout,
            backend_overrides={"event_bus": "inmemory"},
        )
        result = runtime.run()
    if result is not EnumWorkflowResult.COMPLETED:
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.RUNTIME_ERROR,
            message=f"Node '{node_id}' hosted in process ended {result.value}: "
            f"{runtime.last_error or 'no error recorded'}",
        )
    produced = runtime.handler_result
    if isinstance(produced, BaseModel):
        return produced.model_dump(mode="json")
    return dict(produced) if isinstance(produced, dict) else {"result": produced}


def _coerce_contract_metadata(
    contract: ModelGenericYaml | dict[str, object],
) -> dict[str, object]:
    """Normalize tests and production loaders to the metadata model."""
    if isinstance(contract, ModelGenericYaml):
        return contract.model_dump(mode="json", exclude_none=True)
    return contract


def _contract_requires_payload_correlation_id(
    contract: dict[str, object],
) -> bool:
    """Return True when the contract explicitly requires payload.correlation_id."""
    inputs = contract.get("inputs")
    if not isinstance(inputs, dict):
        return False
    correlation_spec = inputs.get("correlation_id")
    if not isinstance(correlation_spec, dict):
        return False
    return correlation_spec.get("required") is True


def _resolve_node_topics(node_id: str) -> tuple[Path, str, str, bool]:
    """Resolve a packaged node to its contract path and Kafka routing metadata."""
    contract_path = _resolve_packaged_contract(node_id)
    contract = _coerce_contract_metadata(load_workflow_contract(Path(contract_path)))

    event_bus = contract.get("event_bus")
    if not isinstance(event_bus, dict):
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=(
                f"Node '{node_id}' contract at {contract_path} is missing an "
                "event_bus mapping"
            ),
        )

    subscribe_topics = event_bus.get("subscribe_topics")
    if not isinstance(subscribe_topics, list) or not subscribe_topics:
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=(
                f"Node '{node_id}' contract at {contract_path} does not declare "
                "event_bus.subscribe_topics"
            ),
        )

    command_topic = subscribe_topics[0]
    if not isinstance(command_topic, str) or not command_topic.strip():
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=(
                f"Node '{node_id}' contract at {contract_path} has an invalid "
                "primary subscribe topic"
            ),
        )

    terminal_event = contract.get("terminal_event")
    if not isinstance(terminal_event, str) or not terminal_event.strip():
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=(
                f"Node '{node_id}' contract at {contract_path} does not declare "
                "a terminal_event"
            ),
        )

    return (
        contract_path,
        command_topic,
        terminal_event,
        _contract_requires_payload_correlation_id(contract),
    )


def _normalize_payload(
    payload: dict[str, object],
    correlation_id: UUID,
    inject_payload_correlation_id: bool,
) -> dict[str, object]:
    """Ensure the payload carries a correlation_id for input models that require one."""
    normalized = dict(payload)
    if inject_payload_correlation_id and normalized.get("correlation_id") in (None, ""):
        normalized["correlation_id"] = str(correlation_id)
    return normalized


def publish_and_poll(
    node_id: str,
    payload: dict[str, object],
    timeout: int,
    bootstrap_servers: str,
    command_topic: str,
    response_topic: str,
    inject_payload_correlation_id: bool = False,
    client_security: dict[str, str] | None = None,
) -> dict[str, object] | None:
    """Publish a contract-routed command envelope and poll for its terminal event.

    ``client_security`` carries the librdkafka security settings; both clients use them.

    Returns the response dict, or None on timeout.
    """
    security = dict(client_security or {})
    try:
        _ck = importlib.import_module("confluent_kafka")
        # NOTE(OMN-9715): lazy importlib import preserves ADR-005 transport boundary
        Producer = _ck.Producer
        Consumer = _ck.Consumer
        OFFSET_END = _ck.OFFSET_END
        TopicPartition = _ck.TopicPartition
    except ImportError as exc:
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.IMPORT_ERROR,
            message=(
                "confluent-kafka is required for run-node. "
                "Install with: uv add omnibase-core[kafka]"
            ),
        ) from exc

    correlation_uuid = uuid.uuid4()
    correlation_id = str(correlation_uuid)
    normalized_payload = _normalize_payload(
        payload,
        correlation_uuid,
        inject_payload_correlation_id,
    )
    envelope = ModelEventEnvelope[object](
        payload=normalized_payload,
        correlation_id=correlation_uuid,
        source_tool="onex.run-node",
        target_tool=node_id,
    )

    delivery_error: list[Exception] = []

    def _on_delivery(err: object, _msg: object) -> None:
        if err is not None:
            delivery_error.append(
                ModelOnexError(
                    error_code=EnumCoreErrorCode.RUNTIME_ERROR,
                    message=f"Kafka delivery failed: {err}",
                )
            )

    deadline = time.monotonic() + timeout
    consumer = Consumer(
        {
            "bootstrap.servers": bootstrap_servers,
            **security,
            "group.id": derive_run_node_group_id(correlation_uuid),
            "auto.offset.reset": "latest",
            "enable.auto.commit": False,
        }
    )
    try:
        # Explicit assignment is more reliable than ephemeral group rebalances
        # for one-shot request/response flows.
        try:
            metadata = consumer.list_topics(response_topic, timeout=10.0)
        except Exception as exc:
            # OMN-13857: the first broker touch fails with a raw
            # confluent_kafka.KafkaException (_TRANSPORT) when the bootstrap
            # address is unreachable. Convert it into an actionable error
            # instead of surfacing an opaque traceback.
            # OMN-17427: a SASL listener closes an unauthenticated connection
            # with the same _TRANSPORT error, so name the security env when
            # none is configured. Only the protocol is ever echoed.
            protocol = security.get("security.protocol")
            auth_hint = (
                f" The client connected with security.protocol={protocol}."
                if protocol
                else " The lane declares no security protocol, so the client "
                "connected in plaintext; a lane broker that requires SASL closes "
                "an unauthenticated connection with this same error."
            )
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.RUNTIME_ERROR,
                message=(
                    f"Kafka broker unreachable at {bootstrap_servers!r}: {exc}. "
                    "Verify the lane named in the node's contract overlay is "
                    "reachable from this host, or run the node locally (bus-less) "
                    f"with `onex run {node_id}`.{auth_hint}"
                ),
            ) from exc
        topic_metadata = metadata.topics.get(response_topic)
        if topic_metadata is None or getattr(topic_metadata, "error", None) is not None:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.RUNTIME_ERROR,
                message=f"Kafka topic metadata unavailable for {response_topic}",
            )

        response_partitions: list[object] = []
        for partition_id in sorted(topic_metadata.partitions):
            response_partitions.append(
                TopicPartition(response_topic, partition_id, OFFSET_END)
            )

        if not response_partitions:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.RUNTIME_ERROR,
                message=f"Kafka topic {response_topic} has no partitions",
            )

        consumer.assign(response_partitions)

        producer = Producer({"bootstrap.servers": bootstrap_servers, **security})
        producer.produce(
            topic=command_topic,
            value=envelope.model_dump_json().encode(),
            on_delivery=_on_delivery,
        )
        pending = producer.flush(timeout=10.0)
        if pending:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.RUNTIME_ERROR,
                message=f"Kafka flush timed out with {pending} queued message(s)",
            )

        if delivery_error:
            raise delivery_error[0]

        while True:
            now = time.monotonic()
            remaining = deadline - now
            if remaining <= 0:
                break
            msg = consumer.poll(timeout=min(remaining, 1.0))
            if msg is None:
                continue
            if msg.error():
                continue
            raw = msg.value()
            if raw is None:
                continue
            try:
                data: dict[str, object] = json.loads(raw.decode())
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            if data.get("correlation_id") == correlation_id:
                return data
    finally:
        consumer.close()

    return None


@click.command("run-node")
@click.argument("node_id")
@click.option(
    "--input",
    "input_json",
    required=True,
    help="JSON payload to send to the node.",
)
@click.option(
    "--timeout",
    type=int,
    default=30,
    show_default=True,
    help="Max seconds to wait for a response.",
)
def run_node(node_id: str, input_json: str, timeout: int) -> None:
    """Execute a packaged ONEX node on the bus its contract overlay declares.

    ``type: kafka`` publishes to the lane's runtime and polls the node's terminal_event;
    ``type: inmemory`` hosts the node in this process. No environment variable, flag or
    default selects the broker; a node with no overlay is refused naming the overlay path.
    Counterpart of `onex run`. Exits non-zero emitting a SkillRoutingError JSON envelope.
    """
    try:
        payload = json.loads(input_json)
    except json.JSONDecodeError as exc:
        _emit_error(node_id, f"Invalid JSON input: {exc}")

    binding = _resolve_binding(node_id)

    try:
        (
            contract_path,
            command_topic,
            response_topic,
            inject_payload_correlation_id,
        ) = _resolve_node_topics(node_id)
        if binding.bus_type.requires_broker:
            response = publish_and_poll(
                node_id=node_id,
                payload=payload,
                timeout=timeout,
                bootstrap_servers=binding.bootstrap_servers or "",
                command_topic=command_topic,
                response_topic=response_topic,
                inject_payload_correlation_id=inject_payload_correlation_id,
                client_security=binding.client_security(),
            )
        else:
            response = {
                "payload": run_node_in_process(
                    node_id,
                    contract_path,
                    _normalize_payload(
                        payload, uuid.uuid4(), inject_payload_correlation_id
                    ),
                    timeout,
                )
            }
    except (ConnectionError, OSError, ImportError, ModelOnexError) as exc:
        _emit_error(node_id, str(exc))

    if response is None:
        _emit_error(
            node_id,
            f"Timeout after {timeout}s waiting for response from {node_id}",
            timeout_seconds=timeout,
        )

    click.echo(json.dumps(response.get("payload", response), indent=2))
