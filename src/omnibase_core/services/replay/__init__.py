"""
Replay services module.

This module contains services for the replay infrastructure including:

- **InjectorRNG**: RNG injection for deterministic replay
- **InjectorTime**: Time injection for deterministic replay
- **InjectorUUID**: UUID injection for deterministic replay
- **RecorderEffect**: Effect recording and replay for determinism
- **ServiceReplaySafetyEnforcer**: Replay safety policy enforcement
- **ServiceAuditTrail**: Enforcement decision audit trail
- **ServiceConfigOverrideInjector**: Configuration override injection
- **ServiceEffectMockRegistry**: Mock registry for MOCKED policy level

Note: Following OMN-1071 policy, services are NOT exported at package level.
Import directly from the specific service module:

    from omnibase_core.services.replay.injector_rng import InjectorRNG
    from omnibase_core.services.replay.injector_time import InjectorTime
    from omnibase_core.services.replay.injector_uuid import InjectorUUID
    from omnibase_core.services.replay.recorder_effect import RecorderEffect
    from omnibase_core.services.replay.service_audit_trail import ServiceAuditTrail
    from omnibase_core.services.replay.service_config_override_injector import (
        ServiceConfigOverrideInjector,
    )
    from omnibase_core.services.replay.service_effect_mock_registry import (
        ServiceEffectMockRegistry,
    )
    from omnibase_core.services.replay.service_replay_safety_enforcer import (
        ServiceReplaySafetyEnforcer,
    )

Integration Guide:
    For detailed integration patterns, including recording/replaying effects,
    configuring enforcement modes, and troubleshooting, see:
    ``docs/guides/replay/REPLAY_SAFETY_INTEGRATION.md``

.. versionadded:: 0.4.0
    Added Replay Infrastructure (OMN-1116)
    Added Configuration Override Injection (OMN-1205)

.. versionadded:: 0.6.3
    Added InjectorUUID (OMN-1150)
    Added ServiceAuditTrail (OMN-1150)
    Added ServiceReplaySafetyEnforcer (OMN-1150)

.. versionadded:: 0.6.4
    Added ServiceEffectMockRegistry (OMN-1147)
"""

__all__: list[str] = []
