# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed, fail-closed view of design-record contract rules (OMN-21509)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums import EnumSeverity
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)

type RuleConfiguration = tuple[bool, EnumSeverity, str, str]


def _contract_error(message: str) -> ModelOnexError:
    return ModelOnexError(
        message=message, error_code=EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR
    )


class ModelDesignRecordRules(BaseModel):
    """Each rule's configuration, diagnostic wording, and validated parameters."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    record_missing: RuleConfiguration = Field(
        description="Missing-record rule state and severity"
    )
    intended_state_missing: RuleConfiguration = Field(
        description="Missing intended state rule state and severity"
    )
    live_check_command_missing: RuleConfiguration = Field(
        description="Missing command rule state and severity"
    )
    failure_mode_table_missing: RuleConfiguration = Field(
        description="Missing table rule state and severity"
    )
    failure_mode_table_empty: RuleConfiguration = Field(
        description="Empty table rule state and severity"
    )
    row_without_detector_or_gap: RuleConfiguration = Field(
        description="Uncovered row rule state and severity"
    )
    severity_out_of_range: RuleConfiguration = Field(
        description="Row severity rule state and severity"
    )

    intended_state_label: str = Field(
        description="Label used to find the intended state"
    )
    live_check_command_label: str = Field(
        description="Label used to find the live command"
    )
    live_check_failing_label: str = Field(
        description="Label used to find the failing reading"
    )
    mode_column: str = Field(description="Required mode header substring")
    severity_column: str = Field(
        description="Required severity header substring and column selector"
    )
    detector_column: str = Field(
        description="Required detector header substring and column selector"
    )
    empty_detector_values: tuple[str, ...] = Field(
        description="Detector values that count as empty"
    )
    gap_pattern: str = Field(
        description="Regular expression recognizing explicit coverage gaps"
    )
    severity_levels: tuple[int, ...] = Field(
        description="Allowed failure-mode severity levels in contract order"
    )

    def configuration(self, rule_id: str) -> RuleConfiguration:
        """Return enablement, issue level, message template, and part for a known rule."""
        return {
            "record_missing": self.record_missing,
            "intended_state_missing": self.intended_state_missing,
            "live_check_command_missing": self.live_check_command_missing,
            "failure_mode_table_missing": self.failure_mode_table_missing,
            "failure_mode_table_empty": self.failure_mode_table_empty,
            "row_without_detector_or_gap": self.row_without_detector_or_gap,
            "severity_out_of_range": self.severity_out_of_range,
        }[rule_id]

    @classmethod
    def from_contract(
        cls, contract: ModelValidatorSubcontract
    ) -> ModelDesignRecordRules:
        """Require all seven rules and all parameters, including disabled rules."""
        by_id = {rule.rule_id: rule for rule in contract.rules}

        def rule(rule_id: str) -> ModelValidatorRule:
            if rule_id not in by_id:
                raise _contract_error(f"{rule_id}: required rule is absent")
            return by_id[rule_id]

        def configuration(rule_id: str) -> RuleConfiguration:
            value = rule(rule_id)
            return (
                value.enabled,
                value.severity,
                string_parameter(rule_id, "message"),
                string_parameter(rule_id, "part"),
            )

        def string_parameter(rule_id: str, name: str) -> str:
            value = (rule(rule_id).parameters or {}).get(name)
            if not isinstance(value, str):
                raise _contract_error(
                    f"{rule_id}: required parameter {name} must be a string"
                )
            return value

        def strings_parameter(rule_id: str, name: str) -> tuple[str, ...]:
            value = (rule(rule_id).parameters or {}).get(name)
            if not isinstance(value, list):
                raise _contract_error(
                    f"{rule_id}: required parameter {name} must be a list of strings"
                )
            return tuple(value)

        levels = strings_parameter("severity_out_of_range", "severity_levels")
        try:
            severity_levels = tuple(int(level) for level in levels)
        except ValueError as exc:
            raise _contract_error(
                "severity_out_of_range: severity_levels must contain integers"
            ) from exc

        return cls(
            record_missing=configuration("record_missing"),
            intended_state_missing=configuration("intended_state_missing"),
            live_check_command_missing=configuration("live_check_command_missing"),
            failure_mode_table_missing=configuration("failure_mode_table_missing"),
            failure_mode_table_empty=configuration("failure_mode_table_empty"),
            row_without_detector_or_gap=configuration("row_without_detector_or_gap"),
            severity_out_of_range=configuration("severity_out_of_range"),
            intended_state_label=string_parameter(
                "record_missing", "intended_state_label"
            ),
            live_check_command_label=string_parameter(
                "record_missing", "live_check_command_label"
            ),
            live_check_failing_label=string_parameter(
                "record_missing", "live_check_failing_label"
            ),
            mode_column=string_parameter("failure_mode_table_missing", "mode_column"),
            severity_column=string_parameter(
                "failure_mode_table_missing", "severity_column"
            ),
            detector_column=string_parameter(
                "failure_mode_table_missing", "detector_column"
            ),
            empty_detector_values=strings_parameter(
                "row_without_detector_or_gap", "empty_detector_values"
            ),
            gap_pattern=string_parameter("row_without_detector_or_gap", "gap_pattern"),
            severity_levels=severity_levels,
        )
