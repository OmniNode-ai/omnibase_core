"""
Mixin that provides generic introspection capabilities to any node.

This eliminates the need for separate introspection.py files in each tool.
"""

import sys

from omnibase_core.core.introspection import GenericIntrospection
from omnibase_core.models.core.model_usage_example import ModelUsageExample


class MixinGenericIntrospection:
    """
    Mixin that provides introspection capabilities using GenericIntrospection.

    Usage:
    ```python
    class WorkflowGeneratorNode(
        MixinGenericIntrospection,
        MixinIntrospectionPublisher,
        MixinNodeIdFromContract,
        MixinContractStateReducer,
        ProtocolReducer,
    ):
        # Define introspection configuration as class attributes
        INTROSPECTION_TOOL_NAME = "tool_workflow_generator"
        INTROSPECTION_TOOL_DESCRIPTION = "LlamaIndex workflow generator for ONEX"
        INTROSPECTION_TOOL_TYPE = "generation"
        INTROSPECTION_INPUT_IMPORTS = [
            "from ..models.model_workflow_generator_input_state import ModelWorkflowGeneratorInputState"
        ]
        INTROSPECTION_OUTPUT_IMPORTS = [
            "from ..models.model_workflow_generator_output_state import ModelWorkflowGeneratorOutputState"
        ]
        INTROSPECTION_USAGE_EXAMPLES = [...]
        INTROSPECTION_EXTRA_CAPABILITIES = {
            "workflow_generation": True,
            "llamaindex_support": True,
        }
    ```
    """

    # These class attributes should be overridden by the implementing class
    INTROSPECTION_TOOL_NAME: str = ""
    INTROSPECTION_TOOL_DESCRIPTION: str = ""
    INTROSPECTION_TOOL_TYPE: str = ""
    INTROSPECTION_INPUT_IMPORTS: list[str] = []
    INTROSPECTION_OUTPUT_IMPORTS: list[str] = []
    INTROSPECTION_USAGE_EXAMPLES: list[ModelUsageExample] = []
    INTROSPECTION_EXTRA_CAPABILITIES: dict[str, bool] | None = None
    INTROSPECTION_EXTRA_HEALTH_CHECKS: dict[str, bool] | None = None

    @classmethod
    def handle_introspection(cls) -> None:
        """
        Handle --introspect command line flag using GenericIntrospection.

        This method should be called from the node's main function when
        --introspect is detected.
        """
        if "--introspect" not in sys.argv:
            return

        # Validate that required attributes are set
        if not cls.INTROSPECTION_TOOL_NAME:
            msg = "INTROSPECTION_TOOL_NAME must be set when using MixinGenericIntrospection"
            raise ValueError(
                msg,
            )

        # Create a configured introspection class
        NodeIntrospection = GenericIntrospection.create(
            tool_name=cls.INTROSPECTION_TOOL_NAME,
            tool_description=cls.INTROSPECTION_TOOL_DESCRIPTION,
            tool_type=cls.INTROSPECTION_TOOL_TYPE,
            input_model_imports=cls.INTROSPECTION_INPUT_IMPORTS,
            output_model_imports=cls.INTROSPECTION_OUTPUT_IMPORTS,
            usage_examples=cls.INTROSPECTION_USAGE_EXAMPLES,
            extra_capabilities=cls.INTROSPECTION_EXTRA_CAPABILITIES,
            extra_health_checks=cls.INTROSPECTION_EXTRA_HEALTH_CHECKS,
        )

        # Handle the introspection command
        NodeIntrospection.handle_introspect_command()
        sys.exit(0)

    @classmethod
    def get_introspection_class(cls):
        """
        Get the configured introspection class for this node.

        This can be useful for testing or programmatic access.
        """
        return GenericIntrospection.create(
            tool_name=cls.INTROSPECTION_TOOL_NAME,
            tool_description=cls.INTROSPECTION_TOOL_DESCRIPTION,
            tool_type=cls.INTROSPECTION_TOOL_TYPE,
            input_model_imports=cls.INTROSPECTION_INPUT_IMPORTS,
            output_model_imports=cls.INTROSPECTION_OUTPUT_IMPORTS,
            usage_examples=cls.INTROSPECTION_USAGE_EXAMPLES,
            extra_capabilities=cls.INTROSPECTION_EXTRA_CAPABILITIES,
            extra_health_checks=cls.INTROSPECTION_EXTRA_HEALTH_CHECKS,
        )
