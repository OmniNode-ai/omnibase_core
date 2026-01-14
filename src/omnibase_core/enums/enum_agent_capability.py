"""
Enum for agent capabilities.

Defines capabilities that agents can have for task routing and selection.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumAgentCapability(StrValueHelper, str, Enum):
    """Agent capabilities for intelligent task routing."""

    # Code-related capabilities
    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    CODE_REFACTORING = "code_refactoring"
    CODE_ANALYSIS = "code_analysis"
    CODE_COMPLETION = "code_completion"

    # Reasoning and analysis
    REASONING = "reasoning"
    COMPLEX_ANALYSIS = "complex_analysis"
    QUICK_VALIDATION = "quick_validation"
    ROOT_CAUSE_ANALYSIS = "root_cause_analysis"

    # Documentation and communication
    DOCUMENTATION = "documentation"
    TECHNICAL_WRITING = "technical_writing"
    EXPLANATION = "explanation"
    TUTORIAL_GENERATION = "tutorial_generation"

    # [Any]types
    GENERAL_TASKS = "general_tasks"
    ARCHITECTURE_DESIGN = "architecture_design"
    SECURITY_ANALYSIS = "security_analysis"
    PERFORMANCE_OPTIMIZATION = "performance_optimization"

    # Special capabilities
    MULTIMODAL = "multimodal"
    EMBEDDINGS = "embeddings"
    LONG_CONTEXT = "long_context"
    FAST_INFERENCE = "fast_inference"

    # Language support
    MULTILINGUAL = "multilingual"

    def is_code_related(self) -> bool:
        """Check if this is a code-related capability."""
        return self.value.startswith("code_")

    def requires_large_model(self) -> bool:
        """Check if this capability typically requires a larger model."""
        return self in {
            self.COMPLEX_ANALYSIS,
            self.ARCHITECTURE_DESIGN,
            self.LONG_CONTEXT,
            self.REASONING,
        }


__all__ = ["EnumAgentCapability"]
