"""
Manifest Observer for Pipeline Integration.

Provides the ManifestObserver class which integrates with pipeline execution
via ModelPipelineContext.data for non-invasive instrumentation.

This observer allows the manifest generator to be attached to pipeline
execution without modifying the core runner implementation.

.. versionadded:: 0.4.0
    Added as part of Manifest Generation & Observability (OMN-1113)
"""

import warnings
from uuid import UUID

from omnibase_core.models.manifest.model_contract_identity import ModelContractIdentity
from omnibase_core.models.manifest.model_execution_manifest import (
    ModelExecutionManifest,
)
from omnibase_core.models.manifest.model_node_identity import ModelNodeIdentity
from omnibase_core.pipeline.manifest_generator import ManifestGenerator


class ManifestObserver:
    """
    Observer that integrates manifest generation with pipeline execution.

    This class provides static methods to attach a ManifestGenerator to
    pipeline context data and retrieve it during execution. It enables
    non-invasive instrumentation of pipeline runs.

    The observer uses ModelPipelineContext.data (a shared dict) to store the
    generator, making it accessible to all hooks during execution.

    Example:
        >>> # In pipeline runner initialization
        >>> context_data = {}
        >>> generator = ManifestObserver.attach(
        ...     context_data,
        ...     node_identity=node_identity,
        ...     contract_identity=contract_identity,
        ... )
        >>>
        >>> # During hook execution
        >>> generator = ManifestObserver.get_generator(context_data)
        >>> if generator:
        ...     generator.start_hook("hook-1", "handler-1", phase)
        >>>
        >>> # After pipeline completes
        >>> manifest = ManifestObserver.build_manifest(context_data)

    Thread Safety:
        ManifestObserver class methods are stateless and do not maintain internal
        state. However, the ``context_data`` dict and the stored ManifestGenerator
        are NOT thread-safe. Concurrent access to the same ``context_data`` dict
        from multiple threads requires external synchronization.

        See :class:`ManifestGenerator` for detailed thread safety considerations.

    See Also:
        - :class:`~omnibase_core.pipeline.manifest_generator.ManifestGenerator`:
          The generator that this observer manages

    .. versionadded:: 0.4.0
        Added as part of Manifest Generation & Observability (OMN-1113)
    """

    CONTEXT_KEY = (
        "__omnibase_manifest_generator__"  # env-var-ok: internal context key constant
    )
    """Key used to store the generator in pipeline context data.

    Uses dunder naming convention to minimize collision risk with user keys.
    """

    @classmethod
    def attach(
        cls,
        context_data: dict[str, object],
        node_identity: ModelNodeIdentity,
        contract_identity: ModelContractIdentity,
        correlation_id: UUID | None = None,
        parent_manifest_id: UUID | None = None,
    ) -> ManifestGenerator:
        """
        Attach a manifest generator to pipeline context.

        Creates a new ManifestGenerator and stores it in the context data
        dict under the CONTEXT_KEY. The generator can then be accessed
        throughout the pipeline execution.

        If a generator already exists in the context, a warning is emitted
        but the new generator will still replace it. This ensures backward
        compatibility while alerting developers to potential issues.

        Args:
            context_data: The pipeline context data dict
            node_identity: Identity of the executing node
            contract_identity: Identity of the driving contract
            correlation_id: Optional correlation ID for tracing
            parent_manifest_id: Parent manifest ID if nested

        Returns:
            The created ManifestGenerator

        Warns:
            UserWarning: If a generator already exists in the context
        """
        # Check for existing generator - warn but still overwrite
        if cls.CONTEXT_KEY in context_data:
            warnings.warn(
                "Overwriting existing ManifestGenerator in context. "
                "This may indicate a programming error or nested pipeline execution.",
                stacklevel=2,
            )

        generator = ManifestGenerator(
            node_identity=node_identity,
            contract_identity=contract_identity,
            correlation_id=correlation_id,
            parent_manifest_id=parent_manifest_id,
        )
        context_data[cls.CONTEXT_KEY] = generator
        return generator

    @classmethod
    def get_generator(
        cls,
        context_data: dict[str, object],
    ) -> ManifestGenerator | None:
        """
        Get the manifest generator from pipeline context.

        Args:
            context_data: The pipeline context data dict

        Returns:
            The ManifestGenerator if attached and valid type, None otherwise
        """
        value = context_data.get(cls.CONTEXT_KEY)
        if isinstance(value, ManifestGenerator):
            return value
        return None

    @classmethod
    def has_generator(cls, context_data: dict[str, object]) -> bool:
        """
        Check if a manifest generator is attached and valid.

        Args:
            context_data: The pipeline context data dict

        Returns:
            True if a generator is attached and is a valid ManifestGenerator instance
        """
        value = context_data.get(cls.CONTEXT_KEY)
        return isinstance(value, ManifestGenerator)

    @classmethod
    def build_manifest(
        cls,
        context_data: dict[str, object],
    ) -> ModelExecutionManifest | None:
        """
        Build and return the manifest from context.

        Retrieves the generator from context and calls build() to create
        the final manifest. Returns None if no generator is attached.

        Args:
            context_data: The pipeline context data dict

        Returns:
            The built manifest if generator exists, None otherwise
        """
        generator = cls.get_generator(context_data)
        if generator:
            return generator.build()
        return None

    @classmethod
    def detach(cls, context_data: dict[str, object]) -> ManifestGenerator | None:
        """
        Remove and return the manifest generator from context.

        Args:
            context_data: The pipeline context data dict

        Returns:
            The removed generator if present and valid type, None otherwise
        """
        value = context_data.pop(cls.CONTEXT_KEY, None)
        if isinstance(value, ManifestGenerator):
            return value
        return None


# Export for use
__all__ = ["ManifestObserver"]
