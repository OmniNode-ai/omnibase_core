# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Normalization Family Enum (OMN-9759).

Phase 1 of the corpus classification and normalization layer
(parent epic OMN-9757).

Classifies the family of contract migration being applied during
normalization. Each member tags a single, well-defined cohort of
contract changes so the migration audit can group, count, and report
findings by family.

Families:
    - family_legacy_input_output_model: legacy input/output model schema renames
    - family_legacy_event_bus: legacy event bus block migrations
    - family_legacy_metadata: legacy top-level metadata fields
    - family_legacy_handler_routing: legacy handler routing/dispatch shapes
    - family_required_now_optional: fields that flipped required → optional
    - family_misc_extra_fields: miscellaneous extra fields tolerated by the model
    - family_handler_block: handler block additions/normalization
    - family_descriptor_block: descriptor block additions/normalization
    - family_terminal_event: terminal event declaration additions
    - family_event_schema_evolution: schema evolution within event payloads
    - family_state_machine: FSM/state-machine block additions
    - family_dod_evidence_schema: dod_evidence schema migrations
    - family_custom_validator: custom validator block additions
    - family_node_type_alias: bare EFFECT/COMPUTE/REDUCER aliases promoted to typed enum
"""

from enum import Enum, unique


@unique
class EnumNormalizationFamily(str, Enum):
    """Canonical migration families for contract normalization."""

    FAMILY_LEGACY_INPUT_OUTPUT_MODEL = "family_legacy_input_output_model"
    FAMILY_LEGACY_EVENT_BUS = "family_legacy_event_bus"
    FAMILY_LEGACY_METADATA = "family_legacy_metadata"
    FAMILY_LEGACY_HANDLER_ROUTING = "family_legacy_handler_routing"
    FAMILY_REQUIRED_NOW_OPTIONAL = "family_required_now_optional"
    FAMILY_MISC_EXTRA_FIELDS = "family_misc_extra_fields"
    FAMILY_HANDLER_BLOCK = "family_handler_block"
    FAMILY_DESCRIPTOR_BLOCK = "family_descriptor_block"
    FAMILY_TERMINAL_EVENT = "family_terminal_event"
    FAMILY_EVENT_SCHEMA_EVOLUTION = "family_event_schema_evolution"
    FAMILY_STATE_MACHINE = "family_state_machine"
    FAMILY_DOD_EVIDENCE_SCHEMA = "family_dod_evidence_schema"
    FAMILY_CUSTOM_VALIDATOR = "family_custom_validator"
    FAMILY_NODE_TYPE_ALIAS = "family_node_type_alias"
