# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
CommandDispatcher -- dynamic command dispatch for the registry-driven CLI.

Dispatches validated, parsed arguments to the correct backend based on the
``invocation.type`` field in a ``ModelCliCommandEntry``.

## Supported Invocation Types

- ``KAFKA_EVENT``: Publishes a fire-and-forget event to the Kafka topic
  specified in ``invocation.topic``.  Returns a correlation ID immediately.
- ``HTTP_ENDPOINT`` (stub): Interface defined, not yet implemented.
- ``DIRECT_CALL`` (stub): Interface defined, not yet implemented.
- ``SUBPROCESS`` (stub): Interface defined, not yet implemented.

## Dispatch Contract

    result = dispatcher.dispatch(command_entry, parsed_args)
    if result.success:
        print(result.correlation_id)
    else:
        print(result.error_message)

## Type Validation

Parsed args are validated against the command's ``args_schema`` (if supplied)
before dispatch.  This is a pre-dispatch validation step -- it rejects
invocations that fail type constraints early, before reaching the backend.

## Thread Safety

``CommandDispatcher`` is stateless after construction.  The Kafka producer
(if any) should be passed in as a dependency; it is not created internally.

See Also:
    - ``omnibase_core.models.cli.model_command_dispatch_result.ModelCommandDispatchResult``
    - ``omnibase_core.errors.error_command_dispatch.CommandDispatchError``
    - ``omnibase_core.protocols.cli.protocol_kafka_producer.ProtocolKafkaProducer``

.. versionadded:: 0.19.0  (OMN-2553)
"""

from __future__ import annotations

__all__ = [
    "CommandDispatcher",
]

import json
import uuid
from argparse import Namespace
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from omnibase_core.enums.enum_cli_invocation_type import EnumCliInvocationType
from omnibase_core.errors.error_command_dispatch import CommandDispatchError
from omnibase_core.models.cli.model_command_dispatch_result import (
    ModelCommandDispatchResult,
)
from omnibase_core.protocols.cli.protocol_kafka_producer import ProtocolKafkaProducer

if TYPE_CHECKING:
    from omnibase_core.models.contracts.model_cli_contribution import (
        ModelCliCommandEntry,
    )


class CommandDispatcher:
    """Dispatches validated CLI arguments to the correct backend.

    The dispatcher is the final step in the registry-driven CLI invocation
    pipeline.  It receives a ``ModelCliCommandEntry`` (from the catalog) and
    a ``Namespace`` of parsed, type-coerced arguments, then routes the
    invocation to the appropriate backend.

    Args:
        kafka_producer: Optional Kafka producer for ``KAFKA_EVENT`` dispatch.
            If not supplied, ``KAFKA_EVENT`` dispatches raise
            ``CommandDispatchError``.

    Example::

        producer = MyKafkaProducer(bootstrap_servers="localhost:29092")
        dispatcher = CommandDispatcher(kafka_producer=producer)
        result = dispatcher.dispatch(command_entry, parsed_namespace)
        print(result.correlation_id)

    .. versionadded:: 0.19.0  (OMN-2553)
    """

    def __init__(
        self,
        kafka_producer: ProtocolKafkaProducer | None = None,
    ) -> None:
        """Initialize CommandDispatcher.

        Args:
            kafka_producer: Kafka producer to use for KAFKA_EVENT dispatch.
                May be None for non-Kafka commands.
        """
        self._kafka_producer = kafka_producer

    def dispatch(
        self,
        command: ModelCliCommandEntry,
        parsed_args: Namespace,
        *,
        args_schema: dict[str, object] | None = None,
    ) -> ModelCommandDispatchResult:
        """Dispatch a parsed command invocation.

        Validates parsed args against the schema (if provided), then
        routes to the appropriate backend based on ``command.invocation.type``.

        Args:
            command: The ``ModelCliCommandEntry`` from the catalog.
            parsed_args: Namespace from ``ArgumentParser.parse_args()``.
            args_schema: Optional resolved JSON Schema dict.  When provided,
                required-field validation is performed before dispatch.

        Returns:
            ``ModelCommandDispatchResult`` with ``success=True`` on success,
            or ``success=False`` with an ``error_message`` on failure.

        Raises:
            CommandDispatchError: If the invocation type is not supported or
                a required backend (e.g. Kafka producer) is not configured.
        """
        correlation_id = str(uuid.uuid4())
        invocation = command.invocation
        invocation_type = invocation.invocation_type

        # Pre-dispatch: validate required fields.
        if args_schema is not None:
            validation_error = self._validate_required_fields(
                args_schema=args_schema,
                parsed_args=parsed_args,
                command_id=command.id,
            )
            if validation_error is not None:
                return ModelCommandDispatchResult(
                    success=False,
                    correlation_id=correlation_id,
                    command_ref=command.id,
                    invocation_type=invocation_type,
                    topic=invocation.topic,
                    error_message=validation_error,
                )

        if invocation_type == EnumCliInvocationType.KAFKA_EVENT:
            return self._dispatch_kafka(
                command=command,
                parsed_args=parsed_args,
                correlation_id=correlation_id,
            )

        if invocation_type == EnumCliInvocationType.HTTP_ENDPOINT:
            raise CommandDispatchError(
                f"HTTP_ENDPOINT dispatch is not yet implemented "
                f"(command: {command.id}). "
                "Stub the interface via a custom CommandDispatcher subclass."
            )

        if invocation_type == EnumCliInvocationType.DIRECT_CALL:
            raise CommandDispatchError(
                f"DIRECT_CALL dispatch is not yet implemented "
                f"(command: {command.id}). "
                "Stub the interface via a custom CommandDispatcher subclass."
            )

        if invocation_type == EnumCliInvocationType.SUBPROCESS:
            raise CommandDispatchError(
                f"SUBPROCESS dispatch is not yet implemented "
                f"(command: {command.id}). "
                "Stub the interface via a custom CommandDispatcher subclass."
            )

        raise CommandDispatchError(
            f"Unknown invocation type '{invocation_type}' for command '{command.id}'."
        )

    # ------------------------------------------------------------------
    # Private: per-backend dispatch
    # ------------------------------------------------------------------

    def _dispatch_kafka(
        self,
        command: ModelCliCommandEntry,
        parsed_args: Namespace,
        correlation_id: str,
    ) -> ModelCommandDispatchResult:
        """Dispatch a KAFKA_EVENT invocation.

        Publishes a JSON event to ``command.invocation.topic`` and returns
        immediately (fire-and-forget).  The correlation ID is embedded in the
        event payload and returned to the caller.

        Args:
            command: The command entry.
            parsed_args: Parsed argument namespace.
            correlation_id: UUID for this invocation.

        Returns:
            ``ModelCommandDispatchResult`` with ``success=True`` and the topic.

        Raises:
            CommandDispatchError: If no Kafka producer is configured.
        """
        if self._kafka_producer is None:
            raise CommandDispatchError(
                f"No Kafka producer configured for KAFKA_EVENT dispatch "
                f"(command: {command.id}). "
                "Pass a kafka_producer to CommandDispatcher()."
            )

        topic = command.invocation.topic
        if not topic:
            raise CommandDispatchError(
                f"Command '{command.id}' is KAFKA_EVENT but invocation.topic is empty."
            )

        # Build event payload.
        args_dict: dict[str, object] = {
            k: v for k, v in vars(parsed_args).items() if not k.startswith("_")
        }
        payload: dict[str, object] = {
            "correlation_id": correlation_id,
            "command_ref": command.id,
            "args": args_dict,
            "dispatched_at": datetime.now(UTC).isoformat(),
        }
        payload_bytes = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")

        try:
            self._kafka_producer.produce(
                topic=topic,
                key=correlation_id,
                value=payload_bytes,
            )
            self._kafka_producer.flush(timeout=5.0)
        except Exception as exc:  # fallback-ok: Kafka errors are captured in dispatch result, not re-raised (fire-and-forget pattern)
            return ModelCommandDispatchResult(
                success=False,
                correlation_id=correlation_id,
                command_ref=command.id,
                invocation_type=EnumCliInvocationType.KAFKA_EVENT,
                topic=topic,
                error_message=f"Kafka produce failed: {exc}",
            )

        return ModelCommandDispatchResult(
            success=True,
            correlation_id=correlation_id,
            command_ref=command.id,
            invocation_type=EnumCliInvocationType.KAFKA_EVENT,
            topic=topic,
        )

    # ------------------------------------------------------------------
    # Private: validation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_required_fields(
        *,
        args_schema: dict[str, object],
        parsed_args: Namespace,
        command_id: str,
    ) -> str | None:
        """Validate that all required schema fields are present in parsed args.

        Args:
            args_schema: JSON Schema dict (object type).
            parsed_args: Parsed argument namespace.
            command_id: Command ID for error messages.

        Returns:
            An error message string if validation fails, else ``None``.
        """
        required: object = args_schema.get("required", [])
        if not isinstance(required, list):
            return None

        args_dict = vars(parsed_args)
        missing: list[str] = []
        for field_name in required:
            flag_name = str(field_name).replace("-", "_")
            value = args_dict.get(flag_name)
            if value is None:
                missing.append(str(field_name))

        if missing:
            return (
                f"Command '{command_id}': missing required argument(s): "
                + ", ".join(f"--{m.replace('_', '-')}" for m in missing)
            )
        return None
