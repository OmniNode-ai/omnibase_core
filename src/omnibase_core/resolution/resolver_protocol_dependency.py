"""Protocol dependency resolver for contract-driven DI.

This module provides resolution of protocol dependencies declared in node contracts.
At node initialization, the resolver processes ModelProtocolDependency declarations
and resolves them from the ONEX container.

Resolution Process:
    1. Validate protocol exists (import check) unless lazy_import is enabled
    2. Resolve service from container using the dependency name
    3. Return dict keyed by bind name (from dep.get_bind_name())
    4. Handle required vs optional (fail fast vs None)

Thread Safety:
    This module is thread-safe. The rate-limiting state uses a module-level
    dictionary with simple timestamp comparisons, which is safe for concurrent
    reads with occasional writes.

Example:
    >>> from omnibase_core.resolution import resolve_protocol_dependencies
    >>> deps = [
    ...     ModelProtocolDependency(
    ...         name="ProtocolLogger",
    ...         protocol="omnibase_core.protocols.protocol_logger:ProtocolLogger",
    ...     )
    ... ]
    >>> resolved = resolve_protocol_dependencies(deps, container)
    >>> print(resolved)  # {"logger": <ProtocolLogger instance>}

See Also:
    - OMN-1731: Contract-driven zero-code node base classes
    - ModelProtocolDependency: The dependency declaration model

.. versionadded:: 0.4.1
"""

from __future__ import annotations

import importlib
import time
from types import ModuleType

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_log_level import EnumLogLevel
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.contracts.subcontracts.model_protocol_dependency import (
    ModelProtocolDependency,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError

# Rate limiting for optional missing dependency warnings
_OPTIONAL_WARNING_INTERVAL_MS = 60_000  # 1 minute
_last_warning_times: dict[str, float] = {}


def _validate_protocol_importable(protocol_path: str) -> type[object]:
    """
    Validate protocol class can be imported (fail fast on typos).

    Parses the "module.path:ClassName" format and attempts to import
    the module and retrieve the class. This catches configuration errors
    at startup rather than at first use.

    Args:
        protocol_path: Import path in 'module.path:ClassName' format.

    Returns:
        The imported protocol class.

    Raises:
        ModelOnexError: If the module cannot be imported or the class
            does not exist in the module.
    """
    # Parse "module.path:ClassName" format
    if ":" not in protocol_path:
        raise ModelOnexError(
            message=f"Invalid protocol path format: {protocol_path!r}. Expected 'module.path:ClassName'",
            error_code=EnumCoreErrorCode.PROTOCOL_CONFIGURATION_ERROR,
            protocol_path=protocol_path,
        )

    module_path, class_name = protocol_path.rsplit(":", 1)

    module: ModuleType
    try:
        module = importlib.import_module(module_path)
    except ImportError as e:
        raise ModelOnexError(
            message=f"Cannot import module for protocol: {module_path}",
            error_code=EnumCoreErrorCode.PROTOCOL_CONFIGURATION_ERROR,
            protocol_path=protocol_path,
            module_path=module_path,
            class_name=class_name,
            import_error=str(e),
        ) from e

    protocol_class: object
    try:
        protocol_class = getattr(module, class_name)
    except AttributeError as e:
        raise ModelOnexError(
            message=f"Protocol class '{class_name}' not found in module '{module_path}'",
            error_code=EnumCoreErrorCode.PROTOCOL_CONFIGURATION_ERROR,
            protocol_path=protocol_path,
            module_path=module_path,
            class_name=class_name,
        ) from e

    # Validate that the result is actually a type/class
    if not isinstance(protocol_class, type):
        raise ModelOnexError(
            message=f"'{class_name}' in module '{module_path}' is not a class",
            error_code=EnumCoreErrorCode.PROTOCOL_CONFIGURATION_ERROR,
            protocol_path=protocol_path,
            module_path=module_path,
            class_name=class_name,
            actual_type=type(protocol_class).__name__,
        )

    return protocol_class


def _emit_optional_missing_warning(
    dep: ModelProtocolDependency,
    node_id: str | None,
) -> None:
    """
    Emit rate-limited warning for missing optional dependency.

    Warnings are rate-limited per dependency name to avoid log spam when
    the same optional dependency is repeatedly unavailable.

    Args:
        dep: The protocol dependency that could not be resolved.
        node_id: Optional node ID for logging context.
    """
    # Rate limiting key
    key = f"{node_id or 'unknown'}:{dep.name}"
    current_time_ms = time.time() * 1000

    last_warning = _last_warning_times.get(key, 0)
    if current_time_ms - last_warning < _OPTIONAL_WARNING_INTERVAL_MS:
        return  # Skip warning due to rate limiting

    _last_warning_times[key] = current_time_ms

    # Try to emit structured log
    try:
        from omnibase_core.logging.logging_structured import emit_log_event_sync

        emit_log_event_sync(
            EnumLogLevel.WARNING,
            f"Optional protocol dependency '{dep.name}' not available",
            {
                "dependency_name": dep.name,
                "protocol_path": dep.protocol,
                "bind_name": dep.get_bind_name(),
                "node_id": node_id,
            },
        )
    except ImportError:
        # Logging module not available, skip warning
        pass


def resolve_protocol_dependencies(
    deps: list[ModelProtocolDependency],
    container: ModelONEXContainer,
    *,
    node_id: str | None = None,
) -> dict[str, object | None]:
    """
    Resolve protocol dependencies from contract declarations.

    Processes a list of ModelProtocolDependency declarations and resolves
    each from the ONEX container. Required dependencies must be available
    or resolution fails fast. Optional dependencies return None if unavailable.

    Resolution Process:
        1. Validate protocol exists (import check) unless lazy_import
        2. Resolve service from container using dep.name
        3. Return dict keyed by dep.get_bind_name()
        4. Handle required vs optional (fail fast vs None)

    lazy_import Semantics:
        When lazy_import=True, the initial validation step is skipped, allowing
        nodes to initialize even if the protocol module is temporarily unavailable.
        However, the import is still attempted during resolution (step 2) with
        graceful error handling. This is useful for optional dependencies where
        the module may not be installed, or for cold-start optimization where
        import errors should not block initialization.

    Args:
        deps: List of ModelProtocolDependency from contract.
        container: ONEX container for service resolution.
        node_id: Optional node ID for logging context.

    Returns:
        Dict mapping bind names to resolved services (or None for optional
        missing dependencies).

    Raises:
        ModelOnexError: If a required dependency cannot be resolved.

    Example:
        >>> deps = [
        ...     ModelProtocolDependency(
        ...         name="ProtocolLogger",
        ...         protocol="omnibase_core.protocols.protocol_logger:ProtocolLogger",
        ...         required=True,
        ...     ),
        ...     ModelProtocolDependency(
        ...         name="ProtocolCache",
        ...         protocol="omnibase_core.protocols.protocol_cache:ProtocolCache",
        ...         required=False,
        ...     ),
        ... ]
        >>> resolved = resolve_protocol_dependencies(deps, container)
        >>> # resolved = {"logger": <service>, "cache": None or <service>}

    Thread Safety:
        This function is thread-safe. It uses the container's thread-safe
        service resolution and module-level rate limiting that is safe for
        concurrent access.

    See Also:
        - ModelProtocolDependency: The dependency declaration model
        - ModelONEXContainer: The DI container

    .. versionadded:: 0.4.1
    """
    resolved: dict[str, object | None] = {}

    for dep in deps:
        bind_name = dep.get_bind_name()

        try:
            # 1. Attempt to import protocol class
            # For eager (lazy_import=False): fail fast on import errors
            # For lazy (lazy_import=True): catch errors and continue with None
            protocol_class: type[object] | None = None
            try:
                protocol_class = _validate_protocol_importable(dep.protocol)
            except ModelOnexError:
                if not dep.lazy_import:
                    raise  # Eager: propagate import failures immediately
                # Lazy: import failed, protocol_class stays None

            # 2. Resolve from container using protocol class (if available)
            service: object | None = None
            if protocol_class is not None:
                service = container.get_service_optional(protocol_class)

            if service is not None:
                resolved[bind_name] = service
                # Log successful resolution at DEBUG level
                try:
                    from omnibase_core.logging.logging_structured import (
                        emit_log_event_sync,
                    )

                    emit_log_event_sync(
                        EnumLogLevel.DEBUG,
                        f"Resolved protocol dependency: {dep.name} -> {bind_name}",
                        {
                            "dependency_name": dep.name,
                            "bind_name": bind_name,
                            "node_id": node_id,
                        },
                    )
                except ImportError:
                    pass
            elif dep.required:
                # Required dependency not available - fail fast
                raise ModelOnexError(
                    message=f"Failed to resolve required protocol: {dep.name}",
                    error_code=EnumCoreErrorCode.PROTOCOL_CONFIGURATION_ERROR,
                    dependency_name=dep.name,
                    protocol_path=dep.protocol,
                    bind_name=bind_name,
                    node_id=node_id,
                    hint="Ensure the protocol is registered in the container's ServiceRegistry",
                )
            else:
                # Optional dependency not available
                resolved[bind_name] = None
                _emit_optional_missing_warning(dep, node_id)

        except ModelOnexError:
            # Re-raise ModelOnexError as-is to preserve context
            raise

        except (AttributeError, ImportError, KeyError, LookupError) as e:
            if dep.required:
                raise ModelOnexError(
                    message=f"Failed to resolve required protocol: {dep.name}",
                    error_code=EnumCoreErrorCode.PROTOCOL_CONFIGURATION_ERROR,
                    dependency_name=dep.name,
                    protocol_path=dep.protocol,
                    bind_name=bind_name,
                    node_id=node_id,
                    original_error=str(e),
                    original_error_type=type(e).__name__,
                ) from e
            # Optional dependency not available
            resolved[bind_name] = None
            _emit_optional_missing_warning(dep, node_id)

    return resolved


__all__ = [
    "resolve_protocol_dependencies",
]
