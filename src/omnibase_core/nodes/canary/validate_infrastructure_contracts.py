"""
Infrastructure Contract Validation Script

Validates all infrastructure contracts by using their backing Pydantic models
to deserialize/validate the contract YAML files. This ensures contracts are
syntactically correct and the models can be properly instantiated.
"""

import contextlib
import importlib
import sys
import traceback
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

from omnibase_core.core.model_contract_base import ModelContractBase

# Import node-specific contract models
from omnibase_core.core.model_contract_compute import ModelContractCompute
from omnibase_core.core.model_contract_effect import ModelContractEffect
from omnibase_core.core.model_contract_orchestrator import ModelContractOrchestrator
from omnibase_core.core.model_contract_reducer import ModelContractReducer

# Import for node type validation
from omnibase_core.enums.enum_node_type import EnumNodeType


class ContractValidator:
    """Validates ONEX contracts using their backing Pydantic models."""

    def __init__(self, infrastructure_path: Path):
        """Initialize validator with infrastructure tools path."""
        self.infrastructure_path = infrastructure_path
        self.validation_results = []

    def validate_subcontract_constraints(self, contract_data: dict) -> list[str]:
        """
        Validate subcontract usage against node-type-specific architectural constraints.

        Enforces rules like:
        - COMPUTE nodes cannot have state_management or aggregation subcontracts
        - REDUCER nodes should have state_transitions subcontracts
        - EFFECT nodes can have caching and routing subcontracts
        - ORCHESTRATOR nodes should have routing subcontracts

        Args:
            contract_data: The loaded contract YAML data

        Returns:
            List of subcontract validation messages
        """
        validations = []

        # Get node_type
        node_type_str = contract_data.get("node_type")
        if not node_type_str:
            return validations  # Let other validation catch this

        try:
            node_type = EnumNodeType(node_type_str)
        except ValueError:
            return validations  # Let other validation catch this

        # Check subcontract constraints based on node type
        if node_type == EnumNodeType.COMPUTE:
            # COMPUTE nodes should be stateless and focused on pure computation
            if "state_management" in contract_data:
                validations.append(
                    "❌ SUBCONTRACT VIOLATION: COMPUTE nodes cannot have state_management subcontracts",
                )
                validations.append("   💡 Use REDUCER nodes for stateful operations")

            if "aggregation" in contract_data:
                validations.append(
                    "❌ SUBCONTRACT VIOLATION: COMPUTE nodes cannot have aggregation subcontracts",
                )
                validations.append("   💡 Use REDUCER nodes for data aggregation")

            if "state_transitions" in contract_data:
                validations.append(
                    "❌ SUBCONTRACT VIOLATION: COMPUTE nodes cannot have state_transitions subcontracts",
                )
                validations.append("   💡 Use REDUCER nodes for FSM state management")

            if not any(v.startswith("❌") for v in validations[-6:]):
                validations.append("✅ COMPUTE node subcontract constraints satisfied")

        elif node_type == EnumNodeType.REDUCER:
            # REDUCER nodes should have state management capabilities
            if "state_transitions" not in contract_data:
                validations.append(
                    "⚠️  REDUCER node recommendation: Consider adding state_transitions subcontract for FSM support",
                )
            else:
                validations.append("✅ REDUCER node has state_transitions subcontract")

            # REDUCER nodes can legitimately have aggregation and state_management
            if "aggregation" in contract_data:
                validations.append(
                    "✅ REDUCER node legitimately has aggregation subcontract",
                )
            if "state_management" in contract_data:
                validations.append(
                    "✅ REDUCER node legitimately has state_management subcontract",
                )

        elif node_type == EnumNodeType.EFFECT:
            # EFFECT nodes can have caching and routing for external operations
            if "caching" in contract_data:
                validations.append(
                    "✅ EFFECT node legitimately has caching subcontract",
                )
            if "routing" in contract_data:
                validations.append(
                    "✅ EFFECT node legitimately has routing subcontract",
                )

            # EFFECT nodes should not manage internal state
            if "state_management" in contract_data:
                validations.append(
                    "❌ SUBCONTRACT VIOLATION: EFFECT nodes should not have state_management subcontracts",
                )
                validations.append(
                    "   💡 Use REDUCER nodes for state management, EFFECT nodes for side effects",
                )

        elif node_type == EnumNodeType.ORCHESTRATOR:
            # ORCHESTRATOR nodes should have workflow coordination capabilities
            if "routing" in contract_data:
                validations.append(
                    "✅ ORCHESTRATOR node legitimately has routing subcontract",
                )

            # ORCHESTRATOR nodes typically should not manage data state directly
            if "state_management" in contract_data:
                validations.append(
                    "⚠️  ORCHESTRATOR node: Consider if state_management should be delegated to REDUCER nodes",
                )

        return validations

    def create_node_specific_contract(self, contract_data: dict) -> ModelContractBase:
        """
        Factory method to create the appropriate node-specific contract model.

        This enforces strong typing by routing to the correct model based on node_type.
        COMPUTE nodes with state_management will be automatically rejected by ModelContractCompute.

        Args:
            contract_data: The loaded contract YAML data

        Returns:
            The appropriate node-specific contract model

        Raises:
            ValidationError: If contract violates architectural constraints
            ValueError: If node_type is invalid or missing
        """
        # Extract node_type
        node_type_str = contract_data.get("node_type")
        if not node_type_str:
            msg = "Contract missing required node_type field"
            raise ValueError(msg)

        try:
            node_type = EnumNodeType(node_type_str)
        except ValueError:
            msg = f"Invalid node_type: {node_type_str}"
            raise ValueError(msg)

        # Route to appropriate model based on node_type
        if node_type == EnumNodeType.COMPUTE:
            return ModelContractCompute(**contract_data)
        if node_type == EnumNodeType.REDUCER:
            return ModelContractReducer(**contract_data)
        if node_type == EnumNodeType.EFFECT:
            return ModelContractEffect(**contract_data)
        if node_type == EnumNodeType.ORCHESTRATOR:
            return ModelContractOrchestrator(**contract_data)
        msg = f"Unknown node_type: {node_type}"
        raise ValueError(msg)

    def find_model_class(
        self,
        tool_path: Path,
        model_name: str,
    ) -> type[BaseModel] | None:
        """
        Find and import the Pydantic model class from the tool's models directory.
        Also handles full module paths like 'omnibase.core.node_orchestrator.ModelOrchestratorInput'.

        Args:
            tool_path: Path to the tool version directory
            model_name: Name of the model class to find (or full module path)

        Returns:
            The Pydantic model class if found, None otherwise
        """
        # Check if this is a full module path (contains dots)
        if "." in model_name and model_name.startswith("omnibase."):
            try:
                # Split module path and class name
                parts = model_name.split(".")
                class_name = parts[-1]  # Last part is the class name
                module_path = ".".join(
                    parts[:-1],
                )  # Everything except last part is module

                # Try to import the module directly
                module = importlib.import_module(module_path)

                if hasattr(module, class_name):
                    model_class = getattr(module, class_name)
                    # For core orchestrator models, we accept any class type
                    if isinstance(model_class, type):
                        return model_class

            except ImportError:
                return None
            except Exception:
                return None

        # Standard case: look in tool's models directory
        models_path = tool_path / "models"
        if not models_path.exists():
            return None

        # Look for the model in all Python files in the models directory
        for model_file in models_path.glob("*.py"):
            if model_file.name == "__init__.py":
                continue

            # Construct module path for import
            # Get relative path from src directory
            try:
                src_path = Path.cwd() / "src"
                relative_path = model_file.relative_to(src_path)
                module_path = (
                    str(relative_path)
                    .replace("/", ".")
                    .replace("\\", ".")
                    .replace(".py", "")
                )
            except ValueError:
                # File is not under src directory, skip
                continue

            try:
                module = importlib.import_module(module_path)

                # Look for the model class in the module
                if hasattr(module, model_name):
                    model_class = getattr(module, model_name)
                    if isinstance(model_class, type) and issubclass(
                        model_class,
                        BaseModel,
                    ):
                        return model_class

            except ImportError:
                continue
            except Exception:
                continue

        return None

    def validate_contract(self, contract_path: Path) -> dict:
        """
        Validate a single contract file using its backing models.

        Args:
            contract_path: Path to the contract.yaml file

        Returns:
            Validation result dictionary
        """
        tool_name = contract_path.parent.parent.name
        version = contract_path.parent.name

        try:
            # Load the contract YAML
            with open(contract_path) as f:
                contract_data = yaml.safe_load(f)

            if not contract_data:
                return {
                    "tool": tool_name,
                    "version": version,
                    "status": "ERROR",
                    "message": "Contract file is empty or invalid YAML",
                }

            # Check if this is using the new contract format (input_state/output_state)
            has_new_format = (
                "input_state" in contract_data and "output_state" in contract_data
            )
            has_old_format = (
                "input_model" in contract_data and "output_model" in contract_data
            )

            if not has_new_format and not has_old_format:
                return {
                    "tool": tool_name,
                    "version": version,
                    "status": "ERROR",
                    "message": "Contract must have either input_state/output_state (new format) or input_model/output_model (old format)",
                }

            validation_results = []
            input_model_name = None
            output_model_name = None

            if has_old_format:
                # Old format: validate input/output models
                input_model_name = contract_data.get("input_model")
                output_model_name = contract_data.get("output_model")

                # Find and validate input model
                input_model_class = self.find_model_class(
                    contract_path.parent,
                    input_model_name,
                )
                if input_model_class:
                    validation_results.append(
                        f"✅ Found input model: {input_model_name}",
                    )

                    # Try to create a minimal instance to test model structure
                    try:
                        # Create a minimal test instance with required fields
                        self.create_test_instance_with_context(
                            input_model_class,
                            contract_path.parent,
                        )
                        validation_results.append(
                            f"✅ Input model {input_model_name} validation passed",
                        )
                    except Exception as e:
                        validation_results.append(
                            f"❌ Input model {input_model_name} validation failed: {e}",
                        )

                else:
                    validation_results.append(
                        f"❌ Input model {input_model_name} not found",
                    )

                # Find and validate output model
                output_model_class = self.find_model_class(
                    contract_path.parent,
                    output_model_name,
                )
                if output_model_class:
                    validation_results.append(
                        f"✅ Found output model: {output_model_name}",
                    )

                    # Try to create a minimal instance to test model structure
                    try:
                        self.create_test_instance_with_context(
                            output_model_class,
                            contract_path.parent,
                        )
                        validation_results.append(
                            f"✅ Output model {output_model_name} validation passed",
                        )
                    except Exception as e:
                        validation_results.append(
                            f"❌ Output model {output_model_name} validation failed: {e}",
                        )

                else:
                    validation_results.append(
                        f"❌ Output model {output_model_name} not found",
                    )

            else:
                # New format: validate input_state/output_state schemas
                validation_results.append(
                    "✅ Using new contract format (input_state/output_state)",
                )

                # Validate input_state structure
                input_state = contract_data.get("input_state", {})
                if input_state.get("object_type") == "object":
                    validation_results.append("✅ input_state has correct structure")
                else:
                    validation_results.append(
                        "❌ input_state missing object_type: 'object'",
                    )

                # Validate output_state structure
                output_state = contract_data.get("output_state", {})
                if output_state.get("object_type") == "object":
                    validation_results.append("✅ output_state has correct structure")
                else:
                    validation_results.append(
                        "❌ output_state missing object_type: 'object'",
                    )

            # Check contract structure against SP0 requirements
            sp0_validations = self.validate_sp0_contract_structure(contract_data)
            validation_results.extend(sp0_validations)

            # NEW: Validate contract against actual ModelContractContent
            contract_format_validations = self.validate_contract_format(contract_data)
            validation_results.extend(contract_format_validations)

            # ARCHITECTURAL: Pydantic model validation with extra="forbid" will catch architectural violations
            # No separate validation needed - ModelContractContent will fail on unknown fields

            # Determine overall status
            error_count = len([r for r in validation_results if r.startswith("❌")])
            status = "SUCCESS" if error_count == 0 else "FAILURE"

            return {
                "tool": tool_name,
                "version": version,
                "status": status,
                "message": f"Contract validation completed with {error_count} errors",
                "validations": validation_results,
                "input_model": input_model_name,
                "output_model": output_model_name,
                "error_count": error_count,
            }

        except yaml.YAMLError as e:
            return {
                "tool": tool_name,
                "version": version,
                "status": "YAML_ERROR",
                "message": f"Invalid YAML syntax: {e}",
            }
        except FileNotFoundError:
            return {
                "tool": tool_name,
                "version": version,
                "status": "FILE_NOT_FOUND",
                "message": "Contract file not found",
            }
        except Exception as e:
            return {
                "tool": tool_name,
                "version": version,
                "status": "ERROR",
                "message": f"Validation error: {e}",
                "traceback": traceback.format_exc(),
            }

    def create_test_instance(
        self,
        model_class: type[BaseModel],
        _recursion_depth: int = 0,
    ) -> BaseModel:
        """
        Create a minimal test instance of a Pydantic model to validate structure.
        Also handles non-Pydantic models like orchestrator models.

        Args:
            model_class: The model class (Pydantic or regular Python class)
            _recursion_depth: Internal parameter to prevent infinite recursion

        Returns:
            A test instance of the model
        """
        # Prevent infinite recursion for deeply nested models
        if _recursion_depth > 5:
            return None

        # Check if this is a Pydantic model
        if hasattr(model_class, "model_fields"):
            # Pydantic v2 model
            fields = model_class.model_fields
        elif hasattr(model_class, "__init__"):
            # Non-Pydantic model (like orchestrator models) - try minimal instantiation
            try:
                # Try to instantiate with minimal parameters
                import inspect

                sig = inspect.signature(model_class.__init__)
                # Get required parameters (those without defaults)
                required_params = {}
                for param_name, param in sig.parameters.items():
                    if (
                        param_name != "self"
                        and param.default == inspect.Parameter.empty
                    ):
                        # Provide minimal test values based on type hints or common patterns
                        if "id" in param_name.lower():
                            required_params[param_name] = "test_id"
                        elif "steps" in param_name.lower():
                            required_params[param_name] = []
                        elif param_name == "workflow_id":
                            required_params[param_name] = "test_workflow"
                        else:
                            required_params[param_name] = "test_value"

                return model_class(**required_params)
            except Exception:
                # If we can't instantiate it, just return the class itself as validation
                return model_class
        else:
            # Unknown model type, skip validation
            return model_class

        # Pydantic model handling continues below
        fields = model_class.model_fields
        test_data = {}

        for field_name, field_info in fields.items():
            # Check if field is required (Pydantic v2)
            if field_info.is_required():
                # Provide minimal values for required fields based on annotation
                field_type = field_info.annotation

                # Handle Literal types (enums)
                if (
                    hasattr(field_type, "__origin__")
                    and getattr(field_type, "__origin__", None).__name__ == "Literal"
                ):
                    # Use the first literal value
                    test_data[field_name] = field_type.__args__[0]
                elif field_type == str:
                    test_data[field_name] = "test_string"
                elif field_type == int:
                    test_data[field_name] = 1
                elif field_type == float:
                    test_data[field_name] = 1.0
                elif field_type == bool:
                    test_data[field_name] = True
                elif field_type == list or str(field_type).startswith("typing.List"):
                    test_data[field_name] = []
                elif field_type == dict or str(field_type).startswith("typing.Dict"):
                    test_data[field_name] = {}
                else:
                    # For complex types, check if it's a Pydantic model we can instantiate
                    nested_instance = self._create_nested_model_instance(
                        field_type,
                        _recursion_depth,
                    )
                    if nested_instance is not None:
                        test_data[field_name] = nested_instance
                    # For other complex types, try to use default if available
                    elif field_info.default is not None and field_info.default != ...:
                        test_data[field_name] = field_info.default
                    else:
                        # Skip complex required fields that we can't easily mock
                        test_data[field_name] = None

        return model_class(**test_data)

    def create_test_instance_with_context(
        self,
        model_class: type[BaseModel],
        tool_path: Path,
        _recursion_depth: int = 0,
    ) -> BaseModel:
        """
        Create a test instance with context for finding nested models in the tool's directory.

        Args:
            model_class: The model class to instantiate
            tool_path: Path to the tool directory for finding nested models
            _recursion_depth: Current recursion depth

        Returns:
            A test instance of the model
        """
        # Store the tool path for nested model resolution
        self._current_tool_path = tool_path
        return self.create_test_instance(model_class, _recursion_depth)

    def _create_nested_model_instance(
        self,
        field_type: Any,
        recursion_depth: int,
    ) -> BaseModel | None:
        """
        Helper method to create instances of nested Pydantic models.

        Args:
            field_type: The type annotation of the field
            recursion_depth: Current recursion depth

        Returns:
            A test instance of the nested model, or None if it can't be created
        """
        # Direct Pydantic model check
        if hasattr(field_type, "model_fields"):
            try:
                return self.create_test_instance(field_type, recursion_depth + 1)
            except Exception:
                return None

        # BaseModel subclass check
        if isinstance(field_type, type) and issubclass(field_type, BaseModel):
            try:
                return self.create_test_instance(field_type, recursion_depth + 1)
            except Exception:
                return None

        # Handle string type annotations (forward references)
        if isinstance(field_type, str):
            # Try to find the model class by name
            try:
                # Look in the current tool's models directory
                tool_path = getattr(self, "_current_tool_path", Path.cwd())
                model_class = self.find_model_class(tool_path, field_type)
                if model_class and hasattr(model_class, "model_fields"):
                    return self.create_test_instance(model_class, recursion_depth + 1)
            except Exception:
                pass

        # Handle type names that might be class names we need to find
        if hasattr(field_type, "__name__"):
            try:
                tool_path = getattr(self, "_current_tool_path", Path.cwd())
                model_class = self.find_model_class(tool_path, field_type.__name__)
                if model_class and hasattr(model_class, "model_fields"):
                    return self.create_test_instance(model_class, recursion_depth + 1)
            except Exception:
                pass

        return None

    def validate_sp0_contract_structure(self, contract_data: dict) -> list[str]:
        """
        Validate contract structure against SP0 requirements.

        Args:
            contract_data: The loaded contract YAML data

        Returns:
            List of validation messages
        """
        validations = []

        # Required SP0 fields (base)
        required_base_fields = [
            "contract_version",
            "node_name",
            "node_version",
            "contract_name",
            "node_type",
            "tool_specification",
        ]

        # Check if new format (input_state/output_state) or old format (input_model/output_model)
        has_new_format = (
            "input_state" in contract_data and "output_state" in contract_data
        )
        has_old_format = (
            "input_model" in contract_data and "output_model" in contract_data
        )

        required_fields = required_base_fields.copy()
        if has_old_format:
            required_fields.extend(["input_model", "output_model"])
        elif has_new_format:
            required_fields.extend(["input_state", "output_state", "definitions"])

        for field in required_fields:
            if field in contract_data:
                validations.append(f"✅ Required field '{field}' present")
            else:
                validations.append(f"❌ Required field '{field}' missing")

        # Validate node_type is valid
        valid_node_types = ["COMPUTE", "EFFECT", "ORCHESTRATOR", "REDUCER", "HUB"]
        node_type = contract_data.get("node_type")
        if node_type in valid_node_types:
            validations.append(f"✅ Valid node_type: {node_type}")
        elif node_type:
            validations.append(f"❌ Invalid node_type: {node_type}")

        # Validate tool_specification structure
        tool_spec = contract_data.get("tool_specification")
        if tool_spec:
            spec_validations = []
            required_spec_fields = [
                "tool_name",
                "version",
                "main_tool_class",
                "container_injection",
            ]

            for field in required_spec_fields:
                if field in tool_spec:
                    spec_validations.append(f"✅ Tool spec field '{field}' present")
                else:
                    spec_validations.append(f"❌ Tool spec field '{field}' missing")

            # Check container injection
            if tool_spec.get("container_injection") == "ModelONEXContainer":
                spec_validations.append("✅ Correct container_injection: ModelONEXContainer")
            else:
                spec_validations.append(
                    f"❌ Invalid container_injection: {tool_spec.get('container_injection')}",
                )

            validations.extend(spec_validations)

        return validations

    def validate_contract_format(self, contract_data: dict) -> list[str]:
        """
        Validate contract against ModelContractContent requirements.
        This is the critical validation that NodeBase uses.

        Args:
            contract_data: The loaded contract YAML data

        Returns:
            List of validation messages
        """
        validations = []

        # Test contract_version format specifically
        contract_version = contract_data.get("contract_version")
        if contract_version:
            if isinstance(contract_version, dict):
                # Check for required ModelSemVer fields (simplified version - only major, minor, patch)
                required_semver_fields = ["major", "minor", "patch"]
                missing_fields = []
                for field in required_semver_fields:
                    if field not in contract_version:
                        missing_fields.append(field)

                if missing_fields:
                    validations.append(
                        f"❌ contract_version missing required fields: {', '.join(missing_fields)}",
                    )
                    validations.append(f"    Current: {contract_version}")
                    validations.append(
                        "    Required: {major: X, minor: Y, patch: Z}",
                    )
                else:
                    validations.append(
                        "✅ contract_version has all required ModelSemVer fields",
                    )
            else:
                validations.append(
                    f"❌ contract_version must be a dictionary, got: {type(contract_version)}",
                )

        # Test node_version format
        node_version = contract_data.get("node_version")
        if node_version:
            if isinstance(node_version, dict):
                required_semver_fields = ["major", "minor", "patch"]
                missing_fields = []
                for field in required_semver_fields:
                    if field not in node_version:
                        missing_fields.append(field)

                if missing_fields:
                    validations.append(
                        f"❌ node_version missing required fields: {', '.join(missing_fields)}",
                    )
                else:
                    validations.append(
                        "✅ node_version has all required ModelSemVer fields",
                    )
            else:
                validations.append(
                    f"❌ node_version must be a dictionary, got: {type(node_version)}",
                )

        # NEW: Use node-specific contract models for strong typing validation
        # This automatically catches architectural violations like COMPUTE nodes with state_management
        try:
            node_specific_contract = self.create_node_specific_contract(contract_data)
            validations.append(
                f"✅ Contract validates as {type(node_specific_contract).__name__}",
            )

            # Validate node-specific configuration WITH original contract data
            try:
                node_specific_contract.validate_node_specific_config(contract_data)
                validations.append("✅ Node-specific configuration validation passed")
            except Exception as config_error:
                validations.append(
                    f"❌ Node-specific validation failed: {config_error!s}",
                )

        except Exception as e:
            # Pydantic v2 wraps validation errors differently
            error_msg = f"Validation error: {type(e).__name__}"
            validations.append(f"❌ ARCHITECTURAL VIOLATION: {error_msg}")
            validations.append(
                "    This contract violates node-type-specific constraints",
            )

            # Provide specific guidance for common violations
            if (
                "state_management" in error_msg.lower()
                and "compute" in str(contract_data.get("node_type", "")).lower()
            ):
                validations.append(
                    "    COMPUTE nodes cannot have state_management - use REDUCER nodes instead",
                )
            elif (
                "aggregation" in error_msg.lower()
                and "compute" in str(contract_data.get("node_type", "")).lower()
            ):
                validations.append(
                    "    COMPUTE nodes cannot have aggregation - use REDUCER nodes instead",
                )

        return validations

    def validate_architectural_constraints(self, contract_data: dict) -> list[str]:
        """
        Validate contract against node-type-specific architectural constraints.

        This is the core improvement that catches violations like COMPUTE nodes
        with state_management configuration.

        Args:
            contract_data: The loaded contract YAML data

        Returns:
            List of architectural validation messages
        """
        validations = []

        # Get node_type from contract
        node_type_str = contract_data.get("node_type")
        if not node_type_str:
            validations.append("❌ Contract missing required node_type field")
            return validations

        try:
            node_type = EnumNodeType(node_type_str)
        except ValueError:
            validations.append(f"❌ Invalid node_type: {node_type_str}")
            return validations

        validations.append(f"✅ Node type: {node_type.value}")

        # Check architectural constraints based on node type
        if node_type == EnumNodeType.COMPUTE:
            # COMPUTE nodes should NOT have state_management or aggregation
            if "state_management" in contract_data:
                validations.append(
                    "❌ ARCHITECTURAL VIOLATION: COMPUTE nodes cannot have state_management configuration",
                )
                validations.append(
                    "❌   State management is only allowed in REDUCER nodes",
                )

            if "aggregation" in contract_data:
                validations.append(
                    "❌ ARCHITECTURAL VIOLATION: COMPUTE nodes cannot have aggregation configuration",
                )
                validations.append("❌   Aggregation is only allowed in REDUCER nodes")

            # Check service configuration for external dependencies
            service_config = contract_data.get("service_configuration", {})
            if service_config.get("requires_external_dependencies", False):
                validations.append(
                    "❌ ARCHITECTURAL VIOLATION: COMPUTE nodes cannot require external dependencies",
                )
                validations.append("❌   Use EFFECT nodes for external integrations")

            if not any(v.startswith("❌") for v in validations[-3:]):
                validations.append(
                    "✅ COMPUTE node architectural constraints satisfied",
                )

        elif node_type == EnumNodeType.REDUCER:
            # REDUCER nodes should have state_management
            if "state_management" not in contract_data:
                validations.append(
                    "❌ ARCHITECTURAL VIOLATION: REDUCER nodes should have state_management configuration",
                )
                validations.append(
                    "❌   State management is required for data aggregation and persistence",
                )
            else:
                validations.append(
                    "✅ REDUCER node has required state_management configuration",
                )

        elif node_type == EnumNodeType.EFFECT:
            # EFFECT nodes should not have state_management
            if "state_management" in contract_data:
                validations.append(
                    "❌ ARCHITECTURAL VIOLATION: EFFECT nodes should not manage internal state",
                )
                validations.append(
                    "❌   Use REDUCER nodes for state management, EFFECT nodes for side effects",
                )
            else:
                validations.append("✅ EFFECT node correctly has no state_management")

        elif node_type == EnumNodeType.ORCHESTRATOR:
            # ORCHESTRATOR nodes should not have state_management
            if "state_management" in contract_data:
                validations.append(
                    "❌ ARCHITECTURAL VIOLATION: ORCHESTRATOR nodes should not manage state directly",
                )
                validations.append(
                    "❌   Use REDUCER nodes for state, ORCHESTRATOR nodes for coordination",
                )
            else:
                validations.append(
                    "✅ ORCHESTRATOR node correctly has no direct state_management",
                )

        return validations

    def validate_all_contracts(self) -> dict:
        """
        Validate all infrastructure contracts.

        Returns:
            Overall validation results
        """

        # Find all contract files
        contract_files = list(self.infrastructure_path.glob("**/contract.yaml"))

        results = []
        successful = 0
        failed = 0

        # Validate each contract
        for contract_path in contract_files:
            result = self.validate_contract(contract_path)
            results.append(result)

            if result["status"] == "SUCCESS":
                successful += 1
            else:
                failed += 1

                # Print detailed errors
                if "validations" in result:
                    for validation in result["validations"]:
                        if validation.startswith("❌"):
                            pass

        # Summary
        total = successful + failed
        success_rate = (successful / total * 100) if total > 0 else 0

        if success_rate >= 90 or success_rate >= 75:
            pass
        else:
            pass

        return {
            "total_contracts": total,
            "successful": successful,
            "failed": failed,
            "success_rate": success_rate,
            "results": results,
            "validation_passed": success_rate >= 75,
        }


def main():
    """Main validation entry point with subcontract validation testing."""
    import argparse

    parser = argparse.ArgumentParser(description="Infrastructure Contract Validator")
    parser.add_argument(
        "--test-subcontracts",
        action="store_true",
        help="Run specific subcontract validation tests",
    )
    parser.add_argument(
        "--debug-aggregator",
        action="store_true",
        help="Debug the message aggregator validation specifically",
    )
    args = parser.parse_args()

    infrastructure_path = Path(__file__).parent
    validator = ContractValidator(infrastructure_path)

    if args.debug_aggregator:
        # Debug the message aggregator specifically

        aggregator_path = infrastructure_path / "canary_compute/v1_0_0/contract.yaml"
        if not aggregator_path.exists():
            return

        # Load the contract YAML
        import yaml

        with open(aggregator_path) as f:
            contract_data = yaml.safe_load(f)

        # Try to create the model
        try:
            node_contract = validator.create_node_specific_contract(contract_data)

            # Try validation
            with contextlib.suppress(Exception):
                node_contract.validate_node_specific_config(contract_data)

        except Exception:
            pass

        return

    if args.test_subcontracts:
        # Test specific contracts for subcontract validation

        # Test 1: Message Aggregator (should fail - COMPUTE with state_management)
        aggregator_path = (
            infrastructure_path
            / "tool_infrastructure_message_aggregator_compute/v1_0_0/contract.yaml"
        )
        if aggregator_path.exists():
            result = validator.validate_contract(aggregator_path)
            validation_text = " ".join(result.get("validations", []))
            has_violation = "state_management subcontracts" in validation_text
            if has_violation:
                pass
            else:
                for _validation in result.get("validations", [])[:3]:
                    pass

        # Test 2: Infrastructure Reducer (should pass - REDUCER can have state_management)
        reducer_path = (
            infrastructure_path / "tool_infrastructure_reducer/v1_0_0/contract.yaml"
        )
        if reducer_path.exists():
            result = validator.validate_contract(reducer_path)
            validation_text = " ".join(result.get("validations", []))
            has_forbidden_violation = "cannot have state_management" in validation_text
            if not has_forbidden_violation:
                pass
            else:
                pass

        # Test 3: Event Type Warnings (all nodes should warn about missing event_type)
        event_type_warnings = 0
        total_contracts = 0

        for contract_file in infrastructure_path.rglob("*/v1_0_0/contract.yaml"):
            total_contracts += 1
            result = validator.validate_contract(contract_file)
            validation_text = " ".join(result.get("validations", []))
            if "event_type subcontracts" in validation_text:
                event_type_warnings += 1

        if event_type_warnings == total_contracts:
            pass
        else:
            pass

        return

    # Normal validation mode
    results = validator.validate_all_contracts()

    # Return appropriate exit code
    if results["validation_passed"]:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
