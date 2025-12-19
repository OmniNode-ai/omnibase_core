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
"""

# Topic Type Suffixes
TOPIC_TYPE_COMMANDS = "commands"
TOPIC_TYPE_EVENTS = "events"
TOPIC_TYPE_INTENTS = "intents"
TOPIC_TYPE_SNAPSHOTS = "snapshots"

# Domain Names
DOMAIN_REGISTRATION = "registration"
DOMAIN_DISCOVERY = "discovery"
DOMAIN_RUNTIME = "runtime"
DOMAIN_METRICS = "metrics"
DOMAIN_AUDIT = "audit"


def topic_name(domain: str, topic_type: str) -> str:
    """Generate standardized topic name: onex.<domain>.<type>."""
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

# Intent Publisher Topic (coordination)
# Note: This is the central intent topic used by MixinIntentPublisher
TOPIC_EVENT_PUBLISH_INTENT = topic_name(DOMAIN_RUNTIME, TOPIC_TYPE_INTENTS)

# Cleanup Policy Defaults
CLEANUP_POLICY_EVENTS = "delete"
CLEANUP_POLICY_SNAPSHOTS = "compact,delete"
CLEANUP_POLICY_COMMANDS = "delete"
CLEANUP_POLICY_INTENTS = "delete"

# Retention Defaults (milliseconds)
RETENTION_MS_DEFAULT = 604800000  # 7 days
RETENTION_MS_AUDIT = 2592000000  # 30 days

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
    # Special topics
    "TOPIC_EVENT_PUBLISH_INTENT",
    # Cleanup policies
    "CLEANUP_POLICY_EVENTS",
    "CLEANUP_POLICY_SNAPSHOTS",
    "CLEANUP_POLICY_COMMANDS",
    "CLEANUP_POLICY_INTENTS",
    # Retention
    "RETENTION_MS_DEFAULT",
    "RETENTION_MS_AUDIT",
]
