"""
Acknowledgment Type Enum.

Canonical enum for acknowledgment types used in discovery
and registration processes.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumAcknowledgmentType(StrValueHelper, str, Enum):
    """Canonical acknowledgment types for ONEX discovery."""

    BOOTSTRAP_ACK = "bootstrap_ack"
    DISCOVERY_ACK = "discovery_ack"
    REGISTRATION_ACK = "registration_ack"
    HEALTH_CHECK_ACK = "health_check_ack"
    SHUTDOWN_ACK = "shutdown_ack"
    UPDATE_ACK = "update_ack"
    ERROR_ACK = "error_ack"
