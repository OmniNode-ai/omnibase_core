# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Handler Descriptor Model.

This module provides the **canonical runtime representation** of a handler descriptor
in the ONEX framework. Handler descriptors contain all metadata necessary for handler
discovery, instantiation, routing, and lifecycle management.

Key Concepts
------------

**Descriptor vs Contract**:
    - **Contracts** are the serialization format (YAML/JSON) stored on disk or in registries
    - **Descriptors** are the runtime representation produced by parsing contracts
    - Contracts are transformed into descriptors at load time via registry resolution

**Classification Axes** (all three must be specified):
    - **handler_role** (EnumHandlerRole): Architectural responsibility
      (INFRA_HANDLER, NODE_HANDLER, PROJECTION_HANDLER, COMPUTE_HANDLER)
    - **handler_type** (EnumHandlerType): Transport/integration kind
      (HTTP, DATABASE, KAFKA, FILESYSTEM, etc.)
    - **handler_type_category** (EnumHandlerTypeCategory): Behavioral classification
      (COMPUTE, EFFECT, NONDETERMINISTIC_COMPUTE)

**Adapter Policy Tag** (is_adapter):
    ADAPTER is a **policy tag**, NOT a category. This distinction is critical:

    - **Behaviorally**: Adapters ARE EFFECT handlers (they do I/O)
    - **Policy-wise**: ``is_adapter=True`` triggers stricter defaults:
        - No secrets access by default
        - Narrow permissions scope
        - Platform plumbing focus

    **Use is_adapter=True for**:
        - Kafka ingress/egress adapters
        - HTTP gateway adapters
        - Webhook receivers
        - CLI bridge adapters

    **Do NOT use is_adapter=True for**:
        - Database handlers (DATABASE type, EFFECT category)
        - Vault handlers (VAULT type, EFFECT category)
        - Consul handlers (SERVICE_DISCOVERY type, EFFECT category)
        - Outbound HTTP client handlers (HTTP type, EFFECT category)

    **Validation Constraint**: If ``is_adapter=True``, then ``handler_type_category``
    MUST be ``EFFECT``. This is enforced via model validation.

Location:
    ``omnibase_core.models.handlers.model_handler_descriptor.ModelHandlerDescriptor``

Import Example:
    .. code-block:: python

        from omnibase_core.models.handlers import ModelHandlerDescriptor
        from omnibase_core.enums import (
            EnumHandlerRole,
            EnumHandlerType,
            EnumHandlerTypeCategory,
            EnumHandlerCapability,
        )
        from omnibase_core.models.primitives.model_semver import ModelSemVer
        from omnibase_core.models.handlers import ModelIdentifier

        # Example: Kafka ingress adapter
        kafka_adapter = ModelHandlerDescriptor(
            handler_name=ModelIdentifier(namespace="onex", name="kafka-ingress"),
            handler_version=ModelSemVer(major=1, minor=0, patch=0),
            handler_role=EnumHandlerRole.INFRA_HANDLER,
            handler_type=EnumHandlerType.KAFKA,
            handler_type_category=EnumHandlerTypeCategory.EFFECT,
            is_adapter=True,  # Platform plumbing - stricter defaults
            capabilities=[EnumHandlerCapability.STREAM, EnumHandlerCapability.ASYNC],
            import_path="omnibase_infra.adapters.kafka_ingress.KafkaIngressAdapter",
        )

        # Example: Database handler (NOT an adapter)
        db_handler = ModelHandlerDescriptor(
            handler_name=ModelIdentifier(namespace="onex", name="postgres-handler"),
            handler_version=ModelSemVer(major=2, minor=1, patch=0),
            handler_role=EnumHandlerRole.INFRA_HANDLER,
            handler_type=EnumHandlerType.DATABASE,
            handler_type_category=EnumHandlerTypeCategory.EFFECT,
            is_adapter=False,  # Full handler - needs secrets, broader permissions
            capabilities=[
                EnumHandlerCapability.RETRY,
                EnumHandlerCapability.IDEMPOTENT,
            ],
            import_path="omnibase_infra.handlers.postgres_handler.PostgresHandler",
        )

        # Example: Pure compute handler
        validator = ModelHandlerDescriptor(
            handler_name=ModelIdentifier(namespace="onex", name="schema-validator"),
            handler_version=ModelSemVer(major=1, minor=0, patch=0),
            handler_role=EnumHandlerRole.COMPUTE_HANDLER,
            handler_type=EnumHandlerType.NAMED,
            handler_type_category=EnumHandlerTypeCategory.COMPUTE,
            capabilities=[
                EnumHandlerCapability.VALIDATE,
                EnumHandlerCapability.CACHE,
            ],
            import_path="omnibase_core.handlers.schema_validator.SchemaValidator",
        )

Thread Safety:
    ModelHandlerDescriptor is immutable (frozen=True) after creation,
    making it thread-safe for concurrent read access from multiple threads
    or async tasks.

See Also:
    - :class:`~omnibase_core.enums.enum_handler_role.EnumHandlerRole`:
      Architectural role classification
    - :class:`~omnibase_core.enums.enum_handler_type.EnumHandlerType`:
      Transport/integration type classification
    - :class:`~omnibase_core.enums.enum_handler_type_category.EnumHandlerTypeCategory`:
      Behavioral classification (COMPUTE, EFFECT, NONDETERMINISTIC_COMPUTE)
    - :class:`~omnibase_core.models.handlers.model_identifier.ModelIdentifier`:
      Structured handler identifier
    - :class:`~omnibase_core.models.handlers.model_artifact_ref.ModelArtifactRef`:
      Artifact reference for container/registry-based instantiation

.. versionadded:: 0.4.0
    Initial implementation as part of OMN-1086 handler descriptor model.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_handler_capability import EnumHandlerCapability
from omnibase_core.enums.enum_handler_command_type import EnumHandlerCommandType
from omnibase_core.enums.enum_handler_role import EnumHandlerRole
from omnibase_core.enums.enum_handler_type import EnumHandlerType
from omnibase_core.enums.enum_handler_type_category import EnumHandlerTypeCategory
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.handlers.model_artifact_ref import ModelArtifactRef
from omnibase_core.models.handlers.model_identifier import ModelIdentifier
from omnibase_core.models.handlers.model_packaging_metadata_ref import (
    ModelPackagingMetadataRef,
)
from omnibase_core.models.handlers.model_security_metadata_ref import (
    ModelSecurityMetadataRef,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelHandlerDescriptor(BaseModel):
    """
    Canonical runtime representation of a handler descriptor.

    This model is the **authoritative runtime representation** of a handler in the
    ONEX framework. Contracts (YAML/JSON configuration files) are transformed into
    descriptors at load time, and descriptors are used for all runtime operations
    including discovery, routing, instantiation, and lifecycle management.

    A handler descriptor contains:
        - **Identity**: Name and version for registry lookup
        - **Classification**: Role, type, and category for routing
        - **Policy Tags**: Flags like ``is_adapter`` that affect defaults
        - **Surface**: Capabilities and accepted commands
        - **Instantiation**: Import path or artifact reference for loading
        - **Metadata References**: Security and packaging configuration

    Classification Axes
    -------------------
    Every handler must specify all three classification dimensions:

    1. **handler_role** - Architectural responsibility (what the handler does)
    2. **handler_type** - Transport/integration (how the handler connects)
    3. **handler_type_category** - Behavioral classification (pure vs impure)

    Adapter Policy Tag
    ------------------
    The ``is_adapter`` flag is a **policy tag**, not a separate category.

    When ``is_adapter=True``:
        - Handler is platform plumbing (ingress/egress, bridge, gateway)
        - Stricter defaults apply (no secrets, narrow permissions)
        - ``handler_type_category`` MUST be ``EFFECT`` (enforced by validation)

    When ``is_adapter=False`` (default):
        - Handler is a full-featured service handler
        - Normal permissions apply (may access secrets if authorized)
        - Any ``handler_type_category`` is valid

    Capability Patterns
    -------------------
    The ``capabilities`` field enables capability-based routing and runtime optimization.
    Common capability combinations and their implications:

    **Stateless Compute Handlers** (pure transformations)::

        capabilities=[CACHE, IDEMPOTENT, VALIDATE]

        - CACHE: Results can be memoized based on input hash
        - IDEMPOTENT: Safe to retry without side effects
        - VALIDATE: Can validate inputs before processing

    **Streaming/Event Handlers** (high-throughput)::

        capabilities=[STREAM, ASYNC, BATCH]

        - STREAM: Supports streaming input/output
        - ASYNC: Non-blocking execution model
        - BATCH: Can process multiple items efficiently

    **Resilient I/O Handlers** (external system integration)::

        capabilities=[RETRY, CIRCUIT_BREAKER, TIMEOUT]

        - RETRY: Automatic retry with backoff
        - CIRCUIT_BREAKER: Fail-fast when downstream is unhealthy
        - TIMEOUT: Enforces maximum execution time

    **Capability-Based Routing Example**::

        # Find handlers with ALL required capabilities
        required = {EnumHandlerCapability.CACHE, EnumHandlerCapability.IDEMPOTENT}
        matching = [
            h for h in registry
            if required.issubset(set(h.capabilities))
        ]

        # Find handlers with ANY of the desired capabilities
        desired = {EnumHandlerCapability.STREAM, EnumHandlerCapability.BATCH}
        matching = [
            h for h in registry
            if desired.intersection(set(h.capabilities))
        ]

    Attributes:
        handler_name: Structured identifier following the namespace:name pattern.
            Used as the primary key for registry lookup.
        handler_version: Semantic version of the handler implementation.
            Used for compatibility checks and version-pinned instantiation.
        handler_role: Architectural role classification. Determines routing
            semantics, DI services available, and lifecycle management.
        handler_type: Transport/integration type. Identifies the external
            system or protocol the handler interacts with.
        handler_type_category: Behavioral classification. Determines caching,
            retry, and parallelization strategies.
        is_adapter: Policy tag for platform plumbing handlers. When True,
            triggers stricter defaults and requires handler_type_category=EFFECT.
        capabilities: List of capabilities the handler supports (caching,
            retry, streaming, etc.). Used for capability-based routing.
        commands_accepted: List of command types the handler responds to
            (EXECUTE, VALIDATE, DRY_RUN, etc.).
        import_path: Python import path for direct instantiation
            (e.g., "mypackage.handlers.MyHandler").
        artifact_ref: Artifact reference for registry-resolved instantiation.
            Used for containerized or external artifacts.
        security_metadata_ref: Reference to security configuration (allowed
            domains, secret scopes, classification level).
        packaging_metadata_ref: Reference to packaging configuration (dependencies,
            entry points, distribution metadata).

    Example:
        >>> # Kafka adapter (is_adapter=True)
        >>> from omnibase_core.models.handlers import ModelHandlerDescriptor, ModelIdentifier
        >>> from omnibase_core.enums import (
        ...     EnumHandlerRole, EnumHandlerType, EnumHandlerTypeCategory
        ... )
        >>> from omnibase_core.models.primitives.model_semver import ModelSemVer
        >>> adapter = ModelHandlerDescriptor(
        ...     handler_name=ModelIdentifier(namespace="onex", name="kafka-adapter"),
        ...     handler_version=ModelSemVer(major=1, minor=0, patch=0),
        ...     handler_role=EnumHandlerRole.INFRA_HANDLER,
        ...     handler_type=EnumHandlerType.KAFKA,
        ...     handler_type_category=EnumHandlerTypeCategory.EFFECT,
        ...     is_adapter=True,
        ...     import_path="mypackage.adapters.KafkaAdapter",
        ... )
        >>> adapter.is_adapter
        True

        >>> # Compute handler (NOT an adapter)
        >>> compute = ModelHandlerDescriptor(
        ...     handler_name=ModelIdentifier(namespace="onex", name="validator"),
        ...     handler_version=ModelSemVer(major=1, minor=0, patch=0),
        ...     handler_role=EnumHandlerRole.COMPUTE_HANDLER,
        ...     handler_type=EnumHandlerType.NAMED,
        ...     handler_type_category=EnumHandlerTypeCategory.COMPUTE,
        ...     import_path="mypackage.handlers.Validator",
        ... )
        >>> compute.is_adapter
        False

    Raises:
        ModelOnexError: If ``is_adapter=True`` but ``handler_type_category``
            is not ``EFFECT``. Adapters must be EFFECT handlers because they
            perform I/O by definition.

    Thread Safety:
        This model is immutable (frozen=True) and safe for concurrent access.

    .. versionadded:: 0.4.0
    """

    # from_attributes=True allows Pydantic to accept objects with matching
    # attributes even when class identity differs (e.g., in pytest-xdist
    # parallel execution where model classes are imported in separate workers)
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    # =========================================================================
    # Identity
    # =========================================================================

    handler_name: ModelIdentifier = Field(
        ...,
        description=(
            "Structured identifier for the handler following the namespace:name "
            "pattern. Used as the primary key for registry lookup and discovery."
        ),
    )

    handler_version: ModelSemVer = Field(
        ...,
        description=(
            "Semantic version of the handler implementation. Used for "
            "compatibility checks and version-pinned instantiation."
        ),
    )

    # =========================================================================
    # Classification (all three axes MUST be specified)
    # =========================================================================

    handler_role: EnumHandlerRole = Field(
        ...,
        description=(
            "Architectural role of the handler. Determines routing semantics, "
            "available DI services, and lifecycle management. "
            "Values: INFRA_HANDLER, NODE_HANDLER, PROJECTION_HANDLER, COMPUTE_HANDLER."
        ),
    )

    handler_type: EnumHandlerType = Field(
        ...,
        description=(
            "Transport/integration type. Identifies the external system or "
            "protocol the handler interacts with. "
            "Values: HTTP, DATABASE, KAFKA, FILESYSTEM, VAULT, etc."
        ),
    )

    handler_type_category: EnumHandlerTypeCategory = Field(
        ...,
        description=(
            "Behavioral classification of the handler. Determines caching, "
            "retry, and parallelization strategies. "
            "Values: COMPUTE (pure/deterministic), EFFECT (I/O), "
            "NONDETERMINISTIC_COMPUTE (pure but non-deterministic)."
        ),
    )

    # =========================================================================
    # Policy Tags
    # =========================================================================

    is_adapter: bool = Field(
        default=False,
        description=(
            "Policy tag for platform plumbing handlers. When True, indicates "
            "the handler is an adapter (ingress/egress, bridge, gateway) with "
            "stricter defaults: no secrets access, narrow permissions. "
            "CONSTRAINT: is_adapter=True requires handler_type_category=EFFECT. "
            "Use for: Kafka ingress/egress, HTTP gateway, webhook, CLI bridge. "
            "Do NOT use for: DB, Vault, Consul, outbound HTTP client handlers."
        ),
    )

    # =========================================================================
    # Surface
    # =========================================================================

    capabilities: list[EnumHandlerCapability] = Field(
        default_factory=list,
        description=(
            "List of capabilities the handler supports. Used for capability-based "
            "routing and runtime optimization. "
            "Values: CACHE, RETRY, BATCH, STREAM, ASYNC, IDEMPOTENT, etc."
        ),
    )

    commands_accepted: list[EnumHandlerCommandType] = Field(
        default_factory=list,
        description=(
            "List of command types the handler responds to. "
            "Values: EXECUTE, VALIDATE, DRY_RUN, ROLLBACK, HEALTH_CHECK, etc."
        ),
    )

    # =========================================================================
    # Instantiation (one or the other, both optional)
    # =========================================================================

    import_path: str | None = Field(
        default=None,
        description=(
            "Python import path for direct instantiation. "
            "Format: 'package.module.ClassName' (e.g., 'mypackage.handlers.MyHandler'). "
            "Mutually exclusive with artifact_ref for instantiation strategy."
        ),
    )

    artifact_ref: ModelArtifactRef | None = Field(
        default=None,
        description=(
            "Artifact reference for registry-resolved instantiation. "
            "Used for containerized handlers or external artifacts that are "
            "resolved at runtime through the artifact registry."
        ),
    )

    # =========================================================================
    # Optional Metadata
    # =========================================================================

    security_metadata_ref: ModelSecurityMetadataRef | None = Field(
        default=None,
        description=(
            "Reference to security metadata configuration. When resolved, "
            "provides allowed domains, secret scopes, classification level, "
            "and access control policies."
        ),
    )

    packaging_metadata_ref: ModelPackagingMetadataRef | None = Field(
        default=None,
        description=(
            "Reference to packaging metadata configuration. When resolved, "
            "provides dependencies, entry points, extras, and distribution metadata."
        ),
    )

    # =========================================================================
    # Validators
    # =========================================================================

    @model_validator(mode="after")
    def validate_adapter_requires_effect_category(self) -> ModelHandlerDescriptor:
        """
        Validate that adapters have EFFECT handler_type_category.

        Adapters are platform plumbing that perform I/O by definition. Therefore,
        if is_adapter=True, handler_type_category MUST be EFFECT.

        This validation ensures semantic consistency: you cannot have an adapter
        that claims to be pure COMPUTE (no I/O) because adapters inherently do I/O.

        Returns:
            Self if validation passes.

        Raises:
            ModelOnexError: If is_adapter=True but handler_type_category is not EFFECT.
        """
        if (
            self.is_adapter
            and self.handler_type_category != EnumHandlerTypeCategory.EFFECT
        ):
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=(
                    f"Handler '{self.handler_name}' has is_adapter=True but "
                    f"handler_type_category={self.handler_type_category.value}. "
                    f"Adapters MUST have handler_type_category=EFFECT because "
                    f"they perform I/O by definition. "
                    f"If this handler does not perform I/O, set is_adapter=False."
                ),
            )
        return self


__all__ = ["ModelHandlerDescriptor"]
