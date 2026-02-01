"""
ServiceReplaySafetyEnforcer - Runtime component for replay safety enforcement.

This module provides the default ProtocolReplaySafetyEnforcer implementation
for enforcing replay safety policies on non-deterministic effects.

Design:
    The enforcer integrates with the replay injectors (InjectorTime, InjectorRNG,
    InjectorUUID) and effect recorder (RecorderEffect) to classify effects and
    apply enforcement policies based on the configured mode.

Architecture:
    During pipeline execution, effects are classified as deterministic or
    non-deterministic. Non-deterministic effects are then handled according
    to the enforcement mode:
    - STRICT: Raises exception (for CI/testing)
    - WARN: Logs warning and continues (for migration)
    - PERMISSIVE: Allows with audit trail (for production)
    - MOCKED: Injects deterministic mocks (for testing)

Usage:
    .. code-block:: python

        from omnibase_core.services.replay.service_replay_safety_enforcer import (
            ServiceReplaySafetyEnforcer,
        )
        from omnibase_core.services.replay.injector_time import InjectorTime
        from omnibase_core.services.replay.injector_rng import InjectorRNG
        from omnibase_core.services.replay.injector_uuid import InjectorUUID
        from omnibase_core.enums.replay import EnumEnforcementMode
        from datetime import datetime, timezone

        # Create injectors for mocking
        time_injector = InjectorTime(
            fixed_time=datetime(2024, 6, 15, tzinfo=timezone.utc)
        )
        rng_injector = InjectorRNG(seed=42)
        uuid_injector = InjectorUUID()

        # Create enforcer in strict mode
        enforcer = ServiceReplaySafetyEnforcer(
            mode=EnumEnforcementMode.STRICT,
            time_injector=time_injector,
            rng_injector=rng_injector,
            uuid_injector=uuid_injector,
        )

        # Enforce policy on an effect
        decision = enforcer.enforce("time.now")
        # In strict mode, this would block the effect

Key Invariant:
    Same mode + same effect type -> Same enforcement decision (determinism)

Thread Safety:
    ServiceReplaySafetyEnforcer instances are NOT thread-safe.

    **Mutable State**: ``_audit_trail`` (list), injector references.

    **Recommended Patterns**:
        - Use separate instances per thread
        - Or wrap ``enforce()`` and ``get_audit_trail()`` calls with ``threading.Lock``

    See ``docs/guides/THREADING.md`` for comprehensive guidance.

Related:
    - OMN-1150: Replay Safety Enforcement
    - ProtocolReplaySafetyEnforcer: Protocol definition
    - InjectorTime: Time injection for mocking
    - InjectorRNG: RNG injection for mocking
    - InjectorUUID: UUID injection for mocking
    - RecorderEffect: Effect recording and replay

.. versionadded:: 0.6.3
"""

from __future__ import annotations

__all__ = ["ServiceReplaySafetyEnforcer"]

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.replay.enum_effect_determinism import EnumEffectDeterminism
from omnibase_core.enums.replay.enum_enforcement_mode import EnumEnforcementMode
from omnibase_core.enums.replay.enum_non_deterministic_source import (
    EnumNonDeterministicSource,
)
from omnibase_core.errors import ModelOnexError
from omnibase_core.models.replay.model_enforcement_decision import (
    ModelEnforcementDecision,
)
from omnibase_core.protocols.replay.protocol_replay_safety_enforcer import (
    ProtocolReplaySafetyEnforcer,
)
from omnibase_core.types.type_json import JsonType

if TYPE_CHECKING:
    from omnibase_core.protocols.protocol_logger_like import ProtocolLoggerLike
    from omnibase_core.services.replay.injector_rng import InjectorRNG
    from omnibase_core.services.replay.injector_time import InjectorTime
    from omnibase_core.services.replay.injector_uuid import InjectorUUID
    from omnibase_core.services.replay.recorder_effect import RecorderEffect

_logger = logging.getLogger(__name__)


# Effect type prefixes mapped to non-deterministic sources
_EFFECT_TYPE_MAPPINGS: dict[str, EnumNonDeterministicSource] = {
    # Time-based effects
    "time.": EnumNonDeterministicSource.TIME,
    "datetime.": EnumNonDeterministicSource.TIME,
    "clock.": EnumNonDeterministicSource.TIME,
    # Random effects
    "random.": EnumNonDeterministicSource.RANDOM,
    "secrets.": EnumNonDeterministicSource.RANDOM,
    "crypto.random": EnumNonDeterministicSource.RANDOM,
    # UUID effects
    "uuid.": EnumNonDeterministicSource.UUID,
    # Network effects
    "http.": EnumNonDeterministicSource.NETWORK,
    "https.": EnumNonDeterministicSource.NETWORK,
    "network.": EnumNonDeterministicSource.NETWORK,
    "socket.": EnumNonDeterministicSource.NETWORK,
    "api.": EnumNonDeterministicSource.NETWORK,
    "grpc.": EnumNonDeterministicSource.NETWORK,
    "websocket.": EnumNonDeterministicSource.NETWORK,
    # Database effects
    "db.": EnumNonDeterministicSource.DATABASE,
    "database.": EnumNonDeterministicSource.DATABASE,
    "sql.": EnumNonDeterministicSource.DATABASE,
    "query.": EnumNonDeterministicSource.DATABASE,
    "redis.": EnumNonDeterministicSource.DATABASE,
    "mongo.": EnumNonDeterministicSource.DATABASE,
    "postgres.": EnumNonDeterministicSource.DATABASE,
    "mysql.": EnumNonDeterministicSource.DATABASE,
    # Filesystem effects
    "file.": EnumNonDeterministicSource.FILESYSTEM,
    "fs.": EnumNonDeterministicSource.FILESYSTEM,
    "path.": EnumNonDeterministicSource.FILESYSTEM,
    "io.": EnumNonDeterministicSource.FILESYSTEM,
    # Environment effects
    "env.": EnumNonDeterministicSource.ENVIRONMENT,
    "environ.": EnumNonDeterministicSource.ENVIRONMENT,
    "config.": EnumNonDeterministicSource.ENVIRONMENT,
    "settings.": EnumNonDeterministicSource.ENVIRONMENT,
}

# Effect types that are explicitly deterministic
_DETERMINISTIC_PREFIXES: set[str] = {
    "compute.",
    "transform.",
    "parse.",
    "serialize.",
    "validate.",
    "hash.",
    "encode.",
    "decode.",
    "format.",
    "math.",
    "string.",
    "list.",
    "dict.",
    "set.",
    "sort.",
    "filter.",
    "map.",
    "reduce.",
}


class ServiceReplaySafetyEnforcer:
    """
    Runtime component for replay safety enforcement.

    Integrates with replay injectors and effect recorder to classify effects
    and enforce policies based on the configured mode.

    Args:
        mode: Enforcement mode. Defaults to STRICT for safety.
        time_injector: Optional time injector for TIME mocking.
        rng_injector: Optional RNG injector for RANDOM mocking.
        uuid_injector: Optional UUID injector for UUID mocking.
        effect_recorder: Optional effect recorder for NETWORK/DATABASE replay.
        logger: Optional logger for warnings. Uses module logger if None.
        max_audit_entries: Optional maximum audit trail entries to retain.
            When exceeded, oldest entries are evicted (FIFO). None means
            unlimited (default). For long-running services, set to 10000.

    Attributes:
        mode: The enforcement mode in effect.
        audit_count: Number of decisions in the audit trail.
        max_audit_entries: Maximum audit entries limit, or None if unlimited.

    Example:
        >>> from omnibase_core.services.replay.service_replay_safety_enforcer import (
        ...     ServiceReplaySafetyEnforcer,
        ... )
        >>> from omnibase_core.enums.replay import EnumEnforcementMode
        >>>
        >>> # Strict mode for CI
        >>> enforcer = ServiceReplaySafetyEnforcer(mode=EnumEnforcementMode.STRICT)
        >>> decision = enforcer.enforce("compute.hash")
        >>> decision.decision
        'allowed'
        >>>
        >>> # Permissive mode for production
        >>> enforcer = ServiceReplaySafetyEnforcer(mode=EnumEnforcementMode.PERMISSIVE)
        >>> decision = enforcer.enforce("http.get")
        >>> decision.decision
        'allowed'

    Integration:
        **With ServiceAuditTrail**:

        For detailed audit logging, combine the enforcer with ServiceAuditTrail:

        .. code-block:: python

            from omnibase_core.services.replay.service_replay_safety_enforcer import (
                ServiceReplaySafetyEnforcer,
            )
            from omnibase_core.services.replay.service_audit_trail import ServiceAuditTrail
            from omnibase_core.enums.replay import EnumEnforcementMode

            enforcer = ServiceReplaySafetyEnforcer(mode=EnumEnforcementMode.PERMISSIVE)
            audit_trail = ServiceAuditTrail()

            # Record enforcement decisions in the audit trail
            decision = enforcer.enforce("http.get", {"url": "https://api.example.com"})
            entry = audit_trail.record(decision, context={"handler": "api_fetch"})

            # Query and analyze decisions
            blocked = audit_trail.get_entries(outcome="blocked")
            summary = audit_trail.get_summary()

        **With Pipeline Execution**:

        The enforcer is typically used within EFFECT nodes to validate operations
        before execution:

        .. code-block:: python

            class NodeApiCallEffect(NodeEffect):
                def __init__(
                    self,
                    container: ModelONEXContainer,
                    enforcer: ServiceReplaySafetyEnforcer,
                ):
                    super().__init__(container)
                    self._enforcer = enforcer

                async def execute_effect(
                    self,
                    ctx: ProtocolPipelineContext,
                ) -> dict[str, Any]:
                    # Enforce replay safety before making API call
                    decision = self._enforcer.enforce(
                        "http.get",
                        {"url": self._url},
                    )

                    if decision.decision == "blocked":
                        raise RuntimeError(f"Effect blocked: {decision.reason}")

                    if decision.decision == "mocked":
                        return decision.mocked_value

                    # Proceed with actual API call
                    return await self._make_api_call()

        **Mode Selection Guide**:

        Choose the appropriate mode based on your use case:

        - **STRICT**: For CI/CD pipelines and integration tests where all
          non-deterministic effects must be controlled. Raises exceptions
          on any non-deterministic effect.

        - **WARN**: For migration phases when adding replay safety to existing
          code. Logs warnings but allows execution to continue.

        - **PERMISSIVE**: For production environments where full audit logging
          is needed but execution should not be blocked. Records all decisions.

        - **MOCKED**: For unit tests and deterministic replay where all
          non-deterministic effects should be automatically replaced with
          mock values from the configured injectors.

        **With Dependency Injection Container**:

        Register the enforcer as a service for container-based resolution:

        .. code-block:: python

            from omnibase_core.models.container.model_onex_container import (
                ModelONEXContainer,
            )

            # Create container with replay services
            container = ModelONEXContainer()
            container.register_service(
                "ProtocolReplaySafetyEnforcer",
                ServiceReplaySafetyEnforcer(
                    mode=EnumEnforcementMode.MOCKED,
                    time_injector=time_injector,
                    rng_injector=rng_injector,
                    uuid_injector=uuid_injector,
                ),
            )

            # Resolve in nodes
            class MyNode(NodeEffect):
                def __init__(self, container: ModelONEXContainer):
                    super().__init__(container)
                    self._enforcer = container.get_service(
                        "ProtocolReplaySafetyEnforcer"
                    )

    Memory Characteristics:
        Without ``max_audit_entries``: Grows unbounded (O(n) memory where n = decisions).
        With ``max_audit_entries``: Bounded to O(max_audit_entries) memory.

        Decision size: ~200-500 bytes per decision (varies with metadata).

        Recommended limits:
            - Long-running services: 10,000 entries (~2-5 MB)
            - Memory-constrained: 1,000 entries (~0.2-0.5 MB)
            - High-volume pipelines: Consider external audit storage

    Thread Safety:
        NOT thread-safe. Mutable state: ``_audit_trail`` list.
        Use separate instances per thread or synchronize access.
        See ``docs/guides/THREADING.md``.

    See Also:
        - :class:`ServiceAuditTrail`: Detailed audit logging and query.
        - :class:`InjectorTime`: Time injection for mocking.
        - :class:`InjectorRNG`: RNG injection for mocking.
        - :class:`InjectorUUID`: UUID injection for mocking.
        - :class:`RecorderEffect`: Effect recording for network/database replay.

    .. versionadded:: 0.6.3
    """

    def __init__(
        self,
        mode: EnumEnforcementMode = EnumEnforcementMode.STRICT,
        time_injector: InjectorTime | None = None,
        rng_injector: InjectorRNG | None = None,
        uuid_injector: InjectorUUID | None = None,
        effect_recorder: RecorderEffect | None = None,
        logger: ProtocolLoggerLike | None = None,
        max_audit_entries: int | None = None,
    ) -> None:
        """
        Initialize the replay safety enforcer.

        Args:
            mode: Enforcement mode. Defaults to STRICT.
            time_injector: Time injector for mocking time effects.
            rng_injector: RNG injector for mocking random effects.
            uuid_injector: UUID injector for mocking UUID effects.
            effect_recorder: Effect recorder for network/db replay.
            logger: Logger for warnings. Uses module logger if None.
            max_audit_entries: Optional maximum audit trail entries to retain.
                When exceeded, oldest entries are evicted (FIFO). None means
                unlimited (default). For long-running services, set to 10000.
        """
        self._mode = mode
        self._time_injector = time_injector
        self._rng_injector = rng_injector
        self._uuid_injector = uuid_injector
        self._effect_recorder = effect_recorder
        self._logger = logger
        self._max_audit_entries = max_audit_entries
        self._audit_trail: list[ModelEnforcementDecision] = []

    @property
    def mode(self) -> EnumEnforcementMode:
        """
        Return the enforcement mode.

        Returns:
            EnumEnforcementMode: The current enforcement mode.

        Example:
            >>> enforcer = ServiceReplaySafetyEnforcer(mode=EnumEnforcementMode.WARN)
            >>> enforcer.mode
            <EnumEnforcementMode.WARN: 'warn'>
        """
        return self._mode

    @property
    def max_audit_entries(self) -> int | None:
        """
        Return the maximum audit entries limit, or None if unlimited.

        Returns:
            int | None: The maximum number of audit entries to retain, or None
                if unlimited.

        Example:
            >>> enforcer = ServiceReplaySafetyEnforcer(max_audit_entries=1000)
            >>> enforcer.max_audit_entries
            1000
            >>> enforcer_unlimited = ServiceReplaySafetyEnforcer()
            >>> enforcer_unlimited.max_audit_entries is None
            True
        """
        return self._max_audit_entries

    def _enforce_audit_limit(self) -> None:
        """
        Enforce max_audit_entries limit with FIFO eviction.

        Called after each decision is appended to the audit trail.
        Evicts oldest entries when the limit is exceeded.
        """
        if (
            self._max_audit_entries is not None
            and len(self._audit_trail) > self._max_audit_entries
        ):
            evict_count = len(self._audit_trail) - self._max_audit_entries
            self._audit_trail = self._audit_trail[evict_count:]

    def _log_warning(
        self, message: str, extra: dict[str, object] | None = None
    ) -> None:
        """Log a warning using the configured logger or module logger."""
        if self._logger is not None:
            self._logger.warning(message, extra=extra)
        else:
            _logger.warning(message, extra=extra or {})

    def classify_effect(
        self,
        effect_type: str,
        effect_metadata: dict[str, JsonType] | None = None,
    ) -> tuple[EnumEffectDeterminism, EnumNonDeterministicSource | None]:
        """
        Classify an effect as deterministic or non-deterministic.

        Uses prefix matching to classify effects:
        - Effects starting with deterministic prefixes are DETERMINISTIC
        - Effects matching non-deterministic prefixes are NON_DETERMINISTIC
        - Unknown effects are classified as UNKNOWN

        Args:
            effect_type: Type identifier for the effect (e.g., "http.get",
                "time.now", "random.randint").
            effect_metadata: Optional metadata about the effect. Currently
                unused but reserved for future context-aware classification.

        Returns:
            tuple[EnumEffectDeterminism, EnumNonDeterministicSource | None]:
                A tuple of (determinism classification, source of non-determinism).
                The source is None for deterministic or unknown effects.

        Example:
            >>> enforcer = ServiceReplaySafetyEnforcer()
            >>> enforcer.classify_effect("time.now")
            (<EnumEffectDeterminism.NON_DETERMINISTIC: ...>,
             <EnumNonDeterministicSource.TIME: ...>)
            >>> enforcer.classify_effect("compute.hash")
            (<EnumEffectDeterminism.DETERMINISTIC: ...>, None)
        """
        effect_type_lower = effect_type.lower()

        # Check for explicitly deterministic effects first
        for prefix in _DETERMINISTIC_PREFIXES:
            if effect_type_lower.startswith(prefix):
                return EnumEffectDeterminism.DETERMINISTIC, None

        # Check for non-deterministic effects
        for prefix, source in _EFFECT_TYPE_MAPPINGS.items():
            if effect_type_lower.startswith(prefix):
                return EnumEffectDeterminism.NON_DETERMINISTIC, source

        # Unknown effects - cannot determine statically
        return EnumEffectDeterminism.UNKNOWN, None

    def enforce(
        self,
        effect_type: str,
        effect_metadata: dict[str, JsonType] | None = None,
    ) -> ModelEnforcementDecision:
        """
        Enforce replay safety policy for an effect.

        Classifies the effect and applies the enforcement policy based on
        the configured mode. The decision is recorded in the audit trail.

        Args:
            effect_type: Type identifier for the effect.
            effect_metadata: Optional metadata about the effect.

        Returns:
            ModelEnforcementDecision: The enforcement decision.

        Raises:
            ModelOnexError: If mode is STRICT and effect is non-deterministic.

        Example:
            >>> enforcer = ServiceReplaySafetyEnforcer(mode=EnumEnforcementMode.PERMISSIVE)
            >>> decision = enforcer.enforce("http.get")
            >>> decision.decision
            'allowed'
        """
        timestamp = datetime.now(UTC)
        determinism, source = self.classify_effect(effect_type, effect_metadata)

        # Deterministic effects are always allowed
        if determinism == EnumEffectDeterminism.DETERMINISTIC:
            decision = ModelEnforcementDecision(
                effect_type=effect_type,
                determinism=determinism,
                source=None,
                mode=self._mode,
                decision="allowed",
                reason="Effect is deterministic",
                timestamp=timestamp,
            )
            self._audit_trail.append(decision)
            self._enforce_audit_limit()
            return decision

        # Unknown effects - handle based on mode (treat as potentially non-deterministic)
        if determinism == EnumEffectDeterminism.UNKNOWN:
            return self._handle_unknown_effect(effect_type, timestamp)

        # Non-deterministic effects - apply enforcement policy
        return self._handle_non_deterministic_effect(
            effect_type, determinism, source, timestamp
        )

    def _handle_unknown_effect(
        self,
        effect_type: str,
        timestamp: datetime,
    ) -> ModelEnforcementDecision:
        """Handle unknown effects based on enforcement mode."""
        if self._mode == EnumEnforcementMode.STRICT:
            decision = ModelEnforcementDecision(
                effect_type=effect_type,
                determinism=EnumEffectDeterminism.UNKNOWN,
                source=None,
                mode=self._mode,
                decision="blocked",
                reason=(
                    "Unknown effect type cannot be verified as deterministic "
                    "in strict mode"
                ),
                timestamp=timestamp,
            )
            self._audit_trail.append(decision)
            self._enforce_audit_limit()
            raise ModelOnexError(
                message=f"Unknown effect '{effect_type}' blocked in strict mode",
                error_code=EnumCoreErrorCode.REPLAY_ENFORCEMENT_BLOCKED,
                effect_type=effect_type,
                mode=self._mode.value,
            )

        if self._mode == EnumEnforcementMode.WARN:
            decision = ModelEnforcementDecision(
                effect_type=effect_type,
                determinism=EnumEffectDeterminism.UNKNOWN,
                source=None,
                mode=self._mode,
                decision="warned",
                reason="Unknown effect type - cannot verify determinism",
                timestamp=timestamp,
            )
            self._audit_trail.append(decision)
            self._enforce_audit_limit()
            self._log_warning(
                f"Unknown effect type '{effect_type}' - cannot verify determinism",
                extra={"effect_type": effect_type},
            )
            return decision

        # PERMISSIVE or MOCKED - allow with audit
        decision = ModelEnforcementDecision(
            effect_type=effect_type,
            determinism=EnumEffectDeterminism.UNKNOWN,
            source=None,
            mode=self._mode,
            decision="allowed",
            reason="Unknown effect allowed in permissive/mocked mode",
            timestamp=timestamp,
        )
        self._audit_trail.append(decision)
        self._enforce_audit_limit()
        return decision

    def _handle_non_deterministic_effect(
        self,
        effect_type: str,
        determinism: EnumEffectDeterminism,
        source: EnumNonDeterministicSource | None,
        timestamp: datetime,
    ) -> ModelEnforcementDecision:
        """Handle non-deterministic effects based on enforcement mode."""
        if source is None:
            source_desc = "unknown source"
        else:
            source_desc = source.value

        if self._mode == EnumEnforcementMode.STRICT:
            decision = ModelEnforcementDecision(
                effect_type=effect_type,
                determinism=determinism,
                source=source,
                mode=self._mode,
                decision="blocked",
                reason=(
                    f"Non-deterministic effect ({source_desc}) blocked in strict mode"
                ),
                timestamp=timestamp,
            )
            self._audit_trail.append(decision)
            self._enforce_audit_limit()
            raise ModelOnexError(
                message=(
                    f"Non-deterministic effect '{effect_type}' ({source_desc}) "
                    f"blocked in strict mode"
                ),
                error_code=EnumCoreErrorCode.REPLAY_ENFORCEMENT_BLOCKED,
                effect_type=effect_type,
                source=source_desc,
                mode=self._mode.value,
            )

        if self._mode == EnumEnforcementMode.WARN:
            decision = ModelEnforcementDecision(
                effect_type=effect_type,
                determinism=determinism,
                source=source,
                mode=self._mode,
                decision="warned",
                reason=f"Non-deterministic effect ({source_desc}) - logged warning",
                timestamp=timestamp,
            )
            self._audit_trail.append(decision)
            self._enforce_audit_limit()
            self._log_warning(
                f"Non-deterministic effect '{effect_type}' ({source_desc})",
                extra={"effect_type": effect_type, "source": source_desc},
            )
            return decision

        if self._mode == EnumEnforcementMode.PERMISSIVE:
            decision = ModelEnforcementDecision(
                effect_type=effect_type,
                determinism=determinism,
                source=source,
                mode=self._mode,
                decision="allowed",
                reason=f"Non-deterministic effect ({source_desc}) allowed with audit",
                timestamp=timestamp,
            )
            self._audit_trail.append(decision)
            self._enforce_audit_limit()
            return decision

        # MOCKED mode - inject deterministic mock
        mock_value = self.get_mock_value(source) if source else None
        decision = ModelEnforcementDecision(
            effect_type=effect_type,
            determinism=determinism,
            source=source,
            mode=self._mode,
            decision="mocked",
            reason=f"Non-deterministic effect ({source_desc}) mocked",
            timestamp=timestamp,
            mock_injected=True,
            mocked_value=mock_value,
        )
        self._audit_trail.append(decision)
        self._enforce_audit_limit()
        return decision

    def get_mock_value(
        self,
        source: EnumNonDeterministicSource,
    ) -> Any:
        """
        Get mocked value for a non-deterministic source.

        Returns a deterministic mock value appropriate for the source type.
        Uses the configured injectors when available.

        Args:
            source: The source of non-determinism to mock.

        Returns:
            Any: A deterministic mock value appropriate for the source.

        Example:
            >>> from datetime import datetime, timezone
            >>> from omnibase_core.services.replay.injector_time import InjectorTime
            >>> time_injector = InjectorTime(
            ...     fixed_time=datetime(2024, 6, 15, tzinfo=timezone.utc)
            ... )
            >>> enforcer = ServiceReplaySafetyEnforcer(time_injector=time_injector)
            >>> enforcer.get_mock_value(EnumNonDeterministicSource.TIME)
            datetime.datetime(2024, 6, 15, 0, 0, tzinfo=datetime.timezone.utc)
        """
        if source == EnumNonDeterministicSource.TIME:
            if self._time_injector is not None:
                return self._time_injector.now()
            # Return deterministic Unix epoch when no injector provided.
            # This is clearly recognizable as a mock value.
            # For proper replay control, configure a time_injector with fixed_time.
            return datetime(1970, 1, 1, tzinfo=UTC)

        elif source == EnumNonDeterministicSource.RANDOM:
            if self._rng_injector is not None:
                return self._rng_injector.random()
            return 0.5  # Default deterministic value

        elif source == EnumNonDeterministicSource.UUID:
            if self._uuid_injector is not None:
                return self._uuid_injector.uuid4()
            # Return a fixed deterministic UUID
            return UUID("00000000-0000-4000-8000-000000000000")

        elif source == EnumNonDeterministicSource.NETWORK:
            # Network effects require recorded data from effect recorder
            # Return empty dict as placeholder
            return {}

        elif source == EnumNonDeterministicSource.DATABASE:
            # Database effects require recorded data from effect recorder
            # Return empty dict as placeholder
            return {}

        elif source == EnumNonDeterministicSource.FILESYSTEM:
            # Filesystem reads return empty string as placeholder
            return ""

        else:
            # ENVIRONMENT or any future enum values
            # Environment variables return empty string as placeholder
            return ""

    def get_audit_trail(self) -> list[ModelEnforcementDecision]:
        """
        Get all enforcement decisions made.

        Returns a copy of the audit trail to prevent external modification.

        Returns:
            list[ModelEnforcementDecision]: Copy of all enforcement decisions.

        Example:
            >>> enforcer = ServiceReplaySafetyEnforcer(mode=EnumEnforcementMode.PERMISSIVE)
            >>> _ = enforcer.enforce("time.now")
            >>> _ = enforcer.enforce("compute.hash")
            >>> trail = enforcer.get_audit_trail()
            >>> len(trail)
            2
        """
        return list(self._audit_trail)

    def reset(self) -> None:
        """
        Reset enforcer state for new replay session.

        Clears the audit trail. Injector state is not reset (caller should
        reset injectors separately if needed).

        Example:
            >>> enforcer = ServiceReplaySafetyEnforcer()
            >>> _ = enforcer.enforce("time.now", {})
            >>> len(enforcer.get_audit_trail())
            1
            >>> enforcer.reset()
            >>> len(enforcer.get_audit_trail())
            0
        """
        self._audit_trail.clear()

    @property
    def audit_count(self) -> int:
        """
        Return the number of decisions in the audit trail.

        Returns:
            int: Number of enforcement decisions recorded.

        Example:
            >>> enforcer = ServiceReplaySafetyEnforcer(mode=EnumEnforcementMode.PERMISSIVE)
            >>> enforcer.audit_count
            0
            >>> _ = enforcer.enforce("time.now")
            >>> enforcer.audit_count
            1
        """
        return len(self._audit_trail)


# Verify protocol compliance at module load time
_enforcer_check: ProtocolReplaySafetyEnforcer = ServiceReplaySafetyEnforcer()
