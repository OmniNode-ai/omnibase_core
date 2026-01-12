# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Replay services module.

This module contains services for the replay infrastructure including:

- **ServiceRNGInjector**: RNG injection for deterministic replay
- **ServiceTimeInjector**: Time injection for deterministic replay
- **ServiceEffectRecorder**: Effect recording and replay for determinism
- **ServiceConfigOverrideInjector**: Configuration override injection

Note: Following OMN-1071 policy, services are NOT exported at package level.
Import directly from the specific service module:

    from omnibase_core.services.replay.service_rng_injector import ServiceRNGInjector
    from omnibase_core.services.replay.service_time_injector import ServiceTimeInjector
    from omnibase_core.services.replay.service_effect_recorder import ServiceEffectRecorder
    from omnibase_core.services.replay.service_config_override_injector import (
        ServiceConfigOverrideInjector,
    )

.. versionadded:: 0.4.0
    Added Replay Infrastructure (OMN-1116)
    Added Configuration Override Injection (OMN-1205)
"""

__all__: list[str] = []
