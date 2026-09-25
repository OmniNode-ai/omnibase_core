# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The runtime lanes a node contract may attach on (OMN-19408).

Declared as a top-level ``runtime_lanes`` list in ``contract.yaml``. The
omnibase_infra auto-wiring loader parses it into this model and attaches the
node only on a runtime whose declared lane (``ONEX_RUNTIME_LANE``) is one of
these. A contract that omits the field is unscoped and attaches wherever its
runtime profile owns it, exactly as before.
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.constants.constants_runtime_lanes import REGISTERED_RUNTIME_LANES

__all__ = ["ModelRuntimeLaneScope"]


class ModelRuntimeLaneScope(BaseModel):
    """The closed set of runtime lanes a node is allowed to attach on."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    lanes: tuple[str, ...] = Field(
        ...,
        min_length=1,
        description=(
            "Runtime lanes this node attaches on, each a member of "
            "REGISTERED_RUNTIME_LANES. Lower-cased and de-duplicated in "
            "declaration order. Never empty: an empty scope would detach the "
            "node on every lane, and the way to say 'any lane' is to omit "
            "runtime_lanes."
        ),
    )

    @field_validator("lanes", mode="before")
    @classmethod
    def _normalize_and_register(cls, value: object) -> tuple[str, ...]:
        if isinstance(value, str):
            raw_values: tuple[object, ...] = (value,)
        elif isinstance(value, (list, tuple)):
            raw_values = tuple(value)
        else:
            raise ValueError("runtime_lanes must be a string or a list of strings")

        lanes: list[str] = []
        for raw in raw_values:
            if not isinstance(raw, str):
                raise ValueError("runtime_lanes entries must be strings")
            lane = raw.strip().lower()
            if not lane:
                raise ValueError("runtime_lanes entries cannot be blank")
            lanes.append(lane)

        unregistered = sorted(set(lanes) - REGISTERED_RUNTIME_LANES)
        if unregistered:
            raise ValueError(
                f"runtime_lanes names lane(s) {unregistered} that are not "
                f"registered runtime lanes {sorted(REGISTERED_RUNTIME_LANES)}; "
                "a node scoped to a lane no runtime can declare is detached "
                "everywhere"
            )
        return tuple(dict.fromkeys(lanes))

    def admits(self, runtime_lane: str | None) -> bool:
        """Return whether a runtime declaring ``runtime_lane`` may attach this node.

        ``None`` (a runtime that declared no lane, or an unregistered one) is
        never admitted. Whether that is an error is the loader's decision.
        """
        if not runtime_lane:
            return False
        return runtime_lane.strip().lower() in self.lanes
