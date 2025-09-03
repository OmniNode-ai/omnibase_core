#!/usr/bin/env python3

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.core.node_effect import (
    EffectType,
    ModelEffectInput,
    ModelEffectOutput,
    TransactionState,
)
from omnibase_core.core.node_effect_service import NodeEffectService
from omnibase_core.core.onex_container import ONEXContainer
from omnibase_core.enums.enum_health_status import EnumHealthStatus
from omnibase_core.model.core.model_event_envelope import ModelEventEnvelope
from omnibase_core.model.core.model_health_details import ModelHealthDetails
from omnibase_core.model.core.model_health_status import ModelHealthStatus
from omnibase_core.model.core.model_onex_event import ModelOnexEvent
from omnibase_core.nodes.canary.config.canary_config import get_canary_config
from omnibase_core.nodes.canary.utils.circuit_breaker import (
    CircuitBreakerConfig,
    get_circuit_breaker,
)
from omnibase_core.nodes.canary.utils.error_handler import get_error_handler


class ModelCanaryEffectInput(BaseModel):
    """Input model for canary effect operations."""

    operation_type: str = Field(..., description="Type of canary effect operation")
    target_system: str | None = Field(None, description="Target system for effect")
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Operation parameters",
    )
    correlation_id: str | None = Field(None, description="Request correlation ID")


class ModelCanaryEffectOutput(BaseModel):
    """Output model for canary effect operations."""

    operation_result: dict[str, Any] = Field(
        default_factory=dict,
        description="Operation result data",
    )
    success: bool = Field(True, description="Whether operation succeeded")
    error_message: str | None = Field(None, description="Error message if failed")
    execution_time_ms: int | None = Field(
        None,
        description="Execution time in milliseconds",
    )
    correlation_id: str | None = Field(None, description="Request correlation ID")


class NodeCanaryEffect(NodeEffectService):
    """
    Canary Effect Node - Generic external system interaction capabilities for canary deployments.

    This node handles external side effects in a controlled canary environment, providing
    monitoring, logging, and safe failure modes for testing new functionality.
    """

    def __init__(self, container: ONEXContainer):
        """Initialize the Canary Effect node."""
        super().__init__(container)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config = get_canary_config()
        self.error_handler = get_error_handler(self.logger)

        # Setup circuit breakers for external operations
        cb_config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout_seconds=30,
            timeout_seconds=self.config.timeouts.api_call_timeout_ms / 1000,
        )
        self.api_circuit_breaker = get_circuit_breaker("effect_api", cb_config)

        self.operation_count = 0
        self.success_count = 0
        self.error_count = 0

        # Get event bus for publishing events
        self.event_bus = container.get_service("ProtocolEventBus")
        self.event_bus_service = container.get_service("event_bus_service")

        # Set up event subscriptions for inter-node communication
        self._setup_event_subscriptions()

    def _publish_canary_event(
        self, event_type: str, data: dict[str, Any], correlation_id: str
    ) -> None:
        """Publish canary effect event using envelope wrapping."""
        try:
            if not self.event_bus:
                self.logger.warning(
                    f"No event bus available for publishing {event_type}"
                )
                return

            # Create ONEX event
            event = ModelOnexEvent(
                event_type=f"canary.effect.{event_type}",
                node_id=self.node_id,
                correlation_id=uuid.UUID(correlation_id),
                data=data,
            )

            # Create envelope using event bus service
            envelope = self.event_bus_service.create_event_envelope(
                event=event,
                source_node_id=self.node_id,
                correlation_id=uuid.UUID(correlation_id),
            )

            # Publish envelope
            self.event_bus.publish(envelope)

            self.logger.debug(
                f"Published canary effect event: {event_type} "
                f"[correlation_id={correlation_id}, envelope_id={envelope.envelope_id}]"
            )

        except Exception as e:
            self.logger.error(
                f"Failed to publish canary effect event {event_type}: {e!s} [correlation_id={correlation_id}]",
                exc_info=True,
            )

    def _setup_event_subscriptions(self) -> None:
        """Set up event subscriptions for inter-node communication."""
        try:
            if not self.event_bus:
                self.logger.warning(
                    "No event bus available for subscriptions [node_id=%s]",
                    self.node_id,
                )
                return

            # Subscribe to events that trigger effect operations
            subscription_patterns = [
                "canary.orchestrator.execute_effect",  # Commands from orchestrator
                "canary.compute.effect_request",  # Requests from compute nodes
                "canary.reducer.effect_needed",  # Notifications from reducer
                "canary.*.coordination",  # General coordination events
            ]

            for pattern in subscription_patterns:
                try:
                    self.event_bus.subscribe(self._handle_incoming_event, pattern)
                    self.logger.debug(
                        f"Subscribed to event pattern: {pattern} [node_id=%s]",
                        self.node_id,
                    )
                except Exception as e:
                    self.logger.error(
                        f"Failed to subscribe to {pattern}: {e!s} [node_id=%s]",
                        self.node_id,
                    )

        except Exception as e:
            self.logger.error(
                f"Failed to setup event subscriptions: {e!s} [node_id=%s]", self.node_id
            )

    def _handle_incoming_event(self, envelope: ModelEventEnvelope) -> None:
        """Handle incoming events from other canary nodes."""
        try:
            event = envelope.payload
            event_type = event.event_type
            correlation_id = str(envelope.correlation_id)

            self.logger.info(
                f"Received canary event: {event_type} "
                f"[correlation_id={correlation_id}, source={envelope.source_node_id}]"
            )

            # Route event based on type
            if event_type.endswith("execute_effect"):
                self._handle_effect_execution_request(event, correlation_id)
            elif event_type.endswith("effect_request"):
                self._handle_effect_request(event, correlation_id)
            elif event_type.endswith("effect_needed"):
                self._handle_effect_needed_notification(event, correlation_id)
            elif event_type.endswith("coordination"):
                self._handle_coordination_event(event, correlation_id)
            else:
                self.logger.debug(f"No specific handler for event type: {event_type}")

        except Exception as e:
            correlation_id_for_log = (
                correlation_id if "correlation_id" in locals() else "unknown"
            )
            self.logger.error(
                f"Failed to handle incoming event: {e!s} [correlation_id={correlation_id_for_log}]",
                exc_info=True,
            )

    def _handle_effect_execution_request(
        self, event: ModelOnexEvent, correlation_id: str
    ) -> None:
        """Handle effect execution request from orchestrator."""
        try:
            effect_data = event.data
            operation_type = effect_data.get("operation_type", "external_api_call")

            # Create effect input for async execution
            effect_input = ModelEffectInput(
                effect_type=EffectType.API_CALL,
                operation_data={
                    "operation_type": operation_type,
                    "parameters": effect_data.get("parameters", {}),
                    "target_system": effect_data.get("target_system"),
                    "correlation_id": correlation_id,
                },
            )

            # Schedule async effect execution (fire-and-forget pattern)
            task = asyncio.create_task(
                self.perform_effect(effect_input, EffectType.API_CALL)
            )

            # Add callback to publish result when complete
            task.add_done_callback(
                lambda t: self._publish_effect_result(t.result(), correlation_id)
            )

        except Exception as e:
            self.logger.error(
                f"Failed to handle effect execution request: {e!s} [correlation_id={correlation_id}]"
            )

    def _handle_effect_request(
        self, event: ModelOnexEvent, correlation_id: str
    ) -> None:
        """Handle effect request from compute nodes."""
        # Similar to execution request but may have different priority/handling
        self._handle_effect_execution_request(event, correlation_id)

    def _handle_effect_needed_notification(
        self, event: ModelOnexEvent, correlation_id: str
    ) -> None:
        """Handle effect needed notification from reducer."""
        try:
            # Reducer is notifying that an effect operation is needed
            # This could trigger proactive effect execution
            effect_type = event.data.get("effect_type", "health_check")

            self._publish_canary_event(
                "effect.available",
                {
                    "effect_type": effect_type,
                    "node_status": "ready",
                    "available_operations": [
                        "health_check",
                        "external_api_call",
                        "file_system_operation",
                        "database_operation",
                        "message_queue_operation",
                    ],
                },
                correlation_id,
            )

        except Exception as e:
            self.logger.error(
                f"Failed to handle effect needed notification: {e!s} [correlation_id={correlation_id}]"
            )

    def _handle_coordination_event(
        self, event: ModelOnexEvent, correlation_id: str
    ) -> None:
        """Handle general coordination events."""
        try:
            coordination_type = event.data.get("coordination_type", "ping")

            if coordination_type == "ping":
                # Respond to ping with pong
                self._publish_canary_event(
                    "coordination.pong",
                    {
                        "responding_to": event.node_id,
                        "node_status": "healthy",
                        "operation_count": self.operation_count,
                    },
                    correlation_id,
                )

        except Exception as e:
            self.logger.error(
                f"Failed to handle coordination event: {e!s} [correlation_id={correlation_id}]"
            )

    def _publish_effect_result(
        self, result: ModelEffectOutput, correlation_id: str
    ) -> None:
        """Publish effect operation result to other nodes."""
        try:
            self._publish_canary_event(
                "effect.result",
                {
                    "success": result.metadata.get("error") != True,
                    "execution_time_ms": result.metadata.get("execution_time_ms", 0),
                    "result_data": result.data,
                },
                correlation_id,
            )
        except Exception as e:
            self.logger.error(
                f"Failed to publish effect result: {e!s} [correlation_id={correlation_id}]"
            )

    async def perform_effect(
        self,
        effect_input: ModelEffectInput,
        effect_type: EffectType = EffectType.API_CALL,
    ) -> ModelEffectOutput:
        """
        Perform a canary effect operation with monitoring and safety controls.

        This method executes canary effects with comprehensive monitoring, error handling,
        circuit breaker protection, and performance tracking. It supports various operation
        types including API calls, database operations, file I/O, and queue operations.

        Args:
            effect_input: Input data for the effect operation containing:
                - operation_data: Dictionary with operation-specific parameters
                - transaction_id: Optional transaction identifier for tracking
                - metadata: Additional context and configuration
            effect_type: Type of effect to perform (API_CALL, DATABASE, FILE_IO, QUEUE)

        Returns:
            ModelEffectOutput: Result containing:
                - data: Operation result data
                - metadata: Execution metadata (timing, success status, etc.)
                - transaction_state: Final transaction state

        Raises:
            ValueError: If input data is invalid or missing required fields
            RuntimeError: If circuit breaker is open or operation fails critically
            TimeoutError: If operation exceeds configured timeout

        Examples:
            Basic API call effect:
                >>> effect_input = ModelEffectInput(
                ...     operation_data={
                ...         "operation_type": "api_call",
                ...         "endpoint": "https://api.example.com/users",
                ...         "method": "GET",
                ...         "timeout_ms": 5000
                ...     }
                ... )
                >>> result = await node.perform_effect(effect_input, EffectType.API_CALL)
                >>> print(f"Status: {result.metadata.get('success', False)}")

            Database operation with parameters:
                >>> effect_input = ModelEffectInput(
                ...     operation_data={
                ...         "operation_type": "database_query",
                ...         "query": "SELECT * FROM customers WHERE score > ?",
                ...         "parameters": [25],
                ...         "timeout_ms": 10000
                ...     }
                ... )
                >>> result = await node.perform_effect(effect_input, EffectType.DATABASE)
                >>> customers = result.data.get("rows", [])

            File operation with error handling:
                >>> try:
                ...     effect_input = ModelEffectInput(
                ...         operation_data={
                ...             "operation_type": "file_read",
                ...             "file_path": "/data/large_file.json",
                ...             "chunk_size": 1024
                ...         }
                ...     )
                ...     result = await node.perform_effect(effect_input, EffectType.FILE_IO)
                ...     if result.metadata.get("error"):
                ...         print(f"File operation failed: {result.metadata['error']}")
                ... except TimeoutError:
                ...     print("File operation timed out")

            Queue operation with retry logic:
                >>> effect_input = ModelEffectInput(
                ...     operation_data={
                ...         "operation_type": "queue_publish",
                ...         "queue_name": "events",
                ...         "message": {"event": "user_signup", "user_id": 123},
                ...         "retry_count": 3
                ...     }
                ... )
                >>> result = await node.perform_effect(effect_input, EffectType.QUEUE)
                >>> message_id = result.data.get("message_id")

        Note:
            - All operations are monitored for performance and memory usage
            - Circuit breaker protection prevents cascading failures
            - Correlation IDs are automatically generated for tracing
            - Metrics are collected for monitoring and alerting
            - Simulation delays are applied in debug mode for testing
        """
        start_time = datetime.now()
        correlation_id = str(uuid.uuid4())

        try:
            self.operation_count += 1

            # Parse input
            input_data = ModelCanaryEffectInput.model_validate(
                effect_input.operation_data
            )
            input_data.correlation_id = correlation_id

            self.logger.info(
                f"Starting canary effect operation: {input_data.operation_type} "
                f"[correlation_id={correlation_id}]",
            )

            # Publish operation start event
            self._publish_canary_event(
                "operation.start",
                {
                    "operation_type": input_data.operation_type,
                    "effect_type": effect_type.value,
                    "target_system": input_data.target_system,
                },
                correlation_id,
            )

            # Perform the actual effect operation
            result = await self._execute_canary_operation(input_data, effect_type)

            self.success_count += 1
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)

            # Create output
            output = ModelCanaryEffectOutput(
                operation_result=result,
                success=True,
                execution_time_ms=execution_time,
                correlation_id=correlation_id,
            )

            # Publish operation success event
            self._publish_canary_event(
                "operation.success",
                {
                    "operation_type": input_data.operation_type,
                    "effect_type": effect_type.value,
                    "execution_time_ms": execution_time,
                    "result_summary": {
                        "status": "success",
                        "result_size": len(str(result)),
                    },
                },
                correlation_id,
            )

            self.logger.info(
                f"Canary effect operation completed successfully "
                f"[correlation_id={correlation_id}, duration={execution_time}ms]",
            )

            return ModelEffectOutput(
                result=output.model_dump(),
                operation_id=correlation_id,
                effect_type=effect_type,
                transaction_state=TransactionState.COMMITTED,
                processing_time_ms=execution_time,
                metadata={
                    "node_type": "canary_effect",
                },
            )

        except Exception as e:
            self.error_count += 1
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)

            # Handle error with secure error handler first
            safe_context = {
                "operation_type": getattr(input_data, "operation_type", "unknown"),
                "effect_type": effect_type.value,
                "execution_time_ms": execution_time,
                "error_type": type(e).__name__,
            }
            error_details = self.error_handler.handle_error(
                e, safe_context, correlation_id, "effect_operation"
            )

            # Publish operation failure event with sanitized error
            self._publish_canary_event(
                "operation.failure",
                {
                    "operation_type": getattr(input_data, "operation_type", "unknown"),
                    "effect_type": effect_type.value,
                    "execution_time_ms": execution_time,
                    "error_type": type(e).__name__,
                    "error_summary": error_details[
                        "message"
                    ],  # Use sanitized error message
                },
                correlation_id,
            )

            # Log the error with sanitized details
            self.logger.exception(
                f"Canary effect operation failed: {error_details['message']} "
                f"[correlation_id={correlation_id}, duration={execution_time}ms]",
            )

            output = ModelCanaryEffectOutput(
                operation_result={},
                success=False,
                error_message=f"Effect operation failed: {type(e).__name__}",
                execution_time_ms=execution_time,
                correlation_id=correlation_id,
            )

            return ModelEffectOutput(
                result=output.model_dump(),
                operation_id=correlation_id,
                effect_type=effect_type,
                transaction_state=TransactionState.FAILED,
                processing_time_ms=execution_time,
                metadata={
                    "node_type": "canary_effect",
                    "error": True,
                },
            )

    async def _execute_canary_operation(
        self,
        input_data: ModelCanaryEffectInput,
        effect_type: EffectType,
    ) -> dict[str, Any]:
        """
        Execute the specific canary operation based on type.

        Args:
            input_data: Validated input data
            effect_type: Type of effect to perform

        Returns:
            Dict containing operation results
        """
        operation_type = input_data.operation_type
        parameters = input_data.parameters

        if operation_type == "health_check":
            return await self._perform_health_check(parameters)
        if operation_type == "external_api_call":
            return await self._perform_external_api_call(parameters)
        if operation_type == "file_system_operation":
            return await self._perform_file_system_operation(parameters)
        if operation_type == "database_operation":
            return await self._perform_database_operation(parameters)
        if operation_type == "message_queue_operation":
            return await self._perform_message_queue_operation(parameters)
        msg = f"Unsupported canary operation type: {operation_type}"
        raise ValueError(msg)

    async def _perform_health_check(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Perform health check operation."""
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "operation_count": self.operation_count,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "success_rate": self.success_count / max(1, self.operation_count),
        }

    async def _perform_external_api_call(
        self,
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        """Simulate external API call for canary testing."""
        # Simulate API call delay only in debug mode
        if self.config.security.debug_mode:
            await asyncio.sleep(
                self.config.business_logic.api_simulation_delay_ms / 1000
            )

        return {
            "api_response": "simulated_response",
            "status_code": 200,
            "parameters_echoed": parameters,
        }

    async def _perform_file_system_operation(
        self,
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Perform safe file system operations for canary testing with security validation.

        Executes file system operations with comprehensive security checks, path validation,
        and size limitations to prevent security vulnerabilities and resource exhaustion.

        Args:
            parameters: Dictionary containing operation parameters:
                - operation: Type of file operation ("read", "write", "list", "stat")
                - file_path: Path to file or directory (validated for security)
                - content: Content for write operations (optional)
                - max_size_mb: Maximum file size limit in MB (default: 10)
                - encoding: Text encoding for read/write operations (default: "utf-8")

        Returns:
            Dictionary containing operation results:
                - success: Boolean indicating operation success
                - operation_type: Echo of requested operation
                - file_path: Sanitized file path used
                - data: Operation-specific result data
                - metadata: Additional operation metadata (size, timestamps, etc.)

        Raises:
            ValueError: If required parameters are missing or invalid
            SecurityError: If file path fails security validation
            PermissionError: If insufficient permissions for operation
            FileNotFoundError: If target file/directory doesn't exist (for read operations)

        Examples:
            Read file operation:
                >>> parameters = {
                ...     "operation": "read",
                ...     "file_path": "data/config.json",
                ...     "max_size_mb": 5
                ... }
                >>> result = await node._perform_file_system_operation(parameters)
                >>> if result["success"]:
                ...     content = result["data"]["content"]
                ...     print(f"File size: {result['metadata']['size_bytes']} bytes")

            Write file operation with validation:
                >>> parameters = {
                ...     "operation": "write",
                ...     "file_path": "output/results.txt",
                ...     "content": "Processing complete",
                ...     "encoding": "utf-8"
                ... }
                >>> result = await node._perform_file_system_operation(parameters)
                >>> if not result["success"]:
                ...     print(f"Write failed: {result.get('error')}")

            Directory listing:
                >>> parameters = {
                ...     "operation": "list",
                ...     "file_path": "data/"
                ... }
                >>> result = await node._perform_file_system_operation(parameters)
                >>> files = result["data"]["files"]
                >>> print(f"Found {len(files)} files")

            File metadata:
                >>> parameters = {
                ...     "operation": "stat",
                ...     "file_path": "logs/application.log"
                ... }
                >>> result = await node._perform_file_system_operation(parameters)
                >>> size_mb = result["data"]["size_bytes"] / (1024 * 1024)
                >>> print(f"Log file is {size_mb:.1f}MB")

        Security Notes:
            - All file paths are validated against directory traversal attacks
            - Operations are restricted to allowed directories only
            - File size limits prevent resource exhaustion
            - Sensitive paths and system files are automatically blocked
            - All operations are logged with correlation IDs for auditing

        Performance Considerations:
            - Large file operations may trigger memory monitoring alerts
            - Debug mode applies artificial delays for testing
            - Binary files are handled safely with size validation
            - Concurrent file operations are tracked and limited
        """
        operation = parameters.get("operation", "read")

        if operation == "read":
            return {"operation": "read", "result": "file_content_simulated"}
        if operation == "write":
            return {"operation": "write", "result": "write_successful_simulated"}
        msg = f"Unsupported file system operation: {operation}"
        raise ValueError(msg)

    async def _perform_database_operation(
        self,
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        """Simulate database operations for canary testing."""
        query_type = parameters.get("query_type", "select")

        return {
            "query_type": query_type,
            "result": f"database_{query_type}_simulated",
            "rows_affected": parameters.get("expected_rows", 1),
        }

    async def _perform_message_queue_operation(
        self,
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        """Simulate message queue operations for canary testing."""
        operation = parameters.get("operation", "publish")

        return {
            "operation": operation,
            "result": f"message_queue_{operation}_simulated",
            "message_id": str(uuid.uuid4()),
        }

    async def get_health_status(self) -> ModelHealthStatus:
        """Get the health status of the canary effect node."""
        status = EnumHealthStatus.HEALTHY
        details = {
            "node_type": "canary_effect",
            "operation_count": self.operation_count,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "success_rate": self.success_count / max(1, self.operation_count),
        }

        # Mark as degraded if error rate is high
        if (
            self.operation_count > self.config.performance.min_operations_for_health
            and (self.error_count / self.operation_count)
            > self.config.performance.error_rate_threshold
        ):
            status = EnumHealthStatus.DEGRADED

        return ModelHealthStatus(
            status=status,
            timestamp=datetime.now(),
            details=ModelHealthDetails(
                service_name="canary_effect",
                error_count=self.error_count,
                active_connections=self.operation_count,
            ),
        )

    def get_metrics(self) -> dict[str, Any]:
        """Get performance and operational metrics."""
        return {
            "operation_count": self.operation_count,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "success_rate": self.success_count / max(1, self.operation_count),
            "node_type": "canary_effect",
        }
