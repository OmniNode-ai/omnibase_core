"""
ONEX Topic Taxonomy Constants.

Standardized topic naming per OMN-939. All topic strings should use
these constants instead of ad-hoc strings.

Topic Format: onex.<domain>.<type>

Types:
- commands: Write requests/commands
- events: Immutable event logs
- intents: Coordination intents
- snapshots: Compacted state snapshots

Thread Safety:
    All constants in this module are immutable strings and thread-safe.
    The topic_name() function is pure and thread-safe.
"""

import re

# Topic Type Suffixes
TOPIC_TYPE_COMMANDS = "commands"
TOPIC_TYPE_EVENTS = "events"
TOPIC_TYPE_INTENTS = "intents"
TOPIC_TYPE_SNAPSHOTS = "snapshots"

# Valid topic types set for validation
_VALID_TOPIC_TYPES = frozenset(
    {TOPIC_TYPE_COMMANDS, TOPIC_TYPE_EVENTS, TOPIC_TYPE_INTENTS, TOPIC_TYPE_SNAPSHOTS}
)

# Domain validation pattern: lowercase alphanumeric with hyphens, starting with letter,
# cannot end with hyphen (must end with letter or digit, or be single letter)
_DOMAIN_PATTERN = re.compile(r"^[a-z][a-z0-9-]*[a-z0-9]$|^[a-z]$")

# Domain Names
DOMAIN_REGISTRATION = "registration"
DOMAIN_DISCOVERY = "discovery"
DOMAIN_RUNTIME = "runtime"
DOMAIN_METRICS = "metrics"
DOMAIN_AUDIT = "audit"


def topic_name(domain: str, topic_type: str) -> str:
    """
    Generate standardized topic name: onex.<domain>.<type>.

    Args:
        domain: Domain name (lowercase alphanumeric with hyphens, starting with letter).
        topic_type: Topic type (commands, events, intents, or snapshots).

    Returns:
        Full topic name in format onex.<domain>.<type>.

    Raises:
        ValueError: If domain or topic_type is invalid.

    Examples:
        >>> topic_name("registration", "events")
        'onex.registration.events'
        >>> topic_name("my-service", "commands")
        'onex.my-service.commands'
    """
    if not domain:
        # error-ok: ValueError is standard for input validation in constants modules
        raise ValueError("Domain cannot be empty")
    if not _DOMAIN_PATTERN.match(domain):
        # error-ok: ValueError is standard for input validation in constants modules
        raise ValueError(
            f"Invalid domain '{domain}': must be lowercase alphanumeric with hyphens, "
            "starting with a letter, cannot end with hyphen "
            "(pattern: ^[a-z][a-z0-9-]*[a-z0-9]$|^[a-z]$)"
        )
    if topic_type not in _VALID_TOPIC_TYPES:
        # error-ok: ValueError is standard for input validation in constants modules
        raise ValueError(
            f"Invalid topic_type '{topic_type}': must be one of {sorted(_VALID_TOPIC_TYPES)}"
        )
    return f"onex.{domain}.{topic_type}"


# Registration Domain Topics
TOPIC_REGISTRATION_COMMANDS = topic_name(DOMAIN_REGISTRATION, TOPIC_TYPE_COMMANDS)
TOPIC_REGISTRATION_EVENTS = topic_name(DOMAIN_REGISTRATION, TOPIC_TYPE_EVENTS)
TOPIC_REGISTRATION_INTENTS = topic_name(DOMAIN_REGISTRATION, TOPIC_TYPE_INTENTS)
TOPIC_REGISTRATION_SNAPSHOTS = topic_name(DOMAIN_REGISTRATION, TOPIC_TYPE_SNAPSHOTS)

# Discovery Domain Topics (migrate from onex.discovery.broadcast/response)
TOPIC_DISCOVERY_COMMANDS = topic_name(DOMAIN_DISCOVERY, TOPIC_TYPE_COMMANDS)
TOPIC_DISCOVERY_EVENTS = topic_name(DOMAIN_DISCOVERY, TOPIC_TYPE_EVENTS)
TOPIC_DISCOVERY_INTENTS = topic_name(DOMAIN_DISCOVERY, TOPIC_TYPE_INTENTS)

# Runtime Domain Topics
TOPIC_RUNTIME_COMMANDS = topic_name(DOMAIN_RUNTIME, TOPIC_TYPE_COMMANDS)
TOPIC_RUNTIME_EVENTS = topic_name(DOMAIN_RUNTIME, TOPIC_TYPE_EVENTS)
TOPIC_RUNTIME_INTENTS = topic_name(DOMAIN_RUNTIME, TOPIC_TYPE_INTENTS)

# Metrics Domain Topics
TOPIC_METRICS_EVENTS = topic_name(DOMAIN_METRICS, TOPIC_TYPE_EVENTS)
TOPIC_METRICS_INTENTS = topic_name(DOMAIN_METRICS, TOPIC_TYPE_INTENTS)

# Intent Publisher Topic (coordination)
# Note: This is the central intent topic used by MixinIntentPublisher
TOPIC_EVENT_PUBLISH_INTENT = topic_name(DOMAIN_RUNTIME, TOPIC_TYPE_INTENTS)

# Cleanup Policy Defaults
CLEANUP_POLICY_EVENTS = "delete"
CLEANUP_POLICY_SNAPSHOTS = "compact,delete"
CLEANUP_POLICY_COMMANDS = "delete"
CLEANUP_POLICY_INTENTS = "delete"

# Retention Defaults (milliseconds) - per ONEX topic taxonomy standard
RETENTION_MS_COMMANDS = 604800000  # 7 days
RETENTION_MS_EVENTS = 2592000000  # 30 days
RETENTION_MS_INTENTS = 86400000  # 1 day (short-lived coordination)
RETENTION_MS_SNAPSHOTS = 604800000  # 7 days
RETENTION_MS_AUDIT = 2592000000  # 30 days (same as events for audit trails)

__all__ = [
    # Type suffixes
    "TOPIC_TYPE_COMMANDS",
    "TOPIC_TYPE_EVENTS",
    "TOPIC_TYPE_INTENTS",
    "TOPIC_TYPE_SNAPSHOTS",
    # Domains
    "DOMAIN_REGISTRATION",
    "DOMAIN_DISCOVERY",
    "DOMAIN_RUNTIME",
    "DOMAIN_METRICS",
    "DOMAIN_AUDIT",
    # Generator
    "topic_name",
    # Registration topics
    "TOPIC_REGISTRATION_COMMANDS",
    "TOPIC_REGISTRATION_EVENTS",
    "TOPIC_REGISTRATION_INTENTS",
    "TOPIC_REGISTRATION_SNAPSHOTS",
    # Discovery topics
    "TOPIC_DISCOVERY_COMMANDS",
    "TOPIC_DISCOVERY_EVENTS",
    "TOPIC_DISCOVERY_INTENTS",
    # Runtime topics
    "TOPIC_RUNTIME_COMMANDS",
    "TOPIC_RUNTIME_EVENTS",
    "TOPIC_RUNTIME_INTENTS",
    # Metrics topics
    "TOPIC_METRICS_EVENTS",
    "TOPIC_METRICS_INTENTS",
    # Special topics
    "TOPIC_EVENT_PUBLISH_INTENT",
    # Cleanup policies
    "CLEANUP_POLICY_EVENTS",
    "CLEANUP_POLICY_SNAPSHOTS",
    "CLEANUP_POLICY_COMMANDS",
    "CLEANUP_POLICY_INTENTS",
    # Retention
    "RETENTION_MS_COMMANDS",
    "RETENTION_MS_EVENTS",
    "RETENTION_MS_INTENTS",
    "RETENTION_MS_SNAPSHOTS",
    "RETENTION_MS_AUDIT",
]
