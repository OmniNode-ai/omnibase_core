"""
Protocol interface for advanced text preprocessing.

Defines the contract for sophisticated text preprocessing capabilities
including configurable chunking, overlap handling, and language-aware processing.
"""

from typing import Protocol

from omnibase_core.model.semantic.model_preprocessing_input_state import \
    ModelPreprocessingInputState
from omnibase_core.model.semantic.model_preprocessing_output_state import \
    ModelPreprocessingOutputState


class ProtocolAdvancedPreprocessor(Protocol):
    """
    Protocol for advanced text preprocessing tools.

    This protocol defines the interface for tools that provide sophisticated
    text preprocessing capabilities with configurable strategies and validation.
    """

    def process(
        self, input_state: ModelPreprocessingInputState
    ) -> ModelPreprocessingOutputState:
        """
        Process documents with advanced preprocessing strategies.

        Args:
            input_state: Input state containing documents and configuration

        Returns:
            Output state with processed documents and metadata
        """
        ...
