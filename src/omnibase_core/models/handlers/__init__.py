"""
Handler models for ONEX framework.

This module provides models for handler-related functionality including
artifact references, identifiers, packaging metadata references, security
metadata references, handler descriptors, handler type metadata, and other
handler configuration types.

Key Models
----------
ModelHandlerDescriptor
    Canonical runtime representation of a handler. Contains all metadata
    necessary for handler discovery, instantiation, routing, and lifecycle
    management. This is the authoritative runtime object produced by parsing
    handler contracts (YAML/JSON).

ModelIdentifier
    Structured identifier following the ``namespace:name[@variant]`` pattern.
    Used as the primary key for handler registry lookup and discovery.
    Immutable and hashable for use as dict keys.

ModelArtifactRef
    Opaque artifact reference for registry-resolved instantiation.
    Enables decoupled artifact management without inline content.

ModelSecurityMetadataRef
    Reference to security metadata configuration (allowed domains,
    secret scopes, classification level, access control policies).

ModelPackagingMetadataRef
    Reference to packaging metadata configuration (dependencies,
    entry points, distribution metadata).

ModelHandlerTypeMetadata
    Metadata describing handler type behavior (replay safety, secrets,
    determinism, caching, idempotency). Used for runtime decisions about
    handler execution semantics.

Example Usage
-------------
Creating a handler descriptor:

    >>> from omnibase_core.models.handlers import (
    ...     ModelHandlerDescriptor,
    ...     ModelIdentifier,
    ... )
    >>> from omnibase_core.enums import (
    ...     EnumHandlerRole,
    ...     EnumHandlerType,
    ...     EnumHandlerTypeCategory,
    ... )
    >>> from omnibase_core.models.primitives.model_semver import ModelSemVer
    >>>
    >>> descriptor = ModelHandlerDescriptor(
    ...     handler_name=ModelIdentifier(namespace="onex", name="validator"),
    ...     handler_version=ModelSemVer(major=1, minor=0, patch=0),
    ...     handler_role=EnumHandlerRole.COMPUTE_HANDLER,
    ...     handler_type=EnumHandlerType.NAMED,
    ...     handler_type_category=EnumHandlerTypeCategory.COMPUTE,
    ...     import_path="mypackage.handlers.Validator",
    ... )

Working with identifiers:

    >>> from omnibase_core.models.handlers import ModelIdentifier
    >>>
    >>> # Create from fields
    >>> id1 = ModelIdentifier(namespace="onex", name="compute")
    >>> str(id1)
    'onex:compute'
    >>>
    >>> # Parse from string
    >>> id2 = ModelIdentifier.parse("vendor:handler@v2")
    >>> id2.variant
    'v2'
    >>>
    >>> # Use as dict keys
    >>> cache = {id1: "cached_value"}
    >>> id1 in cache
    True

Working with handler type metadata:

    >>> from omnibase_core.models.handlers import get_handler_type_metadata
    >>> from omnibase_core.enums import EnumHandlerTypeCategory
    >>>
    >>> # Get metadata for a handler category
    >>> metadata = get_handler_type_metadata(EnumHandlerTypeCategory.COMPUTE)
    >>> metadata.is_replay_safe
    True
    >>> metadata.allows_caching
    True

End-to-End Runtime Example
--------------------------
This example shows the complete flow from YAML contract to runtime descriptor
to handler instantiation.

**Step 1: Define a handler contract (YAML)**

.. code-block:: yaml

    # handler_contract.yaml
    handler_name: "onex:my-validator"
    handler_version: "1.0.0"
    handler_role: COMPUTE_HANDLER
    handler_type: NAMED
    handler_type_category: COMPUTE
    capabilities:
      - VALIDATE
      - CACHE
      - IDEMPOTENT
    import_path: "mypackage.handlers.MyValidator"

**Step 2: Parse contract into descriptor**

.. code-block:: python

    import yaml
    from omnibase_core.models.handlers import ModelHandlerDescriptor, ModelIdentifier
    from omnibase_core.enums import (
        EnumHandlerRole, EnumHandlerType, EnumHandlerTypeCategory, EnumHandlerCapability
    )
    from omnibase_core.models.primitives.model_semver import ModelSemVer

    def load_descriptor_from_yaml(path: str) -> ModelHandlerDescriptor:
        with open(path, "r") as f:
            contract = yaml.safe_load(f)

        handler_name = ModelIdentifier.parse(contract["handler_name"])
        version_parts = contract["handler_version"].split(".")
        handler_version = ModelSemVer(
            major=int(version_parts[0]),
            minor=int(version_parts[1]),
            patch=int(version_parts[2]),
        )

        return ModelHandlerDescriptor(
            handler_name=handler_name,
            handler_version=handler_version,
            handler_role=EnumHandlerRole[contract["handler_role"]],
            handler_type=EnumHandlerType[contract["handler_type"]],
            handler_type_category=EnumHandlerTypeCategory[contract["handler_type_category"]],
            capabilities=[EnumHandlerCapability[cap] for cap in contract.get("capabilities", [])],
            import_path=contract.get("import_path"),
        )

    descriptor = load_descriptor_from_yaml("handler_contract.yaml")

**Step 3: Instantiate handler from descriptor**

.. code-block:: python

    import importlib

    def instantiate_handler(descriptor: ModelHandlerDescriptor):
        if not descriptor.has_instantiation_method:
            raise ValueError(f"Descriptor {descriptor.handler_name} has no instantiation method")

        if descriptor.import_path:
            module_path, class_name = descriptor.import_path.rsplit(".", 1)
            module = importlib.import_module(module_path)
            handler_class = getattr(module, class_name)
            return handler_class()

        elif descriptor.artifact_ref:
            raise NotImplementedError("Artifact registry resolution not shown")

        raise ValueError("No instantiation method available")

    handler = instantiate_handler(descriptor)

**Step 4: Use descriptor for routing decisions**

.. code-block:: python

    def find_handlers_by_capability(
        registry: list[ModelHandlerDescriptor],
        required: set[EnumHandlerCapability],
    ) -> list[ModelHandlerDescriptor]:
        return [h for h in registry if required.issubset(set(h.capabilities))]

    # Find all cacheable, idempotent handlers
    cacheable = find_handlers_by_capability(
        registry=[descriptor],
        required={EnumHandlerCapability.CACHE, EnumHandlerCapability.IDEMPOTENT},
    )

Thread Safety
-------------
All models in this module are immutable (frozen=True) after creation,
making them thread-safe for concurrent read access from multiple threads
or async tasks.

See Also
--------
omnibase_core.enums.enum_handler_role : Handler role classification
omnibase_core.enums.enum_handler_type : Handler type classification
omnibase_core.enums.enum_handler_type_category : Behavioral classification
omnibase_core.enums.enum_handler_capability : Handler capabilities

.. versionadded:: 0.4.0
"""

from omnibase_core.models.handlers.model_artifact_ref import ModelArtifactRef
from omnibase_core.models.handlers.model_handler_descriptor import (
    ModelHandlerDescriptor,
)
from omnibase_core.models.handlers.model_handler_packaging import ModelHandlerPackaging
from omnibase_core.models.handlers.model_handler_type_metadata import (
    ModelHandlerTypeMetadata,
    get_handler_type_metadata,
)
from omnibase_core.models.handlers.model_identifier import ModelIdentifier
from omnibase_core.models.handlers.model_packaging_metadata_ref import (
    ModelPackagingMetadataRef,
)
from omnibase_core.models.handlers.model_sandbox_requirements import (
    ModelSandboxRequirements,
)
from omnibase_core.models.handlers.model_security_metadata_ref import (
    ModelSecurityMetadataRef,
)

__all__ = [
    "ModelArtifactRef",
    "ModelHandlerDescriptor",
    "ModelHandlerPackaging",
    "ModelHandlerTypeMetadata",
    "ModelIdentifier",
    "ModelPackagingMetadataRef",
    "ModelSandboxRequirements",
    "ModelSecurityMetadataRef",
    "get_handler_type_metadata",
]
