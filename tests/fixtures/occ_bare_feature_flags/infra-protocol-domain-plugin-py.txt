# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Domain plugin protocol for kernel-level initialization hooks.

This module defines the ProtocolDomainPlugin protocol, enabling domain-specific
initialization to be decoupled from the generic runtime kernel. Domains (such as
Registration, Intelligence, etc.) can implement this protocol to hook into the
kernel bootstrap sequence.

Design Pattern:
    The plugin pattern follows dependency inversion - the kernel depends on the
    abstract ProtocolDomainPlugin protocol, not concrete implementations. Each
    domain provides its own plugin that implements the protocol.

    ```
    +-------------------------------------------------------------+
    |                        Kernel Layer                         |
    |  +--------------------------------------------------------+ |
    |  |  kernel.py                                             | |
    |  |    - Discovers plugins via registry                    | |
    |  |    - Calls plugin hooks during bootstrap               | |
    |  |    - NO domain-specific code                           | |
    |  +--------------------------------------------------------+ |
    |                            |                                 |
    |                            v                                 |
    |  +--------------------------------------------------------+ |
    |  |  ProtocolDomainPlugin (this file)                      | |
    |  |    - Defines initialization hooks                      | |
    |  |    - Plugin identification (plugin_id)                 | |
    |  |    - Lifecycle hooks (initialize, wire_handlers, etc.) | |
    |  +--------------------------------------------------------+ |
    +-------------------------------------------------------------+
                                 |
              +------------------+------------------+
              v                  v                  v
    +-----------------+ +-----------------+ +-----------------+
    |  Registration   | |  Intelligence   | |  Future Domain  |
    |  Plugin         | |  Plugin         | |  Plugin         |
    +-----------------+ +-----------------+ +-----------------+
    ```

Lifecycle Hooks:
    Plugins are initialized in a specific order during kernel bootstrap:

    1. `should_activate()` - Check if plugin should activate based on environment
    2. `initialize()` - Create domain-specific resources (pools, connections)
    3. `validate_handshake()` - Run prerequisite checks (B1-B3) before wiring
    4. `wire_handlers()` - Register handlers in the container
    5. `wire_dispatchers()` - Register dispatchers with MessageDispatchEngine
    6. `start_consumers()` - Start event consumers
    7. `shutdown()` - Clean up resources during kernel shutdown

Plugin Discovery:
    Plugins can be registered in two ways:

    1. **Explicit registration** via ``RegistryDomainPlugin.register()``
       - Clear, auditable plugin loading
       - Easy testing with mock plugins
       - Explicit registrations take precedence over discovered plugins

    2. **Entry-point discovery** via ``RegistryDomainPlugin.discover_from_entry_points()``
       - Uses ``importlib.metadata.entry_points()`` for PEP 621 discovery
       - Namespace-based security: only trusted namespaces are loaded
       - Deterministic ordering by entry-point name then value
       - Duplicate plugin IDs are silently skipped (explicit wins)

    Explicit registration always takes precedence on duplicate ``plugin_id``.
    Entry-point discovery is security-gated by namespace allowlisting
    (pre-import) and protocol validation (post-import).

Example Implementation:
    ```python
    from omnibase_infra.runtime.protocol_domain_plugin import ProtocolDomainPlugin
    from omnibase_infra.runtime.models import (
        ModelDomainPluginConfig,
        ModelDomainPluginResult,
    )
    from omnibase_infra.runtime.models.model_handshake_result import (
        ModelHandshakeResult,
    )

    class PluginMyDomain:
        '''Domain plugin for MyDomain.'''

        @property
        def plugin_id(self) -> str:
            return "my-domain"

        @property
        def display_name(self) -> str:
            return "My Domain"

        def should_activate(self, config: ModelDomainPluginConfig) -> bool:
            return bool(os.getenv("MY_DOMAIN_HOST"))

        async def initialize(
            self,
            config: ModelDomainPluginConfig,
        ) -> ModelDomainPluginResult:
            # Create pools, connections, etc.
            self._pool = await create_pool()
            return ModelDomainPluginResult(
                plugin_id=self.plugin_id,
                success=True,
                resources_created=["pool"],
            )

        async def validate_handshake(
            self,
            config: ModelDomainPluginConfig,
        ) -> ModelHandshakeResult:
            # Optional: run prerequisite checks before wiring
            return ModelHandshakeResult.default_pass(self.plugin_id)

        async def wire_handlers(
            self,
            config: ModelDomainPluginConfig,
        ) -> ModelDomainPluginResult:
            # Register handlers with container
            await wire_my_domain_handlers(config.container, self._pool)
            return ModelDomainPluginResult.succeeded(
                plugin_id=self.plugin_id,
                services_registered=["MyHandler"],
            )

        async def shutdown(
            self,
            config: ModelDomainPluginConfig,
        ) -> ModelDomainPluginResult:
            await self._pool.close()
            return ModelDomainPluginResult.succeeded(plugin_id=self.plugin_id)
    ```

Related:
    - OMN-1346: Registration Code Extraction
    - OMN-888: Registration Orchestrator
"""

from __future__ import annotations

import logging
from importlib.metadata import entry_points
from typing import Protocol, runtime_checkable

from omnibase_infra.runtime.constants_security import (
    DOMAIN_PLUGIN_ENTRY_POINT_GROUP,
)
from omnibase_infra.runtime.models import (
    ModelDomainPluginConfig,
    ModelDomainPluginResult,
)
from omnibase_infra.runtime.models.model_handshake_result import (
    ModelHandshakeResult,
)
from omnibase_infra.runtime.models.model_plugin_discovery_entry import (
    ModelPluginDiscoveryEntry,
)
from omnibase_infra.runtime.models.model_plugin_discovery_report import (
    ModelPluginDiscoveryReport,
)
from omnibase_infra.runtime.models.model_security_config import ModelSecurityConfig
from omnibase_infra.utils.util_error_sanitization import sanitize_error_message
from omnibase_infra.utils.util_runtime_packages import (
    get_active_runtime_packages,
    is_runtime_package_active,
)

logger = logging.getLogger(__name__)


@runtime_checkable
class ProtocolDomainPlugin(Protocol):
    """Protocol for domain-specific initialization plugins.

    Domain plugins implement this protocol to hook into the kernel bootstrap
    sequence. Each plugin is responsible for initializing its domain-specific
    resources, wiring handlers, and cleaning up during shutdown.

    The protocol uses duck typing - any class that implements these methods
    can be used as a domain plugin without explicit inheritance.

    Thread Safety:
        Plugin implementations should be thread-safe if they maintain state.
        The kernel calls plugin methods sequentially during bootstrap, but
        plugins may be accessed concurrently during runtime.

    Lifecycle Order:
        1. should_activate() - Check environment/config
        2. initialize() - Create pools, connections
        3. validate_handshake() - Run prerequisite checks (optional, default pass)
        4. wire_handlers() - Register handlers in container
        5. wire_dispatchers() - Register with dispatch engine (optional)
        6. start_consumers() - Start event consumers (optional)
        7. shutdown() - Clean up during kernel shutdown

    Optional Methods:
        ``validate_handshake()`` is **not** part of this Protocol definition
        because it is optional. Plugins that implement it will be detected at
        runtime via ``hasattr()`` in the kernel. Plugins that omit it pass
        the handshake gate by default.

        This design avoids a ``@runtime_checkable`` pitfall: if an optional
        method were declared in the Protocol, ``isinstance()`` checks in
        entry-point discovery would reject plugins that omit it.

    Example:
        ```python
        class PluginMyDomain:
            @property
            def plugin_id(self) -> str:
                return "my-domain"

            def should_activate(self, config: ModelDomainPluginConfig) -> bool:
                return bool(os.getenv("MY_DOMAIN_ENABLED"))  # ONEX_FLAG_EXEMPT: docstring example

            async def initialize(
                self, config: ModelDomainPluginConfig
            ) -> ModelDomainPluginResult:
                # Initialize domain resources
                return ModelDomainPluginResult.succeeded("my-domain")

            async def validate_handshake(
                self, config: ModelDomainPluginConfig
            ) -> ModelHandshakeResult:
                # Optional: run prerequisite checks
                return ModelHandshakeResult.default_pass("my-domain")

            # ... other methods
        ```
    """

    @property
    def plugin_id(self) -> str:
        """Return unique identifier for this plugin.

        The plugin_id is used for:
        - Logging and diagnostics
        - Plugin registry lookups
        - Status reporting in kernel banner

        Returns:
            Unique string identifier (e.g., "registration", "intelligence").
        """
        ...

    @property
    def display_name(self) -> str:
        """Return human-readable name for this plugin.

        Used in logs and user-facing output.

        Returns:
            Display name (e.g., "Registration", "Intelligence").
        """
        ...

    def should_activate(self, config: ModelDomainPluginConfig) -> bool:
        """Check if this plugin should activate based on configuration.

        Called during bootstrap to determine if the plugin should run.
        Plugins can check environment variables, config values, or other
        conditions to decide whether to activate.

        Args:
            config: Plugin configuration with container and event bus.

        Returns:
            True if the plugin should activate, False to skip.

        Example:
            ```python
            def should_activate(self, config: ModelDomainPluginConfig) -> bool:
                # Only activate if PostgreSQL is configured
                return bool(os.getenv("OMNIBASE_INFRA_DB_URL"))
            ```
        """
        ...

    async def initialize(
        self,
        config: ModelDomainPluginConfig,
    ) -> ModelDomainPluginResult:
        """Initialize domain-specific resources.

        Called after should_activate() returns True. This method should
        create any resources the domain needs (database pools, connections,
        etc.).

        Args:
            config: Plugin configuration with container and event bus.

        Returns:
            Result indicating success/failure and resources created.

        Example:
            ```python
            async def initialize(
                self, config: ModelDomainPluginConfig
            ) -> ModelDomainPluginResult:
                self._pool = await asyncpg.create_pool(dsn)
                return ModelDomainPluginResult.succeeded(
                    "my-domain",
                    resources_created=["postgres_pool"],
                )
            ```
        """
        ...

    async def wire_handlers(
        self,
        config: ModelDomainPluginConfig,
    ) -> ModelDomainPluginResult:
        """Register handlers with the container.

        Called after initialize(). This method should register any
        handlers the domain provides in the container's service registry.

        Args:
            config: Plugin configuration with container and event bus.

        Returns:
            Result indicating success/failure and services registered.

        Example:
            ```python
            async def wire_handlers(
                self, config: ModelDomainPluginConfig
            ) -> ModelDomainPluginResult:
                summary = await wire_my_handlers(config.container, self._pool)
                return ModelDomainPluginResult.succeeded(
                    "my-domain",
                    services_registered=summary["services"],
                )
            ```
        """
        ...

    async def wire_dispatchers(
        self,
        config: ModelDomainPluginConfig,
    ) -> ModelDomainPluginResult:
        """Register dispatchers with MessageDispatchEngine (optional).

        Called after wire_handlers(). This method should register any
        dispatchers the domain provides with the dispatch engine.

        Note: config.dispatch_engine may be None if no engine is configured.
        Implementations should handle this gracefully.

        Args:
            config: Plugin configuration with dispatch_engine set.

        Returns:
            Result indicating success/failure and dispatchers registered.
        """
        ...

    async def start_consumers(
        self,
        config: ModelDomainPluginConfig,
    ) -> ModelDomainPluginResult:
        """Start event consumers (optional).

        Called after wire_dispatchers(). This method should start any
        event consumers the domain needs to process events from the bus.

        Args:
            config: Plugin configuration with container and event bus.

        Returns:
            Result with unsubscribe_callbacks for cleanup during shutdown.
        """
        ...

    async def shutdown(
        self,
        config: ModelDomainPluginConfig,
    ) -> ModelDomainPluginResult:
        """Clean up domain resources during kernel shutdown.

        Called during kernel shutdown. This method should close pools,
        connections, and any other resources created during initialize().

        Shutdown Order (LIFO):
            Plugins are shut down in **reverse activation order** (Last In, First Out).
            This ensures plugins activated later are shut down before plugins they may
            depend on. For example, if plugins A, B, C are activated in order, shutdown
            order is C, B, A.

        Self-Contained Constraint:
            **CRITICAL**: Plugins MUST be self-contained during shutdown.

            - Plugins MUST NOT depend on resources from other plugins during shutdown
            - Each plugin should only clean up its own resources (pools, connections)
            - If a plugin accesses shared resources, it must handle graceful degradation
              in case those resources are already released by another plugin
            - Shutdown errors in one plugin do not block other plugins from shutting down

            This constraint exists because:
            1. Shutdown order may change as plugins are added/removed
            2. Other plugins may fail to initialize, leaving resources unavailable
            3. Exception handling during shutdown should not cascade failures

        Error Handling:
            Implementations should catch and log errors rather than raising them.
            The kernel will continue shutting down other plugins even if one fails.
            Return a failed ModelDomainPluginResult to report errors without blocking.

        Args:
            config: Plugin configuration. Note that during cleanup after errors,
                a minimal config may be passed instead of the original config.

        Returns:
            Result indicating success/failure of cleanup.

        Example:
            ```python
            async def shutdown(
                self, config: ModelDomainPluginConfig
            ) -> ModelDomainPluginResult:
                errors: list[str] = []

                # Close pool - handle graceful degradation
                if self._pool is not None:
                    try:
                        await self._pool.close()
                    except Exception as e:
                        errors.append(f"pool: {e}")
                    self._pool = None  # Always clear reference

                if errors:
                    return ModelDomainPluginResult.failed(
                        plugin_id=self.plugin_id,
                        error_message="; ".join(errors),
                    )
                return ModelDomainPluginResult.succeeded(plugin_id=self.plugin_id)
            ```
        """
        ...


class RegistryDomainPlugin:
    """Registry for domain plugins with hybrid explicit + entry-point discovery.

    Provides two complementary registration mechanisms:

    1. **Explicit registration** via ``register()`` -- the primary path for
       first-party plugins. Direct, auditable, and easy to test.

    2. **Entry-point discovery** via ``discover_from_entry_points()`` --
       secondary mechanism for external packages. Uses PEP 621 entry_points
       to scan installed packages. Security-gated by namespace allowlisting
       and protocol validation.

    Explicit registrations always take precedence: if ``discover_from_entry_points()``
    finds a plugin whose ``plugin_id`` matches an already-registered plugin, the
    discovered plugin is silently skipped and recorded as ``"duplicate_skipped"``
    in the discovery report.

    Thread Safety:
        The registry is NOT thread-safe. Plugin registration should happen
        during startup before concurrent access.

    Example:
        ```python
        from omnibase_infra.runtime.protocol_domain_plugin import (
            RegistryDomainPlugin,
        )
        from omnibase_infra.nodes.node_registration_orchestrator.plugin import (
            ServiceRegistration,
        )

        # 1. Register first-party plugins explicitly
        registry = RegistryDomainPlugin()
        registry.register(ServiceRegistration())

        # 2. Discover third-party plugins from entry_points
        report = registry.discover_from_entry_points()
        if report.has_errors:
            logger.warning("Plugin discovery had errors: %s", report.rejected)

        # 3. Activate all registered plugins
        plugins = registry.get_all()
        for plugin in plugins:
            if plugin.should_activate(config):
                await plugin.initialize(config)
        ```
    """

    def __init__(self) -> None:
        """Initialize an empty plugin registry."""
        self._plugins: dict[str, ProtocolDomainPlugin] = {}

    def register(self, plugin: ProtocolDomainPlugin) -> None:
        """Register a domain plugin.

        Args:
            plugin: Plugin instance implementing ProtocolDomainPlugin.

        Raises:
            ValueError: If a plugin with the same ID is already registered.
        """
        plugin_id = plugin.plugin_id
        if plugin_id in self._plugins:
            raise ValueError(
                f"Plugin with ID '{plugin_id}' is already registered. "
                f"Each plugin must have a unique plugin_id."
            )
        self._plugins[plugin_id] = plugin
        logger.debug(
            "Registered domain plugin",
            extra={
                "plugin_id": plugin_id,
                "display_name": plugin.display_name,
            },
        )

    def get(self, plugin_id: str) -> ProtocolDomainPlugin | None:
        """Get a plugin by ID.

        Args:
            plugin_id: The plugin identifier.

        Returns:
            The plugin instance, or None if not found.
        """
        return self._plugins.get(plugin_id)

    def get_all(self) -> list[ProtocolDomainPlugin]:
        """Get all registered plugins.

        Returns:
            List of all registered plugin instances.
        """
        return list(self._plugins.values())

    def clear(self) -> None:
        """Clear all registered plugins (useful for testing)."""
        self._plugins.clear()

    def __len__(self) -> int:
        """Return number of registered plugins."""
        return len(self._plugins)

    def discover_from_entry_points(
        self,
        security_config: ModelSecurityConfig | None = None,
        *,
        group: str = DOMAIN_PLUGIN_ENTRY_POINT_GROUP,
        strict: bool = False,
    ) -> ModelPluginDiscoveryReport:
        """Discover and register plugins from PEP 621 entry points.

        Scans the specified entry-point group for plugin classes, validates
        them against the security namespace allowlist, instantiates them, and
        registers any that satisfy the ``ProtocolDomainPlugin`` protocol.

        Security is enforced **inside** this method. If ``security_config`` is
        ``None``, a default ``ModelSecurityConfig()`` is used which blocks all
        third-party namespaces. A bare call with no arguments is always secure.

        Already-registered plugins (from explicit ``register()`` calls) take
        precedence: if a discovered plugin has a ``plugin_id`` that already
        exists in the registry, the discovered plugin is silently skipped and
        recorded as ``"duplicate_skipped"`` in the report.

        Args:
            security_config: Security configuration controlling which
                namespaces are trusted for plugin loading. Defaults to
                ``ModelSecurityConfig()`` (only ``omnibase_core.`` and
                ``omnibase_infra.`` are trusted).
            group: Entry-point group name to scan. Defaults to
                ``DOMAIN_PLUGIN_ENTRY_POINT_GROUP``
                (``"onex.domain_plugins"``).
            strict: When ``True``, raise on the first import or
                instantiation error instead of recording it in the report.
                When ``False`` (default), errors are logged and recorded
                but processing continues.

        Returns:
            A ``ModelPluginDiscoveryReport`` containing all discovery
            outcomes, including accepted, rejected, and errored entries.

        Raises:
            ImportError: Only when ``strict=True`` and an entry point
                fails to load.
            TypeError: Only when ``strict=True`` and a loaded class
                fails to instantiate.
            RuntimeError: Only when ``strict=True`` and a loaded class
                does not satisfy ``ProtocolDomainPlugin``.

        Example:
            >>> registry = RegistryDomainPlugin()
            >>> report = registry.discover_from_entry_points()
            >>> for plugin_id in report.accepted:
            ...     print(f"Registered: {plugin_id}")

            >>> # With third-party plugins enabled
            >>> config = ModelSecurityConfig(
            ...     allow_third_party_plugins=True,
            ...     allowed_plugin_namespaces=(
            ...         "omnibase_core.",
            ...         "omnibase_infra.",
            ...         "mycompany.plugins.",
            ...     ),
            ... )
            >>> report = registry.discover_from_entry_points(
            ...     security_config=config,
            ... )
        """
        if security_config is None:
            security_config = ModelSecurityConfig()

        allowed_namespaces = security_config.get_effective_plugin_namespaces()
        active_packages = get_active_runtime_packages()

        # Retrieve entry points for the group
        eps = entry_points(group=group)

        # Sort deterministically by name then value for reproducible ordering
        sorted_eps = sorted(eps, key=lambda ep: (ep.name, ep.value))

        entries: list[ModelPluginDiscoveryEntry] = []
        accepted: list[str] = []

        for ep in sorted_eps:
            module_path = self._parse_module_path(ep.value)
            dist = getattr(ep, "dist", None)
            dist_name = getattr(dist, "name", "")
            if dist_name and not is_runtime_package_active(dist_name, active_packages):
                logger.debug(
                    "Skipping inactive runtime plugin entry point '%s' from package '%s'",
                    ep.name,
                    dist_name,
                )
                continue

            # Validate namespace BEFORE importing -- pre-import security
            if not self._validate_plugin_namespace(module_path, allowed_namespaces):
                logger.info(
                    "Plugin entry point namespace rejected: %s (module: %s)",
                    ep.name,
                    module_path,
                )
                entries.append(
                    ModelPluginDiscoveryEntry(
                        entry_point_name=ep.name,
                        module_path=module_path,
                        status="namespace_rejected",
                        reason=(
                            f"Module '{module_path}' is not in any trusted "
                            f"namespace: {allowed_namespaces}"
                        ),
                    )
                )
                continue

            # Load the entry point (import and resolve attribute)
            try:
                loaded_class = ep.load()
            except Exception as exc:
                msg = sanitize_error_message(exc)
                logger.warning(
                    "Failed to load plugin entry point '%s': %s",
                    ep.name,
                    msg,
                )
                entries.append(
                    ModelPluginDiscoveryEntry(
                        entry_point_name=ep.name,
                        module_path=module_path,
                        status="import_error",
                        reason=msg,
                    )
                )
                if strict:
                    raise ImportError(
                        f"Failed to load plugin entry point '{ep.name}': {msg}"
                    ) from exc
                continue

            # Instantiate the plugin (no-arg constructor)
            try:
                plugin = loaded_class()
            except Exception as exc:
                msg = sanitize_error_message(exc)
                logger.warning(
                    "Failed to instantiate plugin from entry point '%s': %s",
                    ep.name,
                    msg,
                )
                entries.append(
                    ModelPluginDiscoveryEntry(
                        entry_point_name=ep.name,
                        module_path=module_path,
                        status="instantiation_error",
                        reason=msg,
                    )
                )
                if strict:
                    raise TypeError(
                        f"Failed to instantiate plugin from entry point "
                        f"'{ep.name}': {msg}"
                    ) from exc
                continue

            # Protocol validation
            if not isinstance(plugin, ProtocolDomainPlugin):
                class_name = getattr(loaded_class, "__name__", repr(loaded_class))
                reason = f"Class '{class_name}' does not satisfy ProtocolDomainPlugin"
                logger.warning(
                    "Plugin from entry point '%s' failed protocol check: %s",
                    ep.name,
                    reason,
                )
                entries.append(
                    ModelPluginDiscoveryEntry(
                        entry_point_name=ep.name,
                        module_path=module_path,
                        status="protocol_invalid",
                        reason=reason,
                    )
                )
                if strict:
                    raise RuntimeError(f"Plugin from entry point '{ep.name}': {reason}")
                continue

            # Duplicate check -- explicit registrations win
            plugin_id = plugin.plugin_id
            if plugin_id in self._plugins:
                logger.debug(
                    "Discovered plugin '%s' from entry point '%s' "
                    "already registered (explicit wins), skipping",
                    plugin_id,
                    ep.name,
                )
                entries.append(
                    ModelPluginDiscoveryEntry(
                        entry_point_name=ep.name,
                        module_path=module_path,
                        status="duplicate_skipped",
                        plugin_id=plugin_id,
                        reason=(
                            f"Plugin ID '{plugin_id}' already registered "
                            f"(explicit registration takes precedence)"
                        ),
                    )
                )
                continue

            # Register the plugin
            self._plugins[plugin_id] = plugin
            accepted.append(plugin_id)
            logger.debug(
                "Discovered and registered plugin '%s' from entry point '%s'",
                plugin_id,
                ep.name,
                extra={
                    "plugin_id": plugin_id,
                    "entry_point": ep.name,
                    "module_path": module_path,
                },
            )
            entries.append(
                ModelPluginDiscoveryEntry(
                    entry_point_name=ep.name,
                    module_path=module_path,
                    status="accepted",
                    plugin_id=plugin_id,
                )
            )

        report = ModelPluginDiscoveryReport(
            group=group,
            discovered_count=len(sorted_eps),
            accepted=tuple(accepted),
            entries=tuple(entries),
        )

        logger.info(
            "Plugin discovery for group '%s': %d discovered, %d accepted, %d rejected",
            group,
            report.discovered_count,
            len(report.accepted),
            len(report.rejected),
        )

        return report

    @staticmethod
    def _validate_plugin_namespace(
        module_path: str,
        allowed_namespaces: tuple[str, ...],
    ) -> bool:
        """Validate a module path against the allowed namespace prefixes.

        Uses boundary-aware matching consistent with
        ``HandlerPluginLoader._validate_namespace()``: a namespace prefix
        ending with ``"."`` matches any submodule, while a prefix without a
        trailing dot requires the next character to be ``"."`` or end-of-string
        to prevent ``"foo"`` from matching ``"foobar.module"``.

        Args:
            module_path: Dotted module path to validate
                (e.g. ``"omnibase_infra.plugins.my_plugin"``).
            allowed_namespaces: Tuple of allowed namespace prefixes
                (e.g. ``("omnibase_core.", "omnibase_infra.")``).

        Returns:
            ``True`` if the module path matches at least one allowed
            namespace, ``False`` otherwise.

        Example:
            >>> RegistryDomainPlugin._validate_plugin_namespace(
            ...     "omnibase_infra.plugins.foo",
            ...     ("omnibase_core.", "omnibase_infra."),
            ... )
            True
            >>> RegistryDomainPlugin._validate_plugin_namespace(
            ...     "malicious.module",
            ...     ("omnibase_core.", "omnibase_infra."),
            ... )
            False
        """
        for namespace in allowed_namespaces:
            if module_path.startswith(namespace):
                # Namespace ends with "." -- already at package boundary
                if namespace.endswith("."):
                    return True
                # Otherwise ensure we are at a package boundary
                remaining = module_path[len(namespace) :]
                if remaining == "" or remaining.startswith("."):
                    return True
        return False

    @staticmethod
    def _parse_module_path(entry_point_value: str) -> str:
        """Extract the module path from an entry-point value string.

        Entry-point values follow the format ``"module.path:ClassName"``.
        This method returns the part before the colon.

        Args:
            entry_point_value: Entry-point value string
                (e.g. ``"omnibase_infra.plugins.foo:PluginFoo"``).

        Returns:
            The dotted module path
            (e.g. ``"omnibase_infra.plugins.foo"``).

        Example:
            >>> RegistryDomainPlugin._parse_module_path(
            ...     "omnibase_infra.plugins.foo:PluginFoo"
            ... )
            'omnibase_infra.plugins.foo'
        """
        if ":" in entry_point_value:
            return entry_point_value.split(":", 1)[0]
        return entry_point_value


__all__: list[str] = [
    "ModelDomainPluginConfig",
    "ModelDomainPluginResult",
    "ModelHandshakeResult",
    "ProtocolDomainPlugin",
    "RegistryDomainPlugin",
]
