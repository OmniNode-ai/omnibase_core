"""
Trigger Mappings Model.

Strongly-typed trigger mappings model that replaces dict[str, str] patterns
with proper Pydantic validation and type safety.

Strict typing is enforced: No Any types or dict[str, Any]patterns allowed.
"""

from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class ModelTriggerMappings(BaseModel):
    """
    Strongly-typed trigger mappings for event-to-workflow coordination.

    Replaces dict[str, str] patterns with proper Pydantic model
    providing runtime validation and type safety for trigger mappings.

    Strict typing is enforced: No Any types or dict[str, Any]patterns allowed.
    """

    # ONEX correlation tracking
    correlation_id: UUID = Field(
        default_factory=uuid4,
        description="UUID for tracking trigger mappings across operations",
    )

    # Core mappings
    event_pattern_mappings: dict[str, str] = Field(
        default_factory=dict,
        description="Event patterns mapped to workflow actions (strongly typed)",
    )

    # Specific event type mappings
    workflow_start_events: dict[str, str] = Field(
        default_factory=dict,
        description="Events that trigger workflow start (event_type -> workflow_id)",
    )

    workflow_stop_events: dict[str, str] = Field(
        default_factory=dict,
        description="Events that trigger workflow stop (event_type -> action)",
    )

    workflow_pause_events: dict[str, str] = Field(
        default_factory=dict,
        description="Events that trigger workflow pause (event_type -> action)",
    )

    workflow_resume_events: dict[str, str] = Field(
        default_factory=dict,
        description="Events that trigger workflow resume (event_type -> action)",
    )

    # Error and compensation mappings
    error_handling_mappings: dict[str, str] = Field(
        default_factory=dict,
        description="Error events mapped to handling actions (error_type -> action)",
    )

    compensation_trigger_mappings: dict[str, str] = Field(
        default_factory=dict,
        description="Events that trigger compensation actions (event_type -> compensation_plan_id)",
    )

    # State transition mappings
    state_change_mappings: dict[str, str] = Field(
        default_factory=dict,
        description="State change events mapped to actions (state_event -> action)",
    )

    # Custom action mappings
    custom_action_mappings: dict[str, str] = Field(
        default_factory=dict,
        description="Custom events mapped to custom actions (event_pattern -> action_id)",
    )

    # Notification mappings
    notification_mappings: dict[str, str] = Field(
        default_factory=dict,
        description="Events mapped to notification actions (event_type -> notification_template)",
    )

    # Routing mappings
    routing_mappings: dict[str, str] = Field(
        default_factory=dict,
        description="Events mapped to routing destinations (event_type -> destination)",
    )

    @field_validator(
        "event_pattern_mappings",
        "workflow_start_events",
        "workflow_stop_events",
        "workflow_pause_events",
        "workflow_resume_events",
        "error_handling_mappings",
        "compensation_trigger_mappings",
        "state_change_mappings",
        "custom_action_mappings",
        "notification_mappings",
        "routing_mappings",
    )
    @classmethod
    def validate_string_mappings(cls, v: dict[str, str]) -> dict[str, str]:
        """Validate string-to-string mappings."""
        validated = {}

        for key, value in v.items():
            # Validate key
            key = key.strip()
            if not key:
                continue  # Skip empty keys

            if len(key) > 500:
                raise ModelOnexError(
                    message=f"Mapping key '{key}' too long. Maximum 500 characters.",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                )

            # Validate value
            if not isinstance(value, str):
                raise ModelOnexError(
                    message=f"Mapping value for key {key!r} must be a string, got {type(value)}",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                )

            value = value.strip()
            if not value:
                continue  # Skip empty values

            if len(value) > 500:
                raise ModelOnexError(
                    message=f"Mapping value '{value}' too long. Maximum 500 characters.",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                )

            validated[key] = value

        return validated

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    def get_all_mappings(self) -> dict[str, str]:
        """
        Get all mappings as a single flattened dictionary.

        Returns:
            Flattened dictionary of all mappings
        """
        result = {}
        result.update(self.event_pattern_mappings)
        result.update(self.workflow_start_events)
        result.update(self.workflow_stop_events)
        result.update(self.workflow_pause_events)
        result.update(self.workflow_resume_events)
        result.update(self.error_handling_mappings)
        result.update(self.compensation_trigger_mappings)
        result.update(self.state_change_mappings)
        result.update(self.custom_action_mappings)
        result.update(self.notification_mappings)
        result.update(self.routing_mappings)
        return result

    def add_mapping(self, category: str, event_pattern: str, action: str) -> None:
        """
        Add a mapping to the specified category.

        Args:
            category: Mapping category name
            event_pattern: Event pattern to match
            action: Action to trigger

        Raises:
            ModelOnexError: If category is invalid
        """
        category_mapping = {
            "event_pattern": self.event_pattern_mappings,
            "workflow_start": self.workflow_start_events,
            "workflow_stop": self.workflow_stop_events,
            "workflow_pause": self.workflow_pause_events,
            "workflow_resume": self.workflow_resume_events,
            "error_handling": self.error_handling_mappings,
            "compensation": self.compensation_trigger_mappings,
            "state_change": self.state_change_mappings,
            "custom_action": self.custom_action_mappings,
            "notification": self.notification_mappings,
            "routing": self.routing_mappings,
        }

        if category not in category_mapping:
            raise ModelOnexError(
                message=f"Invalid mapping category '{category}'. Valid categories: {list(category_mapping.keys())}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

        category_mapping[category][event_pattern.strip()] = action.strip()
