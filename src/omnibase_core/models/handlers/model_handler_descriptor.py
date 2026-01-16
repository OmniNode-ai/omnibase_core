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

    Metadata-Only Descriptors
    -------------------------
    Both ``import_path`` and ``artifact_ref`` are optional, allowing for
    **metadata-only descriptors** that contain no instantiation information.
    This is an intentional design choice supporting several use cases:

    1. **Discovery Metadata**: Descriptors used purely for registry queries,
       routing decisions, or capability matching without actual instantiation.

    2. **External Handlers**: Handlers instantiated outside the Python runtime
       (e.g., sidecar containers, external services) where the descriptor
       provides routing/classification metadata only.

    3. **Deferred Resolution**: Descriptors where instantiation information
       is resolved separately through a lookup service or configuration.

    4. **Documentation/Introspection**: Descriptors that document a handler's
       contract without providing runtime instantiation.

    When both fields are None, the descriptor can still be used for:
        - Classification and routing decisions
        - Capability-based handler matching
        - Security policy evaluation via ``security_metadata_ref``
        - Registry listing and discovery

    If instantiation is required, callers should check ``has_instantiation_method``
    or verify that ``import_path`` or ``artifact_ref`` is set.

    Instantiation Precedence (import_path vs artifact_ref)
    ------------------------------------------------------
    When **both** ``import_path`` and ``artifact_ref`` are set, the runtime
    follows a defined precedence order:

    1. **import_path takes precedence** - Direct Python import is attempted first
    2. **artifact_ref is fallback** - Only used if import_path is None or import fails

    This design enables several practical patterns:

    **Pattern 1: Development Override**::

        # Production: Uses container image from artifact registry
        # Development: Uses local Python class via import_path
        descriptor = ModelHandlerDescriptor(
            handler_name=ModelIdentifier(namespace="onex", name="my-handler"),
            handler_version=ModelSemVer(major=1, minor=0, patch=0),
            handler_role=EnumHandlerRole.COMPUTE_HANDLER,
            handler_type=EnumHandlerType.NAMED,
            handler_type_category=EnumHandlerTypeCategory.COMPUTE,
            import_path="myproject.handlers.MyHandler",  # Dev: used first
            artifact_ref=ModelArtifactRef(              # Prod: fallback
                registry="ghcr.io",
                repository="myorg/my-handler",
                tag="v1.0.0",
            ),
        )

    **Pattern 2: Hybrid Deployment**::

        # Some handlers run in-process (Python), others as containers
        # import_path set = in-process Python instantiation
        # Only artifact_ref set = container/external instantiation

    **Pattern 3: Graceful Degradation**::

        # Try local import first (faster, no network)
        # Fall back to artifact registry if local unavailable
        # Useful for edge deployments with intermittent connectivity

    **Best Practice**: For most use cases, set only ONE instantiation method
    to avoid ambiguity. Use both only when you explicitly need the fallback
    behavior described above.

    Attributes:
        handler_name: Structured identifier following the namespace:name pattern.
            Used as the primary key for registry lookup.
        handler_version: Semantic version of the handler implementation.
            Used for version validation and version-pinned instantiation.
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
            "version validation and version-pinned instantiation."
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
            "COMMON PATTERNS: "
            "[CACHE, IDEMPOTENT, VALIDATE] for pure compute (safe to memoize/retry); "
            "[STREAM, ASYNC, BATCH] for event handlers (high-throughput, non-blocking); "
            "[RETRY, CIRCUIT_BREAKER, TIMEOUT] for resilient I/O (fault-tolerant). "
            "FILTERING: Use set operations for matching - "
            "ALL required: required.issubset(set(h.capabilities)); "
            "ANY desired: desired.intersection(set(h.capabilities)). "
            "RUNTIME IMPLICATIONS: CACHE enables memoization; IDEMPOTENT enables "
            "auto-retry; CIRCUIT_BREAKER enables fail-fast; ASYNC indicates "
            "non-blocking execution. "
            "See class docstring 'Capability Patterns' section for detailed examples. "
            "Values: CACHE, RETRY, BATCH, STREAM, ASYNC, IDEMPOTENT, VALIDATE, "
            "CIRCUIT_BREAKER, TIMEOUT, etc."
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
    # Instantiation
    # =========================================================================
    # Both fields are optional, supporting metadata-only descriptors.
    # See class docstring "Metadata-Only Descriptors" section for rationale.
    #
    # Usage patterns:
    #   - import_path only: Direct Python instantiation
    #   - artifact_ref only: Registry-resolved instantiation (containers, external)
    #   - Neither: Metadata-only descriptor (discovery, routing, documentation)
    #   - Both: import_path takes precedence; artifact_ref is fallback
    #           (useful for dev-override, hybrid deployment, graceful degradation)
    #
    # Use has_instantiation_method property to check if instantiation is possible.
    # =========================================================================

    import_path: str | None = Field(
        default=None,
        description=(
            "Python import path for direct instantiation. "
            "Format: 'package.module.ClassName' (e.g., 'mypackage.handlers.MyHandler'). "
            "PRECEDENCE: When BOTH import_path and artifact_ref are set, import_path "
            "takes precedence and is attempted first. artifact_ref serves as fallback. "
            "This enables dev-override patterns (local class in dev, container in prod). "
            "Both fields may be None for metadata-only descriptors (see class docstring "
            "'Metadata-Only Descriptors' section). See 'Instantiation Precedence' "
            "section for detailed patterns and best practices."
        ),
    )

    artifact_ref: ModelArtifactRef | None = Field(
        default=None,
        description=(
            "Artifact reference for registry-resolved instantiation. "
            "Used for containerized handlers or external artifacts that are "
            "resolved at runtime through the artifact registry. "
            "PRECEDENCE: When BOTH import_path and artifact_ref are set, this field "
            "serves as FALLBACK - only used if import_path is None or import fails. "
            "This enables graceful degradation (try local first, then container). "
            "Both fields may be None for metadata-only descriptors (see class docstring "
            "'Metadata-Only Descriptors' and 'Instantiation Precedence' sections)."
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

    def __repr__(self) -> str:
        """Return a concise representation for debugging."""
        return (
            f"ModelHandlerDescriptor("
            f"name={self.handler_name}, "
            f"role={self.handler_role.value}, "
            f"type={self.handler_type.value}, "
            f"category={self.handler_type_category.value})"
        )

    # =========================================================================
    # Computed Properties
    # =========================================================================

    @property
    def has_instantiation_method(self) -> bool:
        """
        Check if this descriptor has an instantiation method defined.

        Returns True if either ``import_path`` or ``artifact_ref`` is set,
        indicating that the handler can be instantiated. Returns False for
        metadata-only descriptors.

        Use this property to determine if a descriptor can be used for
        handler instantiation vs. only for discovery/routing metadata.

        Returns:
            True if import_path or artifact_ref is set, False otherwise.

        Example:
            >>> descriptor = ModelHandlerDescriptor(...)
            >>> if descriptor.has_instantiation_method:
            ...     handler = instantiate(descriptor)
            ... else:
            ...     # Metadata-only, use for routing decisions
            ...     pass
        """
        return self.import_path is not None or self.artifact_ref is not None

    def can_instantiate_via_import(self) -> bool:
        """
        Check if handler can be instantiated via Python import path.

        This method returns True if ``import_path`` is set, indicating that
        the handler class can be loaded directly via Python's import machinery.

        Use this when you need to determine the instantiation strategy:
            - ``can_instantiate_via_import()`` -> Use ``importlib.import_module()``
            - ``can_instantiate_via_artifact()`` -> Use artifact registry resolution

        Returns:
            True if import_path is set and can be used for instantiation.

        Example:
            >>> if descriptor.can_instantiate_via_import():
            ...     module_path, class_name = descriptor.import_path.rsplit(".", 1)
            ...     module = importlib.import_module(module_path)
            ...     handler_class = getattr(module, class_name)
            ...     handler = handler_class()

        See Also:
            - :meth:`can_instantiate_via_artifact`: For registry-resolved instantiation
            - :attr:`has_instantiation_method`: To check if any method is available
        """
        return self.import_path is not None

    def can_instantiate_via_artifact(self) -> bool:
        """
        Check if handler can be instantiated via artifact registry resolution.

        This method returns True if ``artifact_ref`` is set, indicating that
        the handler is loaded through an artifact registry (e.g., container
        registry, package registry, or external artifact store).

        Use this when you need to determine the instantiation strategy:
            - ``can_instantiate_via_import()`` -> Use ``importlib.import_module()``
            - ``can_instantiate_via_artifact()`` -> Use artifact registry resolution

        Returns:
            True if artifact_ref is set and can be used for instantiation.

        Example:
            >>> if descriptor.can_instantiate_via_artifact():
            ...     artifact = artifact_registry.resolve(descriptor.artifact_ref)
            ...     handler = artifact.instantiate()

        See Also:
            - :meth:`can_instantiate_via_import`: For direct Python import
            - :attr:`has_instantiation_method`: To check if any method is available
        """
        return self.artifact_ref is not None

    # =========================================================================
    # Validators
    # =========================================================================

    @model_validator(mode="after")
    def validate_adapter_requires_effect_category(self) -> "ModelHandlerDescriptor":
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


# Rebuild model to resolve forward references (required after removing
# `from __future__ import annotations` per project guidelines in CLAUDE.md)
ModelHandlerDescriptor.model_rebuild()

__all__ = ["ModelHandlerDescriptor"]
