# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Handler Routing Subcontract Model — wrapper shape (OMN-12547 S-1c).

Simplified wrapper around ModelHandlerRoutingEntry (live 5-field shape).
Dead methods removed: build_routing_table (old routing_key/handler_key/priority shape),
get_all_handler_keys, validate_routing_configuration (routing_key duplication check),
validate_no_duplicate_handler_keys, validate_zero_code_requirements.

build_routing_table now derives discriminator keys from the 5-field live shape:
  - payload_type_match: entry.event_model.name
  - operation_match: entry.operation
  - topic_pattern: entry.event_type (pattern key for fnmatch)

Example YAML contract configuration:
    handler_routing:
      version:
        major: 1
        minor: 0
        patch: 0
      routing_strategy: payload_type_match
      handlers:
        - handler:
            name: HandlerUserCreated
            module: myapp.handlers.handler_user_created
          event_model:
            name: ModelUserCreatedEvent
            module: myapp.models
      default_handler: null
"""

from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_handler_routing_strategy import EnumHandlerRoutingStrategy
from omnibase_core.models.contracts.subcontracts.model_handler_routing_entry import (
    ModelHandlerRoutingEntry,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelHandlerRoutingSubcontract(BaseModel):
    """
    Handler routing configuration subcontract.

    Defines contract-driven routing configuration for nodes that need to
    dispatch messages to specific handlers. This subcontract enables
    MixinHandlerRouting to make routing decisions based on YAML contract
    configuration rather than hardcoded logic.

    Routing Strategies:
    - payload_type_match: Route based on event payload model class name.
      Used by ORCHESTRATOR nodes to dispatch events to appropriate handlers.
    - operation_match: Route based on operation field in the message.
      Used by EFFECT nodes to dispatch to appropriate I/O handlers.
    - topic_pattern: Route based on glob pattern matching against topic.
      Uses first-match-wins semantics: patterns (event_type field) are
      evaluated in list order.

    Example YAML configuration:
        handler_routing:
          version:
            major: 1
            minor: 0
            patch: 0
          routing_strategy: payload_type_match
          handlers:
            - handler:
                name: HandlerUserCreated
                module: myapp.handlers.handler_user_created
              event_model:
                name: ModelUserCreatedEvent
                module: myapp.models
          default_handler: null

    Strict typing is enforced: No Any types allowed in implementation.
    """

    model_config = ConfigDict(
        extra="ignore",  # Allow extra fields from YAML contracts
        use_enum_values=False,  # Keep enum objects, don't convert to strings
        validate_assignment=True,
        from_attributes=True,  # pytest-xdist compatibility
    )

    # Interface version for code generation stability
    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version (MUST be provided in YAML contract)",
    )

    routing_strategy: EnumHandlerRoutingStrategy = Field(
        default=EnumHandlerRoutingStrategy.PAYLOAD_TYPE_MATCH,
        description="Strategy for routing events to handlers",
    )

    handlers: list[ModelHandlerRoutingEntry] = Field(
        default_factory=list,
        description=(
            "List of handler routing entries defining routing rules. "
            "Entries are evaluated in list order."
        ),
    )

    default_handler: str | None = Field(
        default=None,
        description=(
            "Default handler registry key to use when no routing entries match. "
            "If None, unmatched messages may raise an error or be ignored "
            "depending on node implementation"
        ),
    )

    def build_routing_table(self) -> dict[str, list[str]]:
        """
        Build a routing table mapping discriminator keys to handler name lists.

        The discriminator key depends on the routing strategy:
        - payload_type_match: ``entry.event_model.name`` (Python class name)
        - operation_match: ``entry.operation`` (operation string)
        - topic_pattern: ``entry.event_type`` (glob pattern key for fnmatch)

        Handler name is always ``entry.handler.name`` (handler class name).
        Entries that lack the required discriminator for the active strategy
        are silently skipped.

        Returns:
            dict[str, list[str]]: Mapping of discriminator key to list of
                handler class names. Iteration order follows entry list order.
        """
        routing_table: dict[str, list[str]] = {}
        for entry in self.handlers:
            if self.routing_strategy == EnumHandlerRoutingStrategy.PAYLOAD_TYPE_MATCH:
                key: str | None = (
                    entry.event_model.name if entry.event_model is not None else None
                )
            elif self.routing_strategy == EnumHandlerRoutingStrategy.OPERATION_MATCH:
                key = entry.operation
            else:
                # TOPIC_PATTERN: use event_type as the fnmatch glob pattern key
                key = entry.event_type
            if key is None:
                continue
            handler_name = entry.handler.name
            if key not in routing_table:
                routing_table[key] = []
            routing_table[key].append(handler_name)
        return routing_table
