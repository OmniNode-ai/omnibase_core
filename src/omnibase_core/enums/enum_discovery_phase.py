"""Discovery implementation phases for progressive rollout."""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumDiscoveryPhase(StrValueHelper, str, Enum):
    """Discovery implementation phases."""

    PHASE_1_SIMPLE = "phase_1_simple_discovery"
    PHASE_2_AUTO_PROVISION = "phase_2_auto_provisioning"
    PHASE_3_FULL_MESH = "phase_3_full_mesh"


__all__ = ["EnumDiscoveryPhase"]
