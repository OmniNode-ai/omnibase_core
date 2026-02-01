"""
Protocol for handler contracts - type-safe handler contract access.

Domain: Handler contract interface for declarative handler specification.

This module defines the main ProtocolHandlerContract interface that aggregates
handler identity, behavior characteristics, capability dependencies, and
execution constraints into a single, type-safe contract specification.

Handler contracts serve as the source of truth for:
    - Handler identification (id, name, version)
    - Behavior specification (idempotency, side effects, retry safety)
    - Capability requirements (what the handler needs to run)
    - Execution constraints (timeouts, retries, resource limits)

The contract supports YAML serialization for declarative handler definitions
and validation for ensuring contract correctness before handler registration.

See Also:
    - protocol_handler_behavior_descriptor.py: Behavior characteristics
    - protocol_capability_dependency.py: Capability requirements
    - protocol_execution_constraints.py: Runtime constraints
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, Self, runtime_checkable

if TYPE_CHECKING:
    from omnibase_core.models.primitives.model_semver import ModelSemVer
    from omnibase_core.protocols.handler.contracts.protocol_capability_dependency import (
        ProtocolCapabilityDependency,
    )
    from omnibase_core.protocols.handler.contracts.protocol_execution_constraints import (
        ProtocolExecutionConstraints,
    )
    from omnibase_core.protocols.handler.contracts.protocol_handler_behavior_descriptor import (
        ProtocolHandlerBehaviorDescriptor,
    )
    from omnibase_core.protocols.validation import ProtocolValidationResult


@runtime_checkable
class ProtocolHandlerContract(Protocol):
    """
    Interface for handler contracts - can be mocked by dependent tickets.

    A handler contract defines the complete specification for a handler,
    including its identity, behavior characteristics, capability dependencies,
    and execution constraints. This protocol enables type-safe access to
    handler contract information and supports YAML serialization.

    The contract serves as the source of truth for:
        - Handler identification (id, name, version)
        - Behavior specification (idempotency, side effects, retry safety)
        - Capability requirements (what the handler needs to run)
        - Execution constraints (timeouts, retries, resource limits)

    This protocol is useful for:
        - Handler registration validation
        - Runtime capability checking
        - Contract-driven handler discovery
        - Declarative handler configuration via YAML
        - Handler metadata introspection

    Attributes:
        handler_id: Unique identifier for this handler.
        handler_name: Human-readable name for this handler.
        contract_version: Semantic version of this handler contract (ModelSemVer).
        descriptor: Behavior descriptor for this handler.
        capability_inputs: List of capability dependencies required by this handler.
        execution_constraints: Execution constraints for this handler.

    Example:
        ```python
        # Load a handler contract from YAML
        contract = ProtocolHandlerContract.from_yaml(yaml_content)

        # Access contract properties
        print(f"Handler: {contract.handler_name} v{contract.contract_version}")
        print(f"Idempotent: {contract.descriptor.idempotent}")

        # Check capability requirements
        for cap in contract.capability_inputs:
            if cap.required:
                print(f"Requires: {cap.capability_name}")

        # Validate the contract
        result = await contract.validate()
        if not result.is_valid:
            for error in result.errors:
                print(f"Error: {error.message}")

        # Serialize back to YAML
        yaml_output = contract.to_yaml()
        ```

    Note:
        This protocol is intended to be implemented by ModelHandlerContract
        in omnibase_core (OMN-1117). The protocol enables loose coupling
        between components while maintaining type safety.

    Implementation Note (Pydantic Validation):
        Implementations of this protocol (e.g., ModelHandlerContract) should use
        Pydantic validators to enforce semantic constraints on field values:
            - timeout_seconds > 0 (must be positive)
            - max_retries >= 0 (must be non-negative)
            - memory_limit_mb > 0 (must be positive if specified)
            - cpu_limit > 0 (must be positive if specified)
            - concurrency_limit >= 1 (must be at least 1 if specified)
            - contract_version is a valid ModelSemVer instance
        These validations ensure contract correctness at construction time
        rather than deferring to runtime validation.

    See Also:
        ProtocolHandlerBehaviorDescriptor: Behavior characteristics
        ProtocolCapabilityDependency: Capability requirements
        ProtocolExecutionConstraints: Runtime constraints
        ProtocolValidationResult: Validation outcome
    """

    @property
    def handler_id(self) -> str:
        """
        Unique identifier for this handler.

        The handler ID provides a globally unique identifier for this handler
        contract. This ID is used for handler lookup, registration tracking,
        and audit logging.

        ID Format Recommendations:
            - UUID: "550e8400-e29b-41d4-a716-446655440000"
            - URN: "urn:onex:handler:http-rest:v1"
            - Hierarchical: "com.example.handlers.http_rest"

        Important:
            The handler_id MUST be unique across all registered handlers.
            Duplicate IDs will cause registration conflicts.

        Returns:
            A globally unique identifier string (typically UUID or URN).
        """
        ...

    @property
    def handler_name(self) -> str:
        """
        Human-readable name for this handler.

        The handler name provides a descriptive identifier suitable for
        display in logs, monitoring dashboards, and administrative interfaces.
        Unlike handler_id, the name does not need to be globally unique but
        should be descriptive enough to identify the handler's purpose.

        Naming Recommendations:
            - Use lowercase with hyphens: "http-rest-handler"
            - Include handler type: "kafka-consumer-handler"
            - Be descriptive: "user-authentication-handler"

        Returns:
            Handler name suitable for display and logging.
        """
        ...

    @property
    def contract_version(self) -> ModelSemVer:
        """
        Semantic version of this handler contract.

        The version follows semantic versioning (semver) conventions to
        communicate compatibility and changes:
            - MAJOR: Breaking changes to the contract interface
            - MINOR: New features, backward compatible
            - PATCH: Bug fixes, backward compatible

        Version Examples:
            - ModelSemVer(1, 0, 0): Initial stable release
            - ModelSemVer(1, 2, 3): Minor feature additions with patches
            - ModelSemVer(2, 0, 0): Breaking changes from v1

        Important:
            Version changes should be coordinated with the handler
            implementation to ensure contract-implementation compatibility.

        Returns:
            ModelSemVer instance representing the contract version.
        """
        ...

    @property
    def descriptor(self) -> ProtocolHandlerBehaviorDescriptor:
        """
        Behavior descriptor for this handler.

        The behavior descriptor provides semantic information about how
        the handler operates, enabling the runtime to make informed
        decisions about caching, retrying, and scheduling.

        Descriptor Properties:
            - idempotent: Can the operation be safely repeated?
            - deterministic: Will the same input produce the same output?
            - side_effects: What external effects does the handler produce?
            - retry_safe: Can the handler be safely retried on failure?

        Returns:
            Descriptor specifying behavioral characteristics.
        """
        ...

    @property
    def capability_inputs(self) -> list[ProtocolCapabilityDependency]:
        """
        List of capability dependencies required by this handler.

        Capability dependencies declare what external capabilities the
        handler needs to function. The runtime uses this information to:
            - Validate all required capabilities are available before registration
            - Inject capability instances at handler initialization
            - Enable graceful degradation when optional capabilities are missing

        Capability Examples:
            - "database.postgresql": PostgreSQL database connection
            - "cache.redis": Redis cache client
            - "messaging.kafka": Kafka producer/consumer

        Returns:
            List of capability dependencies. May be empty if handler
            has no external capability requirements.
        """
        ...

    @property
    def execution_constraints(self) -> ProtocolExecutionConstraints | None:
        """
        Execution constraints for this handler.

        Execution constraints specify resource limits and operational
        boundaries for handler execution. These constraints enable:
            - Timeout enforcement for bounded execution
            - Retry limits for failure recovery
            - Resource quotas for memory and CPU
            - Concurrency limits for rate limiting

        Constraint Properties:
            - max_retries: Maximum retry attempts
            - timeout_seconds: Execution timeout
            - memory_limit_mb: Memory allocation limit
            - cpu_limit: CPU allocation limit
            - concurrency_limit: Maximum concurrent executions

        Returns:
            Constraints if specified, None for default constraints.
            When None, the runtime should apply sensible defaults.
        """
        ...

    async def validate(self) -> ProtocolValidationResult:
        """
        Validate this contract for correctness.

        Performs validation of the contract structure and values,
        including checking for required fields and valid ranges.

        Validation Checks:
            - Required fields are present and non-empty
            - Version string follows semver format
            - Constraint values are within valid ranges (e.g., timeout > 0)
            - Capability names follow naming conventions
            - No conflicting configuration values

        Usage:
            ```python
            result = await contract.validate()
            if not result.is_valid:
                for error in result.errors:
                    logger.error(f"Contract error: {error.message}")
                raise InvalidContractError(result.errors)
            ```

        Returns:
            Validation result with is_valid status and any errors.

        Raises:
            RuntimeError: If validation cannot be completed due to
                internal errors (e.g., missing validator dependencies).
            TypeError: If contract fields have unexpected types that
                prevent validation from proceeding.
        """
        ...

    def to_yaml(self) -> str:
        """
        Serialize this contract to YAML format.

        Converts the contract to a YAML string representation that can
        be saved to a file or transmitted. The YAML format matches the
        expected input format for from_yaml().

        YAML Structure:
            ```yaml
            handler_id: "uuid-or-urn"
            handler_name: "handler-name"
            contract_version: "1.0.0"
            descriptor:
              idempotent: true
              deterministic: false
              side_effects: ["network", "database"]
              retry_safe: true
            capability_inputs:
              - capability_name: "database.postgresql"
                required: true
                version_constraint: ">=14.0.0"
            execution_constraints:
              max_retries: 3
              timeout_seconds: 30.0
              memory_limit_mb: 512
            ```

        Returns:
            YAML string representation of the contract.
        """
        ...

    @classmethod
    def from_yaml(cls, content: str) -> Self:
        """
        Deserialize a contract from YAML content.

        Parses YAML content and constructs a new contract instance.
        The YAML structure should match the output format of to_yaml().

        Args:
            content: YAML string to parse. Must contain all required fields
                (handler_id, handler_name, contract_version, descriptor).
                Optional fields (capability_inputs, execution_constraints)
                use defaults if not specified.

        Returns:
            New contract instance parsed from YAML.

        Raises:
            ValueError: If YAML is malformed or missing required fields.

        Example:
            ```python
            yaml_content = '''
            handler_id: "http-handler-001"
            handler_name: "http-rest-handler"
            contract_version: "1.0.0"
            descriptor:
              idempotent: true
              deterministic: false
              side_effects: ["network"]
              retry_safe: true
            '''

            contract = ProtocolHandlerContract.from_yaml(yaml_content)
            print(f"Loaded: {contract.handler_name}")
            ```
        """
        ...


def create_handler_contract_from_yaml(  # stub-ok
    content: str,
) -> ProtocolHandlerContract:
    """
    Factory function to create a handler contract from YAML content.

    This is an alternative to ProtocolHandlerContract.from_yaml() that provides
    better type inference in some contexts.

    Args:
        content: YAML string to parse.

    Returns:
        New contract instance parsed from YAML.

    Raises:
        ValueError: If YAML is malformed or missing required fields.
        NotImplementedError: Protocol methods are abstract.
    """
    raise NotImplementedError(  # error-ok: intentional stub for abstract factory
        "Factory function requires a concrete implementation. "
        "Use ModelHandlerContract.from_yaml() when available (OMN-1117)."
    )


__all__ = ["ProtocolHandlerContract"]
