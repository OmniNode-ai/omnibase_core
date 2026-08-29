# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Status grid widget configuration model.

The config behind the system-health board (plan D4). OMN-16884 replaced its
``status_colors`` hex map with semantic **severity roles**: a config that carries
presentation colours has already made the decision the theme contract exists to
make, and its own docstring forbade it ("must never hard-code token values").
The colours now come from the active theme instance (OMN-16882) by token name.

Severity is never conveyed by colour alone — every role carries a distinct text
label and a distinct icon, so the board stays readable for a colourblind
operator and in a screenshot pasted into a monochrome channel.

Ordering and summarisation are declared, not left to tile order: severity rank
lives on ``EnumStatusSeverity`` and this model sorts and counts by it.

Example:
    A two-tile health board::

        from omnibase_core.enums import EnumStatusSecondaryKind, EnumStatusSeverity
        from omnibase_core.models.dashboard import (
            ModelSeverityVerdict,
            ModelStatusItemConfig,
            ModelStatusSecondary,
            ModelWidgetConfigStatusGrid,
        )
        from omnibase_core.models.primitives.model_semver import ModelSemVer

        config = ModelWidgetConfigStatusGrid(
            items=(
                ModelStatusItemConfig(
                    key="dlq",
                    label="Dead-letter queue",
                    icon="inbox",
                    verdict=ModelSeverityVerdict(
                        severity=EnumStatusSeverity.CRITICAL,
                        status_value="QUARANTINED",
                        policy_id="onex.policy.dlq_health",
                        policy_version=ModelSemVer(major=1, minor=0, patch=0),
                        policy_digest="sha256:" + "0" * 64,
                    ),
                    secondary=ModelStatusSecondary(
                        kind=EnumStatusSecondaryKind.DEPTH,
                        value=41902,
                        label="DLQ depth",
                    ),
                ),
            ),
            columns=2,
        )
"""

from collections import Counter
from collections.abc import Mapping
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums import EnumWidgetType
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_status_severity import EnumStatusSeverity
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.dashboard.model_severity_role import (
    DEFAULT_SEVERITY_ROLES,
    ModelSeverityRole,
)
from omnibase_core.models.dashboard.model_status_item_config import (
    ModelStatusItemConfig,
)

__all__ = ("ModelWidgetConfigStatusGrid",)

#: Expected config_kind value for this widget type.
_EXPECTED_CONFIG_KIND = "status_grid"


class ModelWidgetConfigStatusGrid(BaseModel):
    """Configuration for status grid dashboard widgets.

    Displays a grid of status indicators for monitoring the health of multiple
    systems, services, or components. Each tile carries an upstream verdict; the
    grid maps that verdict to presentation and never computes one.

    Attributes:
        config_kind: Literal discriminator value, always "status_grid".
        widget_type: Widget type enum, always STATUS_GRID.
        items: Tiles to display.
        columns: Number of columns in the grid layout (1-12).
        show_labels: Whether to display the tile's own text label.
        compact: Whether to use compact mode with smaller indicators.
        severity_roles: How each severity renders — theme token name, text
            label, icon. Every severity must be covered exactly once, with a
            distinct label and a distinct icon.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    config_kind: Literal["status_grid"] = Field(
        default="status_grid", description="Discriminator for widget config union"
    )
    widget_type: EnumWidgetType = Field(
        default=EnumWidgetType.STATUS_GRID, description="Widget type enum value"
    )
    items: tuple[ModelStatusItemConfig, ...] = Field(
        default=(), description="Status items to display"
    )
    columns: int = Field(default=3, ge=1, le=12, description="Number of grid columns")
    show_labels: bool = Field(default=True, description="Show item labels")
    compact: bool = Field(default=False, description="Use compact display mode")
    severity_roles: tuple[ModelSeverityRole, ...] = Field(
        default=DEFAULT_SEVERITY_ROLES,
        description=(
            "Presentation of each severity: theme token NAME, text label, icon. "
            "Carries no colour value — that is the theme instance's job."
        ),
    )

    @model_validator(mode="after")
    def validate_severity_roles_cover_every_severity(self) -> Self:
        """Reject a role set that cannot render some severity, or renders two alike.

        A missing severity means a tile the board cannot draw; a duplicated
        label or icon means two severities distinguishable only by hue, which is
        the exact failure gate GC.4 forbids.

        Raises:
            ValueError: If a severity is missing or duplicated, or if two roles
                share a label or an icon.
        """
        severities = [role.severity for role in self.severity_roles]
        missing = sorted(
            severity.value
            for severity in EnumStatusSeverity
            if severity not in severities
        )
        if missing:
            # error-ok: Pydantic model_validator enforces complete severity coverage
            raise ValueError(
                f"severity_roles must cover every severity; missing: {missing}"
            )
        duplicated = sorted(
            severity.value
            for severity, count in Counter(severities).items()
            if count > 1
        )
        if duplicated:
            # error-ok: Pydantic model_validator enforces one role per severity
            raise ValueError(
                f"severity_roles must declare each severity once; duplicated: "
                f"{duplicated}"
            )
        for attribute in ("label", "icon"):
            values = [getattr(role, attribute) for role in self.severity_roles]
            repeats = sorted(
                value for value, count in Counter(values).items() if count > 1
            )
            if repeats:
                # error-ok: Pydantic model_validator rejects color-only severity roles
                raise ValueError(
                    f"severity_roles must give each severity a distinct "
                    f"{attribute} so severity is never conveyed by colour "
                    f"alone; repeated: {repeats}"
                )
        return self

    @model_validator(mode="after")
    def validate_widget_type_config_kind_consistency(self) -> Self:
        """Validate that widget_type is consistent with config_kind.

        Ensures that the widget_type enum matches the expected config_kind
        discriminator value. widget_type=STATUS_GRID must have
        config_kind="status_grid".

        Raises:
            ValueError: If widget_type does not match config_kind.
        """
        if self.widget_type is not EnumWidgetType.STATUS_GRID:
            raise ValueError(
                f"widget_type must be STATUS_GRID for status_grid config, "
                f"got {self.widget_type.value}"
            )
        if self.config_kind != _EXPECTED_CONFIG_KIND:
            raise ValueError(
                f"config_kind must be '{_EXPECTED_CONFIG_KIND}' for STATUS_GRID widget, "
                f"got '{self.config_kind}'"
            )
        return self

    def role_for(self, severity: EnumStatusSeverity) -> ModelSeverityRole:
        """Return how ``severity`` renders on this grid.

        Args:
            severity: The severity to resolve.

        Returns:
            The declared role. Total by construction — the validator guarantees
            every severity is covered.

        Raises:
            ModelOnexError: If the role set does not cover ``severity``, which
                the constructor's validator makes unreachable.
        """
        for role in self.severity_roles:
            if role.severity is severity:
                return role
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.INVALID_STATE,
            message=(
                f"severity_roles is missing '{severity.value}' despite "
                f"construction-time validation"
            ),
        )

    def items_worst_first(self) -> tuple[ModelStatusItemConfig, ...]:
        """Return the tiles ordered worst-first, deterministically.

        Sorted by declared severity rank descending, then by ``key`` ascending
        so two tiles of equal severity never swap places between renders.

        Returns:
            The tiles in worst-first order.
        """
        return tuple(
            sorted(
                self.items,
                key=lambda item: (-item.verdict.severity.severity_rank, item.key),
            )
        )

    def severity_counts(self) -> Mapping[EnumStatusSeverity, int]:
        """Summarise the board by severity, worst first.

        Every severity appears, including those with zero tiles: a board that
        silently omits "critical: 0" reads differently from one that states it.

        Returns:
            Counts keyed by severity, ordered worst-first.
        """
        counts = Counter(item.verdict.severity for item in self.items)
        return {
            severity: counts.get(severity, 0)
            for severity in sorted(
                EnumStatusSeverity,
                key=lambda severity: -severity.severity_rank,
            )
        }
