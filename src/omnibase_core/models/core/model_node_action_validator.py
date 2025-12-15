"""
Node Action Validator Model.

Comprehensive validator for node actions with security and trust scoring.
"""

from datetime import UTC, datetime, timedelta

from omnibase_core.models.core.model_action_metadata import ModelActionMetadata
from omnibase_core.models.core.model_action_payload_types import SpecificActionPayload
from omnibase_core.models.core.model_action_validation_result import (
    ModelActionValidationResult,
)
from omnibase_core.models.core.model_node_action import ModelNodeAction
from omnibase_core.models.core.model_node_action_type import ModelNodeActionType
from omnibase_core.types.typed_dict_action_validation_context import (
    TypedDictActionValidationContext,
)
from omnibase_core.types.typed_dict_action_validation_statistics import (
    TypedDictActionValidationStatistics,
)
from omnibase_core.utils.util_hash import deterministic_hash


class ModelNodeActionValidator:
    """
    Comprehensive validator for node actions with security and trust scoring.

    Provides validation logic that can be integrated into node execution pipelines.
    """

    def __init__(
        self,
        node_name: str,
        supported_actions: list[ModelNodeActionType],
        validation_cache_size: int = 100,
    ):
        """
        Initialize the validator for a specific node.

        Args:
            node_name: Name of the node this validator is for
            supported_actions: List of rich action types supported by the node
            validation_cache_size: Maximum validation results to cache
        """
        self.node_name = node_name
        self.supported_actions = supported_actions
        self.validation_history: list[ModelActionValidationResult] = []
        self.validation_cache_size = validation_cache_size
        self._validation_cache: dict[str, ModelActionValidationResult] = {}
        self._cache_keys: list[str] = []

    def validate_action(
        self,
        action: ModelNodeAction,
        payload: SpecificActionPayload | None = None,
        metadata: ModelActionMetadata | None = None,
        context: TypedDictActionValidationContext | None = None,
        use_cache: bool = True,
    ) -> ModelActionValidationResult:
        """
        Validate a node action with comprehensive checks.

        Args:
            action: The action to validate
            payload: Optional payload for the action
            metadata: Optional metadata for the action
            context: Optional execution context
            use_cache: Whether to use validation caching

        Returns:
            Detailed validation result
        """
        if use_cache:
            cache_key = self._get_action_cache_key(action)
            if cache_key in self._validation_cache:
                cached_result = self._validation_cache[cache_key]
                # Return cached result if it's still valid (not expired)
                if not self._is_cache_expired(cached_result):
                    return cached_result

        # Perform validation
        result = self._perform_validation(action, payload, metadata, context)

        # Cache the result
        if use_cache:
            self._cache_validation_result(cache_key, result)

        return result

    def _get_action_cache_key(self, action: ModelNodeAction) -> str:
        """Generate a deterministic cache key for action validation.

        Uses SHA-256 instead of Python's built-in hash() for determinism
        across Python sessions (hash() varies with PYTHONHASHSEED).
        """
        action_content = str(action.model_dump())
        content_hash = deterministic_hash(action_content)
        return f"{action.action_name}:{action.action_type}:{content_hash}"

    def _cache_validation_result(
        self,
        cache_key: str,
        result: ModelActionValidationResult,
    ) -> None:
        """Cache validation result with size limit."""
        if len(self._cache_keys) >= self.validation_cache_size:
            # Remove oldest entry
            oldest_key = self._cache_keys.pop(0)
            del self._validation_cache[oldest_key]

        self._validation_cache[cache_key] = result
        self._cache_keys.append(cache_key)

    def _is_cache_expired(self, result: ModelActionValidationResult) -> bool:
        """Check if cached validation result has expired."""
        return datetime.now(UTC) - result.validated_at > timedelta(minutes=5)

    def _perform_validation(
        self,
        action: ModelNodeAction,
        payload: SpecificActionPayload | None = None,
        metadata: ModelActionMetadata | None = None,
        context: TypedDictActionValidationContext | None = None,
    ) -> ModelActionValidationResult:
        """Perform the actual validation logic."""
        result = ModelActionValidationResult(is_valid=True)

        # Basic action validation
        self._validate_action_type(action, result)
        self._validate_action_structure(action, result)

        # Payload validation
        if payload:
            self._validate_payload(action, payload, result)

        # Metadata validation
        if metadata:
            self._validate_metadata(action, metadata, result)

        # Security validation
        self._validate_security(action, payload, metadata, context, result)

        # Trust score calculation
        self._calculate_trust_score(action, payload, metadata, context, result)

        # Final validation status
        result.is_valid = len(result.validation_errors) == 0

        # Store in history for pattern analysis
        self.validation_history.append(result)

        return result

    def _validate_action_type(
        self,
        action: ModelNodeAction,
        result: ModelActionValidationResult,
    ) -> None:
        """Validate that the action type is supported by this node."""
        if action.action_type not in self.supported_actions:
            result.validation_errors.append(
                f"Action type '{action.action_type.name}' not supported by {self.node_name} node. "
                f"Supported: {[a.name for a in self.supported_actions]}",
            )
            result.security_checks["action_type_supported"] = False
        else:
            result.security_checks["action_type_supported"] = True

    def _validate_action_structure(
        self,
        action: ModelNodeAction,
        result: ModelActionValidationResult,
    ) -> None:
        """Validate the structure and content of the action."""
        # Check required fields
        if not action.action_name:
            result.validation_errors.append("Action name is required")

        if not action.display_name:
            result.validation_errors.append("Display name is required")

        if not action.description:
            result.validation_errors.append("Description is required")

        # Check for reasonable duration estimates
        if (
            action.estimated_duration_ms and action.estimated_duration_ms > 600000
        ):  # 10 minutes
            result.validation_warnings.append(
                f"Action duration estimate ({action.estimated_duration_ms}ms) is very high",
            )

        # Validate destructive actions have proper flags
        if action.is_destructive and not action.requires_confirmation:
            result.validation_warnings.append(
                "Destructive actions should typically require confirmation",
            )

        result.security_checks["structure_valid"] = len(result.validation_errors) == 0

    def _validate_payload(
        self,
        action: ModelNodeAction,
        payload: SpecificActionPayload,
        result: ModelActionValidationResult,
    ) -> None:
        """Validate that the payload matches the action type."""
        if payload.action_type != action.action_type:
            result.validation_errors.append(
                f"Payload action type '{payload.action_type.name}' does not match "
                f"action type '{action.action_type.name}'",
            )
            result.security_checks["payload_type_match"] = False
        else:
            result.security_checks["payload_type_match"] = True

        # Additional payload-specific validation could be added here
        result.security_checks["payload_validated"] = True

    def _validate_metadata(
        self,
        action: ModelNodeAction,
        metadata: ModelActionMetadata,
        result: ModelActionValidationResult,
    ) -> None:
        """Validate action metadata."""
        # Check trust score bounds
        if not metadata.validate_trust_score():
            result.validation_errors.append(
                f"Invalid trust score: {metadata.trust_score} (must be 0.0-1.0)",
            )
            result.security_checks["trust_score_valid"] = False
        else:
            result.security_checks["trust_score_valid"] = True

        # Check for expiration
        if metadata.is_expired():
            result.validation_errors.append("Action metadata has expired")
            result.security_checks["not_expired"] = False
        else:
            result.security_checks["not_expired"] = True

        # Validate action type consistency
        if (
            metadata.action_type is not None
            and metadata.action_type != action.action_type
        ):
            result.validation_errors.append(
                f"Metadata action type '{metadata.action_type.name}' does not match "
                f"action type '{action.action_type.name}'",
            )
            result.security_checks["metadata_consistency"] = False
        else:
            result.security_checks["metadata_consistency"] = True

    def _validate_security(
        self,
        action: ModelNodeAction,
        payload: SpecificActionPayload | None,
        metadata: ModelActionMetadata | None,
        context: TypedDictActionValidationContext | None,
        result: ModelActionValidationResult,
    ) -> None:
        """Perform security validation checks."""
        # Check for suspicious patterns
        suspicious_patterns = ["../", "eval(", "exec(", "__import__"]
        action_content = f"{action.action_name} {action.description}"

        for pattern in suspicious_patterns:
            if pattern in action_content:
                result.validation_warnings.append(
                    f"Potentially suspicious pattern detected: {pattern}",
                )

        # Validate destructive action handling
        if action.is_destructive:
            if not action.requires_confirmation:
                result.recommendations.append(
                    "Consider requiring confirmation for destructive actions",
                )

            if metadata and metadata.trust_score < 0.8:
                result.validation_warnings.append(
                    f"Destructive action with low trust score: {metadata.trust_score}",
                )

        result.security_checks["security_validated"] = True

    def _calculate_trust_score(
        self,
        action: ModelNodeAction,
        payload: SpecificActionPayload | None,
        metadata: ModelActionMetadata | None,
        context: TypedDictActionValidationContext | None,
        result: ModelActionValidationResult,
    ) -> None:
        """Calculate a trust score for the action based on various factors."""
        base_score = 1.0

        # Reduce score for validation errors
        if result.validation_errors:
            base_score -= len(result.validation_errors) * 0.2

        # Reduce score for validation warnings
        if result.validation_warnings:
            base_score -= len(result.validation_warnings) * 0.1

        # Factor in metadata trust score
        if metadata:
            base_score = min(base_score, metadata.trust_score)

        # Factor in destructive actions
        if action.is_destructive:
            base_score *= 0.9  # Slight reduction for destructive actions

        # Ensure score stays within bounds
        result.trust_score = max(0.0, min(1.0, base_score))

    def can_execute_action(
        self,
        action: ModelNodeAction,
        minimum_trust_score: float = 0.5,
    ) -> tuple[bool, list[str]]:
        """
        Check if an action can be executed based on validation.

        Args:
            action: The action to check
            minimum_trust_score: Minimum required trust score

        Returns:
            Tuple of (can_execute, reasons_if_not)
        """
        validation_result = self.validate_action(action)

        if not validation_result.is_valid:
            return False, validation_result.validation_errors

        if validation_result.trust_score < minimum_trust_score:
            return False, [
                f"Trust score {validation_result.trust_score} below minimum {minimum_trust_score}",
            ]

        return True, []

    def get_validation_statistics(self) -> TypedDictActionValidationStatistics:
        """Get statistics about validation history."""
        if not self.validation_history:
            return TypedDictActionValidationStatistics(total_validations=0)

        total = len(self.validation_history)
        valid_count = sum(1 for r in self.validation_history if r.is_valid)
        avg_trust_score = sum(r.trust_score for r in self.validation_history) / total

        return TypedDictActionValidationStatistics(
            total_validations=total,
            valid_actions=valid_count,
            invalid_actions=total - valid_count,
            success_rate=valid_count / total,
            average_trust_score=avg_trust_score,
            recent_validations=(
                self.validation_history[-10:] if total > 10 else self.validation_history
            ),
        )


def create_node_validator(
    node_name: str,
    supported_actions: list[ModelNodeActionType],
    validation_cache_size: int = 100,
) -> ModelNodeActionValidator:
    """
    Create a validator for a specific node.

    Args:
        node_name: Name of the node
        supported_actions: List of rich action types supported by the node
        validation_cache_size: Maximum validation results to cache

    Returns:
        Configured validator instance
    """
    return ModelNodeActionValidator(node_name, supported_actions, validation_cache_size)
