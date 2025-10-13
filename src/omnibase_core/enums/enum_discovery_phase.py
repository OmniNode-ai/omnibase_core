from enum import Enum


class EnumDiscoveryPhase(str, Enum):
    """Discovery implementation phases."""

    PHASE_1_SIMPLE = "phase_1_simple_discovery"
    PHASE_2_AUTO_PROVISION = "phase_2_auto_provisioning"
    PHASE_3_FULL_MESH = "phase_3_full_mesh"
