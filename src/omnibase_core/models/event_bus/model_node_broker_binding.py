# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The broker a node is reached on, as its contract overlay resolves it (OMN-22362)."""

from __future__ import annotations

from importlib.metadata import entry_points
from pathlib import Path
from typing import Final, Self

from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator

from omnibase_core.enums.enum_event_bus_type import EnumEventBusType
from omnibase_core.models.event_bus.model_node_broker_resolution_error import (
    ModelNodeBrokerResolutionError,
)

NODE_BROKER_RESOLVER_ENTRY_POINT_GROUP: Final[str] = "onex.node_broker_resolvers"


class ModelNodeBrokerBinding(BaseModel):
    """What a resolver answers for one node: the bus kind and, for a broker, how to dial it.

    ``kafka`` carries the lane's bootstrap address and its client transport.
    ``inmemory`` hosts the node in the caller's process and carries neither. The
    SASL password is a ``SecretStr`` so it never reaches a repr, a log line or an
    error message; :meth:`client_security` is the only place it is revealed.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    bus_type: EnumEventBusType
    overlay_path: Path = Field(
        description="The overlay file the declaration was read from."
    )
    lane: str | None = Field(
        default=None, description="The lane a kafka overlay names."
    )
    bootstrap_servers: str | None = Field(default=None, min_length=1)
    security_protocol: str | None = None
    sasl_mechanism: str | None = None
    sasl_username: str | None = None
    sasl_password: SecretStr | None = None

    @model_validator(mode="after")
    def _transport_matches_bus_type(self) -> Self:
        if self.bus_type.requires_broker:
            if not self.bootstrap_servers:
                raise ValueError(
                    f"a {self.bus_type.value} binding needs bootstrap_servers"
                )
        elif (
            self.lane is not None
            or self.bootstrap_servers is not None
            or self.security_protocol is not None
            or self.sasl_mechanism is not None
            or self.sasl_username is not None
            or self.sasl_password is not None
        ):
            raise ValueError(
                "an inmemory binding has no broker, so it carries no transport"
            )
        return self

    @classmethod
    def for_node(cls, node_id: str) -> Self:
        """The broker ``node_id`` is reached on, as its contract overlay declares it.

        ``omnibase_core`` must not import ``omnibase_infra`` (the layering ``RuntimeLocal``
        already honours for ``onex.backends``) and cannot read the lab lane declaration. The
        package that can registers a ``ProtocolNodeBrokerResolver`` under
        :data:`NODE_BROKER_RESOLVER_ENTRY_POINT_GROUP`. Exactly one provider may be installed:
        none leaves the node with no broker to dial, and two would let install order pick.
        The provider is checked structurally, since a new importer of the protocols package is
        refused by the import-layering ratchet.

        Raises:
            ModelNodeBrokerResolutionError: no or several providers, or the provider refuses.
        """
        providers = list(entry_points(group=NODE_BROKER_RESOLVER_ENTRY_POINT_GROUP))
        if not providers:
            raise ModelNodeBrokerResolutionError(
                "no node broker resolver is installed, so no broker can be read from the "
                "node's contract overlay. Install the package that registers one under "
                f"`{NODE_BROKER_RESOLVER_ENTRY_POINT_GROUP}` (omnibase_infra). The broker "
                "is never taken from the environment or a flag."
            )
        if len(providers) > 1:
            found = ", ".join(sorted(f"{ep.name} ({ep.value})" for ep in providers))
            raise ModelNodeBrokerResolutionError(
                f"more than one node broker resolver is registered ({found}); "
                "uninstall the extra provider so one declaration answers."
            )
        loaded = providers[0].load()
        resolver = loaded() if isinstance(loaded, type) else loaded
        resolve = getattr(resolver, "resolve_node_broker", None)
        if not callable(resolve):
            raise ModelNodeBrokerResolutionError(
                f"node broker resolver {providers[0].value!r} does not provide "
                "resolve_node_broker"
            )
        binding = resolve(node_id)
        if not isinstance(binding, cls):
            raise ModelNodeBrokerResolutionError(
                f"node broker resolver {providers[0].value!r} answered "
                f"{type(binding).__name__}, not {cls.__name__}"
            )
        return binding

    def client_security(self) -> dict[str, str]:
        """The librdkafka security settings for this binding; empty for a plaintext lane."""
        config: dict[str, str] = {}
        if self.security_protocol:
            config["security.protocol"] = self.security_protocol
        if self.sasl_mechanism:
            config["sasl.mechanism"] = self.sasl_mechanism
        if self.sasl_username:
            config["sasl.username"] = self.sasl_username
        if self.sasl_password is not None:
            config["sasl.password"] = self.sasl_password.get_secret_value()
        return config


__all__ = ["NODE_BROKER_RESOLVER_ENTRY_POINT_GROUP", "ModelNodeBrokerBinding"]
